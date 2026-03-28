import time
import requests

from bot import sql, x3, bot
from config import CHANEL_ID, ADMIN_IDS, BOT_URL
from keyboard import (keyboard_start, keyboard_start_bonus, keyboard_tariff_bonus, keyboard_tariff,
                      keyboard_subscription, ref_keyboard, keyboard_gift_tariff, keyboard_payment_method,
                      chanel_keyboard, keyboard_tariff_old, keyboard_inline_ref,
                      create_kb, BTN_BACK, keyboard_sub_after_free)
from logging_config import logger
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated, InlineQuery, InlineQueryResultArticle, \
    InputTextMessageContent
from aiogram.filters import ChatMemberUpdatedFilter, KICKED, MEMBER, Command
from lexicon import lexicon


router: Router = Router()


# Этот хэндлер срабатывает на команду /start
@router.message(Command(commands="start"))
async def process_start_command(message: Message, command: Command):

    user_data = await sql.get_user(message.from_user.id)
    in_panel = False
    ref_login = ''
    existing = False
    stamp = ''
    ttclid = None

    if user_data:
        in_panel = user_data[4]
        existing = True

    if len(message.text.split(' ')) == 1:
        if user_data:
            logger.info(f'Юзер {message.from_user.id} - {message.from_user.username} нажал старт повторно')
        else:
            logger.success(f'Юзер {message.from_user.id} - {message.from_user.username} зашел в бота в первый раз')

    else:
        if 'ref' in message.text:
            if user_data:
                logger.info(f'Юзер {message.from_user.id} - {message.from_user.username} нажал старт повторно с реферальной ссылкой')
            else:
                logger.success(
                    f'Юзер {message.from_user.id} - {message.from_user.username} зашел в бота в первый раз по реферальной ссылкой')
                ref_login = message.text.split(' ')[1].replace('ref', '')

        elif 'gift_' in message.text:
            logger.info(
                f'Юзер {message.from_user.id} - {message.from_user.username} пытается активировать подарочную подписку')
            gift_id = message.text.split(' ')[1].replace('gift_', '')
            in_panel = await activate_gift(message, gift_id)
            await asyncio.sleep(2)
            existing = True
        elif 'ttclid_' in message.text:
            if user_data:
                logger.info(f'Юзер {message.from_user.id} - {message.from_user.username} нажал старт повторно с меткой ttclid')
            else:
                logger.success(
                    f'Юзер {message.from_user.id} - {message.from_user.username} зашел в бота в первый раз по метке ttclid')
                stamp = 'YuraTT'
                ttclid = message.text.split(' ')[1].replace('ttclid_', '').replace('_', '.')

                payload = {
                    'event_source': 'web',
                    'event_source_id': 'D5U8OFJC77U9E3ANE170',
                    'data': [
                        {
                            'event': 'Subscribe',
                            'event_time': int(time.time()),
                            'context': {
                                'ad': {
                                    'callback': ttclid
                                }
                            }
                        }
                    ]
                }
                response = requests.post(
                    'https://business-api.tiktok.com/open_api/v1.3/event/track/',
                    json=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'Access-Token': '7a9d82c42eaccd2393b74f31975fb8cc96bbb5d6'
                    },
                    timeout=2
                )

                if response.status_code == 200:
                    logger.success('Пиксель успешно отправлен в TikTok')
                else:
                    logger.error(f'Ошибка TikTok API: статус {response.status_code}, ответ: {response.text}')
        else:
            if user_data:
                logger.info(f'Юзер {message.from_user.id} - {message.from_user.username} нажал старт повторно с меткой')
            else:
                logger.success(
                    f'Юзер {message.from_user.id} - {message.from_user.username} зашел в бота в первый раз по метке')
                stamp = message.text.split(' ')[1]

    if not existing:
        inserted = await sql.add_user(message.from_user.id, False, False, ref=ref_login, stamp=stamp)
        if inserted:
            logger.info(f'Юзер {message.from_user.id} - {message.from_user.username} добавлен в БД')
        if ttclid:
            await sql.update_ttclid(message.from_user.id, ttclid)
            logger.info(f'Юзеру {message.from_user.id} - {message.from_user.username} присвоен ttclid')

    if not in_panel:
        await message.answer(text=lexicon['start_bonus'],
                             reply_markup=keyboard_start_bonus(),
                             disable_web_page_preview=True)
    else:
        await message.answer(text=lexicon['start'],
                             reply_markup=keyboard_start(),
                             disable_web_page_preview=True)


@router.callback_query(F.data == 'buy_vpn')
async def buy_vpn_cb(callback: CallbackQuery):
    await callback.answer()
    user_data = await sql.get_user(callback.from_user.id)
    in_panel = False

    if user_data is not None and len(user_data) > 4:
        in_panel = user_data[4]

    result_active = await x3.activ(str(callback.from_user.id))

    if result_active['activ'] == '🔎 - Не подключён' and not in_panel:
        await callback.message.answer(text=lexicon['buy'],
                                      reply_markup=keyboard_tariff_bonus(),
                                      disable_web_page_preview=True)
    else:
        await callback.message.answer(text=lexicon['buy'],
                                      reply_markup=keyboard_tariff(),
                                      disable_web_page_preview=True)


@router.callback_query(F.data == 'connect_vpn')
async def direct_connect_vpn_cb(callback: CallbackQuery):
    # await x3.test_connect()
    user_id = str(callback.from_user.id)
    sub_url = await x3.sublink(user_id)
    sub_url_white = None
    user_data = await sql.get_user(callback.from_user.id)
    if user_data[10]:
        user_id_white = user_id + '_white'
        sub_url_white = await x3.sublink(user_id_white)

    if not sub_url and not sub_url_white:
        await callback.message.answer(lexicon['no_sub'])
        return

    await callback.message.answer(
        text=lexicon['to_sub'],
        reply_markup=keyboard_subscription(sub_url, sub_url_white),
        disable_web_page_preview=True
    )
    await callback.answer()


@router.callback_query(F.data.in_({'r_7', 'r_30', 'r_90', 'r_240', 'r_white_30'}))
async def process_payment_method(callback: CallbackQuery):
    await callback.answer()
    text = lexicon['payment_link']
    if 'white' in callback.data:
        await sql.add_white_counter_if_not_exists(callback.from_user.id)
        text = lexicon['payment_link_white']
    text += '\n\nВыберите способ оплаты:'
    tariff = callback.data
    await callback.message.answer(text, reply_markup=keyboard_payment_method(tariff))


@router.callback_query(F.data == 'free_vpn')
async def free_vpn_cb(callback: CallbackQuery):
    day = 5

    user_data = await sql.get_user(callback.from_user.id)
    in_panel = False
    if user_data is not None and len(user_data) > 4:
        in_panel = user_data[4]
    if in_panel:
        await callback.message.answer(text=lexicon['free_vpn_no'],
                                      reply_markup=keyboard_start())
        return
    # Проверка на наличие данных
    # await x3.test_connect()
    logger.info(await x3.addClient(day, str(callback.from_user.id), int(callback.from_user.id)))
    result_active = await x3.activ(str(callback.from_user.id))
    time = result_active['time']

    # Проверка на наличие данных
    if await sql.get_user(callback.from_user.id) is not None:
        await sql.update_in_panel(callback.from_user.id)
    else:
        await sql.add_user(callback.from_user.id, True)
    user_id = str(callback.from_user.id)
    sub_url = await x3.sublink(user_id)

    await callback.message.answer(text=lexicon['buy_success'].format(time, sub_url),
                                  reply_markup=keyboard_sub_after_free(sub_url),
                                  disable_web_page_preview=True)



@router.callback_query(F.data == 'info')
async def faq(callback: CallbackQuery):
    await callback.answer()
    user_data = await sql.get_user(callback.from_user.id)
    in_panel = False
    if user_data is not None and len(user_data) > 4:
        in_panel = user_data[4]
    if in_panel:
        await callback.message.answer(
            text=lexicon['start'],
            reply_markup=keyboard_start(),
            disable_web_page_preview=True
        )
    else:
        await callback.message.answer(
            text=lexicon['start_bonus'],
            reply_markup=keyboard_start_bonus(),
            disable_web_page_preview=True
        )


@router.callback_query(F.data == 'ref')
async def referral_program(callback: CallbackQuery):
    await callback.answer()
    count = await sql.select_ref_count(int(callback.from_user.id))
    await callback.message.answer(
        text=lexicon['ref_info'].format(count, callback.from_user.id),
        reply_markup=ref_keyboard(callback.from_user.id),
        disable_web_page_preview=True
    )


@router.callback_query(F.data == 'buy_gift')
async def gift_subscription_start(callback: CallbackQuery):
    await callback.answer()
    """Начало процесса подарка подписки"""
    await callback.message.answer(
        lexicon['gift_start'],
        reply_markup=keyboard_gift_tariff()
    )


@router.callback_query(F.data.startswith('gift_'))
async def process_gift_payment_method(callback: CallbackQuery):
    await callback.answer()
    text = lexicon['payment_link']
    if 'white' in callback.data:
        await sql.add_white_counter_if_not_exists(callback.from_user.id)
        text = lexicon['payment_link_white']
    tariff = callback.data
    text += '\n\nВыберите способ оплаты <b>подарочной подписки</b>:'
    await callback.message.answer(text, reply_markup=keyboard_payment_method(tariff))


async def activate_gift(message: Message, gift_id: str):
    """Активация подарка по gift_id"""
    result = await sql.activate_gift(gift_id, message.from_user.id)

    if not result[0]:
        await message.answer(lexicon['gift_no'])
        logger.warning(f'Ссылка на подарок протухла')
        if await sql.get_user(message.from_user.id) is None:
            await sql.add_user(message.from_user.id, False)
            logger.success(
                f'Юзер {message.from_user.id} - {message.from_user.username} зашел в бота в первый раз по подарочной ссылке')
        return False

    duration = result[1]
    white_flag = result[2]

    # Активируем подписку для получателя
    # await x3.test_connect()
    user_id = message.from_user.id
    user_id_str = str(message.from_user.id)
    if white_flag:
        user_id_str += '_white'

    was_in_db = await sql.get_user(message.from_user.id) is not None
    if not was_in_db:
        await sql.add_user(message.from_user.id, False)


    # Проверяем существует ли пользователь
    existing_user = await x3.get_user_by_username(user_id_str)

    if existing_user and 'response' in existing_user and existing_user['response']:
        response = await x3.updateClient(duration, user_id_str, user_id)
    else:
        response = await x3.addClient(duration, user_id_str, user_id)

    if response:
        # Получаем информацию о подписке
        result_active = await x3.activ(user_id_str)
        subscription_time = result_active.get('time', '-')

        # Обновляем базу данных
        await sql.update_in_panel(message.from_user.id)
        if was_in_db:
            logger.info(
                f'Юзер {message.from_user.id} - {message.from_user.username} получил в подарок подписку, уже был в БД')
        else:
            logger.success(
                f'Юзер {message.from_user.id} - {message.from_user.username} зашел в бота в первый раз и получил подарочную подписку')

        # Отправляем сообщение получателю
        await message.answer(lexicon['gift_yes'].format(duration, subscription_time))
        return True

    else:
        await message.answer(lexicon['gift_error'])
        if await sql.get_user(message.from_user.id) is None:
            await sql.add_user(message.from_user.id, False)
        return False


@router.callback_query(F.data == 'video_faq')
async def video_faq(callback: CallbackQuery):
    await callback.message.answer_video(
        video='BAACAgIAAxkBAAECpqNpqrDnzrb_G1rcEtZli39lGgVpMAACa5sAAl9MWUmxYN_rJYzPVToE',
        caption=lexicon['video_faq_caption'],
        reply_markup=create_kb(1, back_to_main=BTN_BACK),
    )


@router.callback_query(F.data == 'back_to_buy_menu')
async def handle_back_to_menu(callback: CallbackQuery):
    """Обработчик для возврата в главное меню из оплаты"""
    await callback.message.answer(text=lexicon['buy'], reply_markup=keyboard_tariff())


@router.callback_query(F.data == 'back_to_main')
async def handle_back_to_menu(callback: CallbackQuery):
    """Обработчик для возврата в главное меню из оплаты"""
    await callback.message.answer(text=lexicon['start'],
                                  reply_markup=keyboard_start(),
                                  disable_web_page_preview=True)


@router.callback_query(F.data == 'back_to_gift_menu')
async def handle_back_to_menu(callback: CallbackQuery):
    """Обработчик для возврата в главное меню из оплаты"""
    await callback.message.edit_text(text=lexicon['gift_start'], reply_markup=keyboard_gift_tariff())


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def user_blocked_bot(event: ChatMemberUpdated):
    await sql.update_delete(event.from_user.id, True)
    logger.warning(f'Юзер {event.from_user.id} заблокировал бота')


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER))
async def user_unblocked_bot(event: ChatMemberUpdated):
    await sql.update_delete(event.from_user.id, False)
    logger.success(f'Юзер {event.from_user.id} разблокировал бота')


@router.chat_member()
async def handle_chat_member_update(update: ChatMemberUpdated):
    if str(update.chat.id) != str(CHANEL_ID):
        return
    user_id = update.new_chat_member.user.id
    user_dct = await sql.get_user(user_id)

    if not user_dct:
        logger.warning(f"User in chanel {user_id} not found in database")
        return

    if update.old_chat_member.status == "left" and update.new_chat_member.status == "member":
        await sql.update_in_chanel(user_id, True)
        logger.success(f"User {user_id} connect to chanel")
    elif update.old_chat_member.status != "left" and update.new_chat_member.status == "left":
        await sql.update_in_chanel(user_id, False)
        logger.warning(f"User {user_id} left chanel")


@router.inline_query(lambda query: query.query == 'partner')
async def inline_partner(inline_query: InlineQuery):
    user_id = inline_query.from_user.id

    text = f'''
Привет. Подключись к <b>Регион VPN</b> по моей ссылке:

{BOT_URL}?start=ref{user_id}

⚡ Высокая скорость канала, надёжные сервера
🛡 Защита данных, без искусственных лимитов по трафику
📱 До 3 устройств одновременно
    '''

    result = InlineQueryResultArticle(
        id="1",
        title='🤝🤝🤝 Приглашение',
        description="Друг, перешедший по этой кнопке станет Вашим рефералом.",
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode='HTML',
            disable_web_page_preview=False
        ),
        reply_markup=keyboard_inline_ref(user_id),
        thumb_url="https://img.freepik.com/premium-photo/glowing-blue-neon-wifi-signal-icon-dark-background_989822-6238.jpg?semt=ais_hybrid"  # опционально: иконка
    )

    # Отправляем результат обратно в Telegram
    await bot.answer_inline_query(
        inline_query.id,
        results=[result],
        cache_time=0
    )