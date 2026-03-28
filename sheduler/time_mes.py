import asyncio
from datetime import datetime
from aiogram import Bot

from bot import sql, x3
from keyboard import keyboard_tariff, keyboard_tariff_trial, create_kb, STYLE_PRIMARY
from lexicon import lexicon
from logging_config import logger


async def send_message_cron(bot: Bot):
    all_users = await sql.select_all_users()
    await bot.send_message(1012882762, 'Начинаю ежедневную рассылку')
    sent_count_7 = 0
    sent_count_3 = 0
    sent_count_1 = 0
    sent_count_0 = 0
    sent_count_week = 0
    sent_count_second_chance = 0
    failed_count = 0
    for user_id in all_users:
        end_date = None  # Инициализация переменной перед блоком try
        try:
            # Если метод get_subscription_end_date не асинхронный, убираем await
            end_date = await sql.get_subscription_end_date(user_id)
            user_data = await sql.get_user(user_id)
            is_pay_flag = user_data[8]
            second_chance_flag = user_data[15]
            if end_date:
                if isinstance(end_date, datetime):
                    end_date = end_date.date()  # Приводим к типу date, если это datetime
                today = datetime.now().date()  # Приводим текущую дату и время к типу date
                days_left = (end_date - today).days
                if is_pay_flag:
                    keyboard = keyboard_tariff()
                else:
                    keyboard = keyboard_tariff_trial()
                if days_left == 7 and not await sql.notification_sent_today(user_id):
                    await bot.send_message(chat_id=user_id, text=lexicon['push_7'], reply_markup=keyboard)
                    await asyncio.sleep(0.05)
                    await sql.mark_notification_as_sent(user_id)
                    sent_count_7 += 1
                elif days_left == 3 and not await sql.notification_sent_today(user_id):
                    await bot.send_message(chat_id=user_id, text=lexicon['push_3'], reply_markup=keyboard)
                    await asyncio.sleep(0.05)
                    await sql.mark_notification_as_sent(user_id)
                    sent_count_3 += 1
                elif days_left == 1 and not await sql.notification_sent_today(user_id):
                    await bot.send_message(chat_id=user_id, text=lexicon['push_1'], reply_markup=keyboard)
                    await asyncio.sleep(0.05)
                    await sql.mark_notification_as_sent(user_id)
                    sent_count_1 += 1
                elif days_left == 0 and not await sql.notification_sent_today(user_id):
                    await bot.send_message(chat_id=user_id, text=lexicon['push_0'], reply_markup=keyboard)
                    await asyncio.sleep(0.05)
                    await sql.mark_notification_as_sent(user_id)
                    sent_count_0 += 1
                elif days_left < 0:
                    if days_left == -7 and not second_chance_flag:

                        await bot.send_message(chat_id=user_id,
                                               text=lexicon['second_chance_message'],
                                               reply_markup=create_kb(
                                                   1,
                                                   styles={'connect_vpn': STYLE_PRIMARY},
                                                   connect_vpn='📡 Подключить Регион VPN',
                                               ))

                        user_id_str = str(user_id)
                        try:
                            response = await x3.updateClient(3, user_id_str, user_id)
                            if response:
                                result_active = await x3.activ(user_id_str)
                                subscription_time = result_active.get('time', '-')
                                if subscription_time != '-':
                                    try:
                                        new_end_date = datetime.strptime(subscription_time, '%d-%m-%Y %H:%M МСК')
                                        await sql.update_subscription_end_date(user_id, new_end_date)
                                        logger.info(f"✅ Дата подписки для {user_id} обновлена после second_chance")
                                    except ValueError as e:
                                        logger.error(f"Ошибка парсинга даты second_chance для {user_id}: {e}")
                            else:
                                logger.error(f"❌ Не удалось добавить 3 дня пользователю {user_id} (second_chance)")
                        except Exception as e:
                            logger.error(f"Ошибка при добавлении 3 дней пользователю {user_id}: {e}")

                        ttclid_value = f"second_chance_{today.strftime('%d%m%y')}"
                        try:
                            await sql.update_ttclid(user_id, ttclid_value)
                            logger.info(f"✅ ttclid для {user_id} установлен: {ttclid_value}")
                        except Exception as e:
                            logger.error(f"Ошибка обновления ttclid для {user_id}: {e}")

                        sent_count_second_chance += 1

                    else:
                        last_notification_date = await sql.get_last_notification_date(user_id)
                        if last_notification_date:
                            if isinstance(last_notification_date, datetime):
                                last_notification_date = last_notification_date.date()
                        # Проверяем, прошло ли 3 дней с момента последнего уведомления
                        if not last_notification_date or (today - last_notification_date).days >= 3:
                            await bot.send_message(chat_id=user_id, text=lexicon['push_off'], reply_markup=keyboard)
                            await asyncio.sleep(0.05)
                            await sql.mark_notification_as_sent(user_id)
                            sent_count_week += 1
        except Exception:
            failed_count += 1

    await bot.send_message(1012882762, f'''
Рассылка об окончании подписки:
за 7 дней: {sent_count_7}
за 3 дня: {sent_count_3}
за 1 день: {sent_count_1}
за 0 дней: {sent_count_0}
после окончания каждые 3 дня: {sent_count_week}
повторный триал: {sent_count_second_chance}

Не получилось: {failed_count}
''')
    # Выводим обобщенную информацию в консоль
    logger.info(f"Уведомлений отправлено: {sent_count_7 + sent_count_3 + sent_count_1 + sent_count_0 +sent_count_week}")
    logger.info(f"Не удалось отправить уведомления: {failed_count}")
