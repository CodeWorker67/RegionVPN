from datetime import datetime
import asyncio
import os
import tempfile

import openpyxl
from aiogram import Router
from openpyxl.styles import Alignment, Border, Side

from bot import sql, x3
from config import ADMIN_IDS
from logging_config import logger
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command

router = Router()


@router.message(Command(commands=['export']))
async def export_database_to_excel(message: Message):
    """Экспорт базы данных в Excel файл"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Эта команда доступна только администраторам.")
        return

    try:
        await message.answer("🔄 Начинаю экспорт базы данных...")

        snapshot = await sql.get_export_snapshot()

        def _sync_build_export() -> str:
            users_list = snapshot["users"]
            payments_list = snapshot["payments"]
            payments_cards_list = snapshot["payments_cards"]
            payments_platega_crypto_list = snapshot["payments_platega_crypto"]
            payments_stars_list = snapshot["payments_stars"]
            payments_cryptobot_list = snapshot["payments_cryptobot"]
            payments_fk_sbp_list = snapshot["payments_fk_sbp"]
            payments_wata_sbp_list = snapshot["payments_wata_sbp"]
            payments_wata_card_list = snapshot["payments_wata_card"]
            gifts_list = snapshot["gifts"]
            online_list = snapshot["online"]
            white_counter_list = snapshot["white_counter"]

            wb = openpyxl.Workbook()
            if 'Sheet' in wb.sheetnames:
                wb.remove(wb['Sheet'])
            
            # --- Лист USERS ---
            ws_users = wb.create_sheet(title="users")
            users_columns = [
                'id', 'user_id', 'ref', 'is_delete', 'in_panel', 'is_connect',
                'create_user', 'reserve_field', 'subscription_end_date',
                'white_subscription_end_date', 'last_notification_date',
                'last_broadcast_status', 'last_broadcast_date', 'stamp', 'ttclid',
            ]
            header_alignment = Alignment(horizontal="center", vertical="center")
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                 top=Side(style='thin'), bottom=Side(style='thin'))
            
            # Заголовки
            for col_num, title in enumerate(users_columns, 1):
                cell = ws_users.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border
            
            # Данные
            for row_num, user in enumerate(users_list, 2):
                row_data = [
                    user.id, user.user_id, user.ref, user.is_delete,
                    user.in_panel, user.is_connect, user.create_user,
                    user.reserve_field, user.subscription_end_date,
                    user.white_subscription_end_date, user.last_notification_date,
                    user.last_broadcast_status, user.last_broadcast_date,
                    user.stamp, user.ttclid,
                ]
                for col_num, value in enumerate(row_data, 1):
                    # Форматирование дат
                    if col_num in (9, 10, 13) and value:  # subscription_end_date, white_subscription_end_date, last_broadcast_date
                        if isinstance(value, datetime):
                            value = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif col_num == 11 and value:  # last_notification_date
                        if isinstance(value, datetime):
                            value = value.strftime('%Y-%m-%d')
                    cell = ws_users.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border
            
            # Автоширина
            for col in ws_users.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_users.column_dimensions[col_letter].width = min(max_len + 2, 50)
            
            # --- Лист PAYMENTS (Platega) ---
            ws_payments = wb.create_sheet(title="payments_sbp")
            payments_columns = ['ID', 'User ID', 'Amount', 'Time Created', 'Is Gift', 'Status', 'Transaction_Id']
            for col_num, title in enumerate(payments_columns, 1):
                cell = ws_payments.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border
            
            for row_num, pay in enumerate(payments_list, 2):
                row_data = [
                    pay.id, pay.user_id, pay.amount, pay.time_created,
                    pay.is_gift, pay.status, pay.transaction_id
                ]
                for col_num, value in enumerate(row_data, 1):
                    if col_num == 4 and value and isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    cell = ws_payments.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border
            
            for col in ws_payments.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_payments.column_dimensions[col_letter].width = min(max_len + 2, 50)

            # --- Лист PAYMENTS_FK_SBP (FreeKassa СБП) ---
            ws_fk_sbp = wb.create_sheet(title="payments_fk_sbp")
            fk_columns = [
                'ID', 'User ID', 'Amount', 'Time Created', 'Is Gift', 'Status',
                'Transaction_Id', 'FK_Order_Id', 'Nonce', 'Signature', 'Method', 'Payload',
            ]
            for col_num, title in enumerate(fk_columns, 1):
                cell = ws_fk_sbp.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border

            for row_num, pay in enumerate(payments_fk_sbp_list, 2):
                row_data = [
                    pay.id, pay.user_id, pay.amount, pay.time_created,
                    pay.is_gift, pay.status, pay.transaction_id, pay.fk_order_id,
                    pay.nonce, pay.signature, pay.method, pay.payload,
                ]
                for col_num, value in enumerate(row_data, 1):
                    if col_num == 4 and value and isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    cell = ws_fk_sbp.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border

            for col in ws_fk_sbp.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_fk_sbp.column_dimensions[col_letter].width = min(max_len + 2, 50)

            wata_columns = ['ID', 'User ID', 'Amount', 'Time Created', 'Is Gift', 'Status', 'Transaction_Id', 'Payload']

            ws_wata_sbp = wb.create_sheet(title="payments_wata_sbp")
            for col_num, title in enumerate(wata_columns, 1):
                cell = ws_wata_sbp.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border
            for row_num, pay in enumerate(payments_wata_sbp_list, 2):
                row_data = [
                    pay.id, pay.user_id, pay.amount, pay.time_created,
                    pay.is_gift, pay.status, pay.transaction_id, pay.payload,
                ]
                for col_num, value in enumerate(row_data, 1):
                    if col_num == 4 and value and isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    cell = ws_wata_sbp.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border
            for col in ws_wata_sbp.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_wata_sbp.column_dimensions[col_letter].width = min(max_len + 2, 50)

            ws_wata_card = wb.create_sheet(title="payments_wata_card")
            for col_num, title in enumerate(wata_columns, 1):
                cell = ws_wata_card.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border
            for row_num, pay in enumerate(payments_wata_card_list, 2):
                row_data = [
                    pay.id, pay.user_id, pay.amount, pay.time_created,
                    pay.is_gift, pay.status, pay.transaction_id, pay.payload,
                ]
                for col_num, value in enumerate(row_data, 1):
                    if col_num == 4 and value and isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    cell = ws_wata_card.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border
            for col in ws_wata_card.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_wata_card.column_dimensions[col_letter].width = min(max_len + 2, 50)

            # --- Лист PAYMENTS_CARDS (платежи по картам) ---
            ws_payments_cards = wb.create_sheet(title="payments_cards")
            cards_columns = ['ID', 'User ID', 'Amount', 'Time Created', 'Is Gift', 'Status', 'Transaction_Id',
                             'Payload']
            for col_num, title in enumerate(cards_columns, 1):
                cell = ws_payments_cards.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border
            
            for row_num, pay in enumerate(payments_cards_list, 2):
                row_data = [
                    pay.id, pay.user_id, pay.amount, pay.time_created,
                    pay.is_gift, pay.status, pay.transaction_id, pay.payload
                ]
                for col_num, value in enumerate(row_data, 1):
                    if col_num == 4 and value and isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    cell = ws_payments_cards.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border
            
            for col in ws_payments_cards.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_payments_cards.column_dimensions[col_letter].width = min(max_len + 2, 50)
            
            
            # --- Лист PAYMENTS_STARS ---
            ws_payments_stars = wb.create_sheet(title="payments_stars")
            stars_columns = ['ID', 'User ID', 'Amount (Stars)', 'Time Created', 'Is Gift', 'Status']
            for col_num, title in enumerate(stars_columns, 1):
                cell = ws_payments_stars.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border
            
            for row_num, ps in enumerate(payments_stars_list, 2):
                row_data = [
                    ps.id, ps.user_id, ps.amount, ps.time_created,
                    ps.is_gift, ps.status
                ]
                for col_num, value in enumerate(row_data, 1):
                    if col_num == 4 and value and isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    cell = ws_payments_stars.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border
            
            for col in ws_payments_stars.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_payments_stars.column_dimensions[col_letter].width = min(max_len + 2, 50)
            
            
            
            # --- Лист PAYMENTS_PLATEGA_CRYPTO ---
            ws_platega_crypto = wb.create_sheet(title="payments_platega_crypto")
            platega_crypto_columns = ['ID', 'User ID', 'Amount', 'Time Created', 'Is Gift', 'Status', 'Transaction_Id',
                                      'Payload']
            for col_num, title in enumerate(platega_crypto_columns, 1):
                cell = ws_platega_crypto.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border
            
            for row_num, pay in enumerate(payments_platega_crypto_list, 2):
                row_data = [
                    pay.id, pay.user_id, pay.amount, pay.time_created,
                    pay.is_gift, pay.status, pay.transaction_id, pay.payload
                ]
                for col_num, value in enumerate(row_data, 1):
                    if col_num == 4 and value and isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    cell = ws_platega_crypto.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border
            
            for col in ws_platega_crypto.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_platega_crypto.column_dimensions[col_letter].width = min(max_len + 2, 50)
            
            
            # --- Лист PAYMENTS_CRYPTOBOT ---
            ws_payments_cryptobot = wb.create_sheet(title="payments_cryptobot")
            crypto_columns = [
                'ID', 'User ID', 'Amount', 'Currency', 'Time Created',
                'Is Gift', 'Status', 'Invoice ID', 'Payload'
            ]
            for col_num, title in enumerate(crypto_columns, 1):
                cell = ws_payments_cryptobot.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border
            
            for row_num, pc in enumerate(payments_cryptobot_list, 2):
                row_data = [
                    pc.id, pc.user_id, pc.amount, pc.currency, pc.time_created,
                    pc.is_gift, pc.status, pc.invoice_id, pc.payload
                ]
                for col_num, value in enumerate(row_data, 1):
                    if col_num == 5 and value and isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    cell = ws_payments_cryptobot.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border
            
            for col in ws_payments_cryptobot.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_payments_cryptobot.column_dimensions[col_letter].width = min(max_len + 2, 50)
            
            # --- Лист GIFTS ---
            ws_gifts = wb.create_sheet(title="gifts")
            gifts_columns = ['gift_id', 'giver_id', 'duration', 'recepient_id', 'white_flag', 'flag']
            for col_num, title in enumerate(gifts_columns, 1):
                cell = ws_gifts.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border
            
            for row_num, gift in enumerate(gifts_list, 2):
                row_data = [
                    gift.gift_id, gift.giver_id, gift.duration,
                    gift.recepient_id, gift.white_flag, gift.flag
                ]
                for col_num, value in enumerate(row_data, 1):
                    cell = ws_gifts.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border
            
            for col in ws_gifts.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_gifts.column_dimensions[col_letter].width = min(max_len + 2, 50)
            
            # --- Лист ONLINE ---
            ws_online = wb.create_sheet(title="online")
            online_columns = ['ID', 'Дата сбора', 'Всего в панели', 'Активны сегодня', 'Платных', 'Триальных']
            for col_num, title in enumerate(online_columns, 1):
                cell = ws_online.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border
            
            for row_num, rec in enumerate(online_list, 2):
                row_data = [
                    rec.online_id, rec.online_date, rec.users_panel,
                    rec.users_active, rec.users_pay, rec.users_trial
                ]
                for col_num, value in enumerate(row_data, 1):
                    if col_num == 2 and value and isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    cell = ws_online.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border
            
            for col in ws_online.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_online.column_dimensions[col_letter].width = min(max_len + 2, 50)
            
            # --- Лист WHITE_COUNTER ---
            ws_white_counter = wb.create_sheet(title="white_counter")
            wc_columns = ['ID', 'User ID', 'Time Created']
            for col_num, title in enumerate(wc_columns, 1):
                cell = ws_white_counter.cell(row=1, column=col_num, value=title)
                cell.alignment = header_alignment
                cell.border = thin_border
            
            for row_num, wc in enumerate(white_counter_list, 2):
                row_data = [wc.id, wc.user_id, wc.time_created]
                for col_num, value in enumerate(row_data, 1):
                    if col_num == 3 and value and isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    cell = ws_white_counter.cell(row=row_num, column=col_num, value=value)
                    cell.border = thin_border
            
            for col in ws_white_counter.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws_white_counter.column_dimensions[col_letter].width = min(max_len + 2, 50)
            
            # Заморозка заголовков
            for ws in [ws_users, ws_payments, ws_fk_sbp, ws_wata_sbp, ws_wata_card, ws_payments_cards, ws_payments_stars, ws_platega_crypto,
                       ws_payments_cryptobot, ws_gifts, ws_online, ws_white_counter]:
                ws.freeze_panes = ws['A2']

            fd, path = tempfile.mkstemp(suffix=".xlsx")
            os.close(fd)
            wb.save(path)
            return path

        export_path = await asyncio.to_thread(_sync_build_export)
        users_list = snapshot["users"]
        gifts_list = snapshot["gifts"]
        payments_list = snapshot["payments"]
        payments_cards_list = snapshot["payments_cards"]
        payments_stars_list = snapshot["payments_stars"]
        payments_platega_crypto_list = snapshot["payments_platega_crypto"]
        payments_cryptobot_list = snapshot["payments_cryptobot"]
        payments_fk_sbp_list = snapshot["payments_fk_sbp"]
        payments_wata_sbp_list = snapshot["payments_wata_sbp"]
        payments_wata_card_list = snapshot["payments_wata_card"]

        users_count = len(users_list)
        gifts_count = len(gifts_list)
        payments_count = len(payments_list)
        payments_cards_count = len(payments_cards_list)
        payments_stars_count = len(payments_stars_list)
        payments_cryptobot_count = len(payments_cryptobot_list)
        payments_platega_crypto_count = len(payments_platega_crypto_list)
        white_counter_count = len(snapshot["white_counter"])
        white_subscription_count = sum(
            1 for u in users_list if u.white_subscription_end_date is not None
        )

        successful_payments_count = sum(1 for p in payments_list if p.status == "confirmed")
        successful_cards_count = sum(1 for p in payments_cards_list if p.status == "confirmed")
        successful_platega_crypto_count = sum(
            1 for p in payments_platega_crypto_list if p.status == "confirmed"
        )
        successful_stars_count = sum(1 for p in payments_stars_list if p.status == "confirmed")
        successful_cryptobot_count = sum(1 for p in payments_cryptobot_list if p.status == "paid")
        successful_fk_sbp_count = sum(1 for p in payments_fk_sbp_list if p.status == "confirmed")
        fk_sbp_count = len(payments_fk_sbp_list)
        successful_wata_sbp_count = sum(1 for p in payments_wata_sbp_list if p.status == "confirmed")
        wata_sbp_count = len(payments_wata_sbp_list)
        successful_wata_card_count = sum(1 for p in payments_wata_card_list if p.status == "confirmed")
        wata_card_count = len(payments_wata_card_list)

        try:
            now_s = datetime.now().strftime('%d.%m.%Y %H:%M')
            caption = (
                "📊 Экспорт базы данных (Excel)\n"
                f"📅 Создано: {now_s}\n\n"
                "📊 Краткая сводка по платежам:\n"
                f"├ 👥 Пользователей: {users_count}\n"
                f"├ 🎁 Подарков: {gifts_count}\n"
                f"├ 📲 FreeKassa СБП (архив): {successful_fk_sbp_count}/{fk_sbp_count}\n"
                f"├ ⚡ WATA СБП: {successful_wata_sbp_count}/{wata_sbp_count}\n"
                f"├ 💳 WATA Карта: {successful_wata_card_count}/{wata_card_count}\n"
                f"├ ⚡ Platega СБП (архив): {successful_payments_count}/{payments_count}\n"
                f"├ 💳 Platega Карта: {successful_cards_count}/{payments_cards_count}\n"
                f"├ ⭐ Stars: {successful_stars_count}/{payments_stars_count}\n"
                f"├ 💰 Platega Крипто: {successful_platega_crypto_count}/{payments_platega_crypto_count}\n"
                f"├ 💎 Криптобот: {successful_cryptobot_count}/{payments_cryptobot_count}\n"
                f"├ ⚪ White-подписок: {white_subscription_count}\n"
                f"└ 👁 White-кликов: {white_counter_count}"
            )
            await message.answer_document(
                document=FSInputFile(export_path),
                caption=caption,
            )
        finally:
            try:
                os.remove(export_path)
            except OSError:
                pass

        logger.info(f"Администратор {message.from_user.id} экспортировал базу данных в Excel")

    except Exception as e:
        error_message = f"❌ Ошибка при экспорте базы данных: {str(e)}"
        logger.error(error_message)
        logger.exception("Детали ошибки:")
        await message.answer(error_message)


@router.message(Command("export_panel"))
async def export_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    users_x3 = await x3.get_all_panel()
    total = len(users_x3)
    await message.answer(f"{total} - всего юзеров в панели. Формирую Excel...")

    if not users_x3:
        await message.answer("Нет пользователей для экспорта.")
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "panel_users"

    # Заголовки
    headers = [
        "username", "telegramId", "expireAt",
        "shortUuid", "vlessUuid", "trojanPassword", "ssPassword",
        "description", "squad_uuid"
    ]
    ws.append(headers)

    # Стили
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                         top=Side(style='thin'), bottom=Side(style='thin'))

    # Заголовки форматируем
    for col_num, title in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=title)
        cell.alignment = header_alignment
        cell.border = thin_border

    # Заполнение данными
    for user in users_x3:
        # Извлекаем squad (первый элемент списка activeInternalSquads, если есть)
        squad_name = ""
        squad_uuid = ""
        if user.get('activeInternalSquads') and len(user['activeInternalSquads']) > 0:
            squad = user['activeInternalSquads'][0]
            squad_name = squad.get('name', '')
            squad_uuid = squad.get('uuid', '')

        # Форматируем даты (если есть)
        def format_date(dt_str):
            if dt_str:
                try:
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    return dt_str
            return ""

        row_data = [
            user.get('username', ''),
            user.get('telegramId', ''),
            format_date(user.get('expireAt')),
            user.get('shortUuid', ''),
            user.get('vlessUuid', ''),
            user.get('trojanPassword', ''),
            user.get('ssPassword', ''),
            user.get('description', ''),
            squad_uuid
        ]
        ws.append(row_data)

    # Автоширина колонок
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 50)

    # Заморозка заголовка
    ws.freeze_panes = 'A2'

    wb.save('panel.xlsx')

    # Отправляем файл
    from aiogram.types import BufferedInputFile
    await message.answer_document(
        document=FSInputFile('panel.xlsx',
        filename=f"panel_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"),
        caption=f"📊 Выгружено пользователей из панели: {total}"
    )

    logger.info(f"Администратор {message.from_user.id} выгрузил список пользователей панели")
