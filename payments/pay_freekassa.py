import hashlib
import hmac
import json
from typing import Any, Dict, Optional

import aiohttp

from bot import sql
from config import API_FREEKASSA, SHOP_ID_FREEKASSA, FREEKASSA_SERVER_IP
from logging_config import logger

FK_API_BASE = "https://api.fk.life/v1"
FK_PAYMENT_SBP_QR = 44


def _fk_scalar_for_signature(v: Any) -> str:
    """
    Строка для подписи должна совпадать с PHP: ksort + implode('|', $data),
    где значения приводятся к строке как в PHP (float 99.0 → \"99\", не \"99.0\").
    """
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        s = format(v, ".10g")
        return s
    return str(v)


def fk_build_signature(body: Dict[str, Any], api_key: str) -> str:
    sign_data = {k: v for k, v in body.items() if k != "signature"}
    keys = sorted(sign_data.keys())
    message = "|".join(_fk_scalar_for_signature(sign_data[k]) for k in keys)
    return hmac.new(
        api_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class FreekassaPayment:
    def __init__(self, api_key: str, shop_id: int):
        self.api_key = api_key
        self.shop_id = shop_id

    async def _raw_post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{FK_API_BASE}/{path.lstrip('/')}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body) as response:
                text = await response.text()
                try:
                    data = json.loads(text) if text else {}
                except json.JSONDecodeError:
                    logger.error(f"FreeKassa {path} не JSON: {text[:500]}")
                    raise
                if response.status != 200:
                    logger.error(f"FreeKassa {path} {response.status}: {text[:800]}")
                    raise RuntimeError(f"FreeKassa HTTP {response.status}: {text[:200]}")
                typ = data.get("type")
                if typ and typ != "success":
                    logger.error(f"FreeKassa {path}: {text[:800]}")
                    raise RuntimeError(f"FreeKassa API: {data.get('message', typ)}")
                return data

    async def create_order(
            self,
            nonce: int,
            payment_id: str,
            amount: float,
            email: str,
            ip: str,
            payment_system_id: int = FK_PAYMENT_SBP_QR,
    ) -> tuple[Dict[str, Any], str]:
        amt = float(amount)
        amount_field: Any = int(amt) if amt.is_integer() else amt
        body: Dict[str, Any] = {
            "shopId": self.shop_id,
            "nonce": nonce,
            "paymentId": payment_id,
            "amount": amount_field,
            "currency": "RUB",
            "email": email,
            "ip": ip,
            "i": payment_system_id,
        }
        signature = fk_build_signature(body, self.api_key)
        body["signature"] = signature
        result = await self._raw_post("orders/create", body)
        return result, signature

    async def get_orders(
        self,
        nonce: int,
        *,
        payment_id: Optional[str] = None,
        order_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if payment_id is None and order_id is None:
            raise ValueError("get_orders: укажите payment_id или order_id")
        body: Dict[str, Any] = {
            "shopId": self.shop_id,
            "nonce": nonce,
        }
        if payment_id is not None:
            body["paymentId"] = payment_id
        if order_id is not None:
            body["orderId"] = order_id
        body["signature"] = fk_build_signature(body, self.api_key)
        return await self._raw_post("orders", body)


def _parse_fk_order_status(orders_payload: Dict[str, Any]) -> Optional[int]:
    orders = orders_payload.get("orders")
    if not orders:
        return None
    first = orders[0]
    return first.get("status")


def _payment_url_from_create(data: Dict[str, Any]) -> str:
    return (data.get("location") or data.get("Location") or "").strip()


async def pay(val: str, des: str, user_id: str, duration: str, white: bool) -> Dict:
    if not API_FREEKASSA or SHOP_ID_FREEKASSA is None:
        logger.error("FreeKassa: не заданы API_FREEKASSA или SHOP_ID_FREEKASSA")
        return {"status": "error", "url": "", "id": ""}

    payload = (
        f"user_id:{user_id},duration:{duration},white:{white},gift:False,method:fksbp,amount:{int(val)}"
    )
    fk = FreekassaPayment(API_FREEKASSA, SHOP_ID_FREEKASSA)
    nonce = await sql.alloc_fk_api_nonce()
    payment_id = f"fk{user_id}n{nonce}"
    email = f"{user_id}@telegram.org"

    try:
        data, signature = await fk.create_order(
            nonce=nonce,
            payment_id=payment_id,
            amount=float(val),
            email=email,
            ip=FREEKASSA_SERVER_IP,
        )
        url = _payment_url_from_create(data)
        fk_oid = data.get("orderId")
        await sql.add_fk_sbp_payment(
            int(user_id),
            int(val),
            "pending",
            payment_id,
            int(fk_oid) if fk_oid is not None else None,
            payload,
            nonce,
            signature,
            is_gift=False,
        )
        logger.info(f"✅ FreeKassa заказ: paymentId={payment_id}, orderId={fk_oid}")
        return {"status": "pending", "url": url, "id": payment_id}
    except Exception as e:
        logger.error(f"❌ FreeKassa create_order: {e}")
        return {"status": "error", "url": "", "id": ""}


async def pay_for_gift(val: str, des: str, user_id: str, duration: str, white: bool) -> Dict:
    if not API_FREEKASSA or SHOP_ID_FREEKASSA is None:
        logger.error("FreeKassa: не заданы API_FREEKASSA или SHOP_ID_FREEKASSA")
        return {"status": "error", "url": "", "id": ""}

    payload = (
        f"user_id:{user_id},duration:{duration},white:{white},gift:True,method:fksbp,amount:{int(val)}"
    )
    fk = FreekassaPayment(API_FREEKASSA, SHOP_ID_FREEKASSA)
    nonce = await sql.alloc_fk_api_nonce()
    payment_id = f"fk{user_id}n{nonce}"
    email = f"{user_id}@telegram.org"

    try:
        data, signature = await fk.create_order(
            nonce=nonce,
            payment_id=payment_id,
            amount=float(val),
            email=email,
            ip=FREEKASSA_SERVER_IP,
        )
        url = _payment_url_from_create(data)
        fk_oid = data.get("orderId")
        await sql.add_fk_sbp_payment(
            int(user_id),
            int(val),
            "pending",
            payment_id,
            int(fk_oid) if fk_oid is not None else None,
            payload,
            nonce,
            signature,
            is_gift=True,
        )
        logger.info(f"✅ FreeKassa подарок: paymentId={payment_id}, orderId={fk_oid}")
        return {"status": "pending", "url": url, "id": payment_id}
    except Exception as e:
        logger.error(f"❌ FreeKassa create_order (gift): {e}")
        return {"status": "error", "url": "", "id": ""}


# СБП переведён на WATA (pay_wata); хендлер FreeKassa СБП отключён (check_fk остаётся для старых pending).
