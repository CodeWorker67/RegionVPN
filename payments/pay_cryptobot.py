import aiohttp
from typing import Dict, Optional
from aiogram import F, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot import sql
from config import CRYPTOBOT_API_TOKEN, ADMIN_IDS, BOT_URL
from keyboard import create_kb, BTN_BACK, btn_pay_cryptobot
from lexicon import lexicon, dct_price, dct_desc
from logging_config import logger

router: Router = Router()


class CryptoBotPayment:
    """Класс для взаимодействия с Cryptobot API"""
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {
            "Crypto-Pay-API-Token": api_token,
            "Content-Type": "application/json"
        }

    async def create_invoice(self, fiat_amount: float, fiat_currency: str, description: str,
                             payload: str, expires_in: int = 7200) -> Dict:
        """Создание счета в Cryptobot с суммой в фиате — пользователь сам выбирает криптовалюту"""
        url = f"{self.base_url}/createInvoice"
        data = {
            "currency_type": "fiat",
            "fiat": fiat_currency,
            "amount": str(fiat_amount),
            "description": description,
            "payload": payload,
            "paid_btn_name": "openBot",
            "paid_btn_url": BOT_URL,
            "allow_comments": False,
            "allow_anonymous": False,
            "expires_in": expires_in
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=self.headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("ok"):
                            inv = result["result"]
                            return {
                                'status': 'pending',
                                'url': inv['pay_url'],
                                'invoice_id': inv['invoice_id'],
                                'payload': payload
                            }
                        else:
                            logger.error(f"Cryptobot API error: {result}")
                            return {'status': 'error', 'message': result.get('error')}
                    else:
                        text = await resp.text()
                        logger.error(f"Cryptobot HTTP error {resp.status}: {text}")
                        return {'status': 'error', 'message': f"HTTP {resp.status}"}
        except Exception as e:
            logger.error(f"Error creating Cryptobot invoice: {e}")
            return {'status': 'error', 'message': str(e)}

    async def get_invoice_status(self, invoice_id: int) -> Optional[str]:
        """Получение статуса счета по invoice_id"""
        url = f"{self.base_url}/getInvoices"
        params = {"invoice_ids": str(invoice_id)}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("ok") and result.get("result", {}).get("items"):
                            invoice = result["result"]["items"][0]
                            return invoice.get("status")
                        else:
                            logger.error(f"Failed to get invoice {invoice_id}: {result}")
                            return None
                    else:
                        logger.error(f"HTTP error {resp.status} for invoice {invoice_id}")
                        return None
        except Exception as e:
            logger.error(f"Error checking invoice {invoice_id}: {e}")
            return None


async def create_cryptobot_payment(rub_amount: int, description: str,
                                   user_id: int, duration: str, white: bool,
                                   is_gift: bool) -> Dict:
    """
    Создание платежа через Cryptobot с суммой в рублях.
    Пользователь сам выбирает криптовалюту внутри Cryptobot.
    """
    cryptobot = CryptoBotPayment(CRYPTOBOT_API_TOKEN)

    payload = (f"user_id:{user_id},duration:{duration},white:{white},"
               f"gift:{is_gift},method:cryptobot,amount:{rub_amount}")

    result = await cryptobot.create_invoice(
        fiat_amount=float(rub_amount),
        fiat_currency="RUB",
        description=description,
        payload=payload
    )

    if result['status'] == 'pending':
        try:
            await sql.add_cryptobot_payment(
                user_id=user_id,
                amount=float(rub_amount),
                currency="RUB",
                is_gift=is_gift,
                invoice_id=result['invoice_id'],
                payload=payload
            )
        except Exception as e:
            logger.error(f"Error saving cryptobot payment to DB: {e}")
            return {'status': 'error', 'url': '', 'invoice_id': ''}

    return result


@router.callback_query(F.data.startswith('crypto_'))
async def process_payment_crypto(callback: CallbackQuery):
    await callback.answer()
    gift_flag = False
    white_flag = False
    data = callback.data
    user_id = callback.from_user.id

    if 'gift_' in data:
        gift_flag = True

    if gift_flag:
        duration_key = data.replace('crypto_gift_r_', '')
    else:
        duration_key = data.replace('crypto_r_', '')

    rub_amount = dct_price[duration_key]
    desc_key = duration_key

    if 'white' in duration_key:
        white_flag = True
        duration = duration_key.replace('white_', '')
    elif 'old' in duration_key:
        duration = duration_key.replace('old', '')
    else:
        duration = duration_key

    if callback.from_user.id in ADMIN_IDS:
        rub_amount = 1

    if gift_flag:
        description = f"Подписка в подарок {dct_desc[desc_key]}"
    else:
        description = dct_desc[desc_key]

    result = await create_cryptobot_payment(
        rub_amount=rub_amount,
        description=description,
        user_id=user_id,
        duration=duration,
        white=white_flag,
        is_gift=gift_flag
    )

    if result['status'] == 'pending':
        text = lexicon['payment_link_white'] if white_flag else lexicon['payment_link']
        if gift_flag:
            text += '\n\nДля оплаты <b>подарочной подписки</b> перейдите по ссылке:'
        else:
            text += '\n\nДля оплаты тарифа перейдите по ссылке:'
        pay_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=btn_pay_cryptobot(rub_amount), url=result['url'])]
            ]
        )
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=pay_keyboard)
        logger.info(f"Юзер {user_id} создал счет в Cryptobot на {rub_amount} руб {'(подарок)' if gift_flag else ''}")
    else:
        await callback.message.answer(
            lexicon.get('error_payment', 'Произошла ошибка при создании счета.'),
            reply_markup=create_kb(1, back_to_main=BTN_BACK)
        )
