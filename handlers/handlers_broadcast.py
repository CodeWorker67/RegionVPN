import urllib.parse

from bot import sql
from config import ADMIN_IDS, BOT_URL
from keyboard import create_kb, keyboard_tariff, STYLE_PRIMARY, STYLE_SUCCESS, BTN_BACK
from logging_config import logger
import asyncio
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


router = Router()


class BroadcastState(StatesGroup):
    waiting_for_message = State()
    waiting_for_parameter = State()
    waiting_for_parameter_value = State()
    confirm_send = State()


@router.message(Command(commands=['broadcast']))
async def broadcast_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:  # Проверка прав администратора из базы данных
        back_button_keyboard = create_kb(1, broadcast_cancel=BTN_BACK)
        await message.answer("Отправьте сообщение для рассылки или нажмите «◀️ Назад» для отмены.",
                             reply_markup=back_button_keyboard)
        await state.set_state(BroadcastState.waiting_for_message)
    else:
        await message.answer("Эта команда доступна только администраторам.")


# Обработка сообщения для рассылки
@router.message(BroadcastState.waiting_for_message)
async def broadcast_waiting_for_message(message: Message, state: FSMContext):
    # Проверяем тип контента
    if message.content_type not in [
        ContentType.TEXT,
        ContentType.PHOTO,
        ContentType.VIDEO,
        ContentType.DOCUMENT,
        ContentType.VOICE,
        ContentType.AUDIO,
        ContentType.ANIMATION,
        ContentType.STICKER
    ]:
        await message.answer("Этот тип контента не поддерживается для рассылки.")
        return
    elif message.content_type == ContentType.TEXT:
        mes = await message.answer(message.text, disable_web_page_preview=True)
        await state.update_data(
            broadcast_message_id=mes.message_id,
            broadcast_chat_id=mes.chat.id,
            broadcast_content_type=mes.content_type
        )
    else:
        # Сохраняем сообщение (включая тип контента) в состоянии
        await state.update_data(
            broadcast_message_id=message.message_id,
            broadcast_chat_id=message.chat.id,
            broadcast_content_type=message.content_type
        )

    # Запрашиваем список доступных параметров из базы данных
    parameters = sql.get_parameters()  # Эта функция должна возвращать список доступных параметров
    parameters_text = "\n".join(parameters)  # Преобразуем список в строку для отображения
    await message.answer(
        f"Теперь выберите параметр из следующего списка:\n{parameters_text}\nИли нажмите «◀️ Назад» для отмены.")

    await state.set_state(BroadcastState.waiting_for_parameter)


# Обработчик для выбора параметра
@router.message(BroadcastState.waiting_for_parameter)
async def process_parameter(message: Message, state: FSMContext):
    selected_parameter = message.text
    available_parameters = sql.get_parameters()  # Получаем список доступных параметров для проверки

    if selected_parameter not in available_parameters:
        await message.answer("Ошибка: выбранный параметр недействителен. Пожалуйста, выберите из списка.")
        return

    # Сохраняем выбранный параметр в состоянии
    await state.update_data(selected_parameter=selected_parameter)

    await confirm_broadcast(message, state)


async def confirm_broadcast(message: Message, state: FSMContext):
    # Получаем пользователей по выбранному параметру и значению, если это не "Все пользователи"
    data = await state.get_data()
    selected_parameter = data.get('selected_parameter')
    user_ids = []
    if selected_parameter == "all_users":
        user_ids = await sql.select_all_users()  # Получаем всех пользователей
    elif selected_parameter == 'not_connected_subscribe_yes':
        user_ids = await sql.select_not_connected_subscribe_yes()
    elif selected_parameter == 'not_connected_subscribe_off':
        user_ids = await sql.select_not_connected_subscribe_off()
    elif selected_parameter == 'connected_subscribe_off':
        user_ids = await sql.select_connected_subscribe_off()
    elif selected_parameter == 'connected_subscribe_yes':
        user_ids = await sql.select_connected_subscribe_yes()
    elif selected_parameter == 'not_subscribed':
        user_ids = await sql.select_subscribe_off()
    elif selected_parameter == 'subscribed':
        user_ids = await sql.select_subscribe_yes()
    elif selected_parameter == 'connected_never_paid':
        user_ids = await sql.select_connected_never_paid()

    if not user_ids:
        await message.answer("Нет пользователей, соответствующих выбранному параметру и значению.")
        await state.clear()
        return

    # Создаем клавиатуру для подтверждения
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить", callback_data="Подтвердить", style="success")],
        [InlineKeyboardButton(text=BTN_BACK, callback_data="broadcast_cancel")],
    ])

    await message.answer("Подтвердите отправку сообщения выбранным пользователям или нажмите «◀️ Назад» для отмены.\n"
                         f"{selected_parameter} - {len(user_ids)}",
                         reply_markup=confirm_keyboard)
    await state.set_state(BroadcastState.confirm_send)


@router.callback_query(F.data == 'Подтвердить', StateFilter(BroadcastState.confirm_send))
async def broadcast_confirm_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    broadcast_message_id = data.get('broadcast_message_id')
    broadcast_chat_id = data.get('broadcast_chat_id')
    broadcast_content_type = data.get('broadcast_content_type')
    selected_parameter = data.get('selected_parameter')

    # Проверка наличия сообщения для отправки
    if not broadcast_message_id or not broadcast_chat_id or not broadcast_content_type:
        await callback.message.edit_text("Ошибка: сообщение не найдено. Отправка прервана.")
        await state.clear()
        return
    user_ids = []
    keyboard_broadcast = None
    # Получаем пользователей по выбранному параметру
    if selected_parameter == "all_users":
        user_ids = await sql.select_all_users()  # Получаем всех пользователей
        keyboard_broadcast = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛍️ Купить подписку",
                        callback_data="buy_vpn",
                        style=STYLE_SUCCESS,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🌐 Наш сайт",
                        url="https://4region.top",
                        style=STYLE_PRIMARY,
                    )
                ],
            ]
        )
    elif selected_parameter == 'not_connected_subscribe_yes':
        user_ids = await sql.select_not_connected_subscribe_yes()
        keyboard_broadcast = create_kb(
            1,
            styles={'connect_vpn': STYLE_PRIMARY},
            connect_vpn='📡 Подключить Регион VPN',
        )
    elif selected_parameter == 'not_connected_subscribe_off':
        user_ids = await sql.select_not_connected_subscribe_off()
        keyboard_broadcast = create_kb(1, styles={'buy_vpn': STYLE_PRIMARY}, buy_vpn='🛍️ Купить подписку')
    elif selected_parameter == 'connected_subscribe_off':
        user_ids = await sql.select_connected_subscribe_off()
        keyboard_broadcast = create_kb(1, styles={'buy_vpn': STYLE_PRIMARY}, buy_vpn='🛍️ Купить подписку')
    elif selected_parameter == 'connected_subscribe_yes':
        user_ids = await sql.select_connected_subscribe_yes()
        keyboard_broadcast = None
    elif selected_parameter == 'not_subscribed':
        user_ids = await sql.select_subscribe_off()
        keyboard_broadcast = create_kb(
            1,
            styles={'free_vpn': STYLE_SUCCESS},
            free_vpn='🎯 Попробовать бесплатно',
        )
    elif selected_parameter == 'subscribed':
        user_ids = await sql.select_subscribe_yes()
        keyboard_broadcast = keyboard_tariff()
    elif selected_parameter == 'connected_never_paid':
        user_ids = await sql.select_connected_never_paid()
        keyboard_broadcast = keyboard_tariff()

    # Проверяем, есть ли пользователи для отправки
    if not user_ids:
        await callback.message.edit_text("Нет пользователей, соответствующих выбранному параметру и значению.")
        await state.clear()
        return
    count = 0
    # Отправляем сообщение пользователям
    user_ids.append(1012882762)
    for user_id in user_ids:
        try:
            keyboard_broadcast = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                InlineKeyboardButton(
                    text="Поделиться 💬",
                    url=f"https://t.me/share/url?url={BOT_URL}?start=ref{user_id}&text={urllib.parse.quote('Вот ссылка для тебя на надежный VPN!')}",
                    style=STYLE_SUCCESS,
                )
            ]
            ]
            )
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=broadcast_chat_id,
                message_id=broadcast_message_id,
                reply_markup=keyboard_broadcast,
            )
            await sql.update_broadcast_status(user_id, 'sent')  # Успешная отправка
            await asyncio.sleep(0.05)
            count += 1
        except Exception as e:
            await sql.update_broadcast_status(user_id, 'failed')  # Ошибка отправки
            logger.error(f"Failed to send message to {user_id}: {e}")
    logger.success(f"Send broadcast to {count} users")

    await callback.message.edit_text(f"Сообщение успешно отправлено {count} пользователям.")
    await state.clear()


# Обработка отмены рассылки
@router.callback_query(F.data == 'broadcast_cancel')
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state in [BroadcastState.confirm_send, BroadcastState.waiting_for_message]:
        await callback.message.edit_text("Рассылка отменена.")
        await state.clear()
    else:
        await callback.answer("Отмена завершена.")
