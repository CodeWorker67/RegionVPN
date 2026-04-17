from datetime import datetime, timedelta

from bot import bot, sql
from config import WATA_API_CARD_KEY
from keyboard import keyboard_payment_cancel
from lexicon import lexicon
from logging_config import logger
from payments.pay_wata import (
    WATA_DECLINED_CANCEL_GRACE_AFTER_LINK,
    WataPayment,
    wata_order_payment_state,
    wata_transactions_status_counts,
)
from payments.process_payload import process_confirmed_payment

_EMPTY_API_EXPIRE = timedelta(hours=12)


async def process_confirmed_wata_card(payment) -> None:
    if not payment.payload:
        logger.error(f"WATA Карта: пустой payload для orderId={payment.transaction_id}")
        return
    await process_confirmed_payment(payment.payload)


async def _notify_wata_card_cancel(uid) -> None:
    if uid and int(uid) > 0:
        try:
            await bot.send_message(
                int(uid),
                lexicon["payment_cancel"],
                reply_markup=keyboard_payment_cancel(),
            )
        except Exception as e:
            logger.error(f"WATA Карта cancel notify: {e}")


async def check_wata_card() -> None:
    if not WATA_API_CARD_KEY:
        return

    client = WataPayment(WATA_API_CARD_KEY)

    try:
        pending_payments = await sql.get_pending_wata_card_payments_polled()
        total_pending = await sql.count_pending_wata_card()
        if not pending_payments:
            logger.info("✅ Нет платежей WATA Карта в текущей порции опроса")
            return

        logger.info(
            f"🔍 WATA Карта: в порции {len(pending_payments)}, всего pending в БД {total_pending}"
        )
        processed = confirmed = canceled = 0

        for payment in pending_payments:
            try:
                order_id = payment.transaction_id
                items = await client.search_transactions_by_order_id(order_id)
                tc = payment.time_created
                logger.debug(
                    f"WATA Карта orderId={order_id} tx_counts={wata_transactions_status_counts(items)}"
                )
                if (
                    not items
                    and tc is not None
                    and datetime.now() - tc > _EMPTY_API_EXPIRE
                    and payment.status != "canceled"
                ):
                    await sql.update_wata_card_status(order_id, "canceled")
                    logger.info(
                        f"🔄 WATA Карта orderId={order_id} → canceled (нет транзакций в API > {int(_EMPTY_API_EXPIRE.total_seconds() // 3600)} ч)"
                    )
                    canceled += 1
                    await _notify_wata_card_cancel(payment.user_id)
                    processed += 1
                    continue

                state = wata_order_payment_state(items, "CardCrypto")

                if state == "paid":
                    if payment.status != "confirmed":
                        await sql.update_wata_card_status(order_id, "confirmed")
                        logger.info(f"✅ WATA Карта оплачена orderId={order_id}")
                        await process_confirmed_wata_card(payment)
                        confirmed += 1
                    processed += 1
                elif state in ("declined", "wrong_paid"):
                    if (
                        state == "declined"
                        and tc is not None
                        and datetime.now() - tc < WATA_DECLINED_CANCEL_GRACE_AFTER_LINK
                    ):
                        logger.info(
                            f"WATA Карта orderId={order_id}: declined в API, записи < "
                            f"{int(WATA_DECLINED_CANCEL_GRACE_AFTER_LINK.total_seconds() // 60)} мин — "
                            "отмену в БД не делаем (ждём Paid)"
                        )
                        processed += 1
                    elif payment.status != "canceled":
                        await sql.update_wata_card_status(order_id, "canceled")
                        logger.info(f"🔄 WATA Карта orderId={order_id} → canceled ({state})")
                        canceled += 1
                        await _notify_wata_card_cancel(payment.user_id)
                        processed += 1
                    else:
                        processed += 1
                else:
                    processed += 1

            except Exception as e:
                logger.error(f"❌ WATA Карта check {payment.transaction_id}: {e}")

        logger.info(
            f"✅ Проверка WATA Карта: обработано {processed}, подтверждено {confirmed}, отменено {canceled}"
        )
    except Exception as e:
        logger.error(f"❌ check_wata_card: {e}")
