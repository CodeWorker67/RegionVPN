from typing import List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CHANEL_URL, BOT_URL

# Единый текст «Назад» для импорта из других модулей
BTN_BACK = "◀️ Назад"

# Тексты кнопок перехода к оплате (эмодзи как у способов в keyboard_payment_method)
BTN_PAY_SBP = "🔹 Оплатить через СБП"
BTN_PAY_CARD_RF = "🏦 Оплатить по карте РФ"


def btn_pay_cryptobot(rub_amount: int) -> str:
    return f"🪙 Оплатить через Crypto bot · {rub_amount} ₽"

STYLE_PRIMARY = "primary"
STYLE_SUCCESS = "success"
STYLE_DANGER = "danger"


def create_kb(
    width: int,
    *,
    styles: Optional[dict[str, str]] = None,
    **kwargs: str,
) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру. kwargs: callback_data -> текст кнопки.
    styles: callback_data -> 'primary' | 'success' | 'danger' (цвет кнопки в клиентах Telegram).
    """
    kb_builder = InlineKeyboardBuilder()
    buttons: List[InlineKeyboardButton] = []
    style_map = styles or {}

    for button_data, button_text in kwargs.items():
        st = style_map.get(button_data)
        if st:
            buttons.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=button_data,
                    style=st,
                )
            )
        else:
            buttons.append(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=button_data,
                )
            )

    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


def chanel_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📣 Подписаться на канал",
                url=CHANEL_URL,
                style=STYLE_PRIMARY,
            )
        ]
    ])
    return keyboard


def keyboard_start_bonus():
    return create_kb(
        1,
        styles={"free_vpn": STYLE_SUCCESS, "buy_vpn": STYLE_SUCCESS},
        free_vpn="🎯 Попробовать бесплатно",
        buy_vpn="🛍️ Купить подписку",
    )


def keyboard_start():
    return create_kb(
        1,
        styles={
            "buy_vpn": STYLE_SUCCESS,
            "connect_vpn": STYLE_PRIMARY,
            "ref": STYLE_PRIMARY,
            "buy_gift": STYLE_SUCCESS,
        },
        buy_vpn="🛍️ Купить подписку",
        connect_vpn="📡 Подключить Регион VPN",
        ref="🔗 Реферальная программа",
        buy_gift="💝 Подарить подписку",
        # info="💡 Информация",
    )


_STYLES_TARIFF = {
    "r_7": STYLE_PRIMARY,
    "r_30": STYLE_PRIMARY,
    "r_90": STYLE_SUCCESS,
    "r_240": STYLE_SUCCESS,
    "r_white_30": STYLE_PRIMARY,
    "r_30old": STYLE_PRIMARY,
    "free_vpn": STYLE_SUCCESS,
}


def keyboard_tariff_bonus():
    return create_kb(
        1,
        styles=_STYLES_TARIFF,
        r_7="⚡ 7 дней - 99 руб",
        r_30="⭐ 30 дней - 199 руб",
        r_90="🔥 90 дней - 539 руб (выгода -10%)",
        r_240="🏆 240 дней - 999 руб (выгода -40%)",
        # r_white_30="📲 Мобильный тариф — 299 руб",
        free_vpn="🎁 ПОПРОБОВАТЬ 5 дней БЕСПЛАТНО 🎁",
        back_to_main=BTN_BACK,
    )


def keyboard_tariff():
    return create_kb(
        1,
        styles={k: v for k, v in _STYLES_TARIFF.items() if k != "free_vpn"},
        r_7="⚡ 7 дней - 99 руб",
        r_30="⭐ 30 дней - 199 руб",
        r_90="🔥 90 дней - 539 руб (выгода -10%)",
        r_240="🏆 240 дней - 999 руб (выгода -40%)",
        # r_white_30="📲 Мобильный тариф — 299 руб",
        back_to_main=BTN_BACK,
    )


def keyboard_tariff_trial():
    return create_kb(
        1,
        styles={k: v for k, v in _STYLES_TARIFF.items() if k != "free_vpn"},
        r_7="⚡ 7 дней - 99 руб",
        r_30="⭐ 30 дней - 199 руб",
        r_90="🔥 90 дней - 539 руб (выгода -10%)",
        r_240="🏆 240 дней - 999 руб (выгода -40%)",
        # r_white_30="📲 Мобильный тариф — 299 руб",
        back_to_main=BTN_BACK,
    )


def keyboard_tariff_old():
    return create_kb(
        1,
        styles={"r_30old": STYLE_PRIMARY},
        r_30old="⭐ 30 дней - 99 руб",
        back_to_main=BTN_BACK,
    )


_STYLES_GIFT = {
    "gift_r_7": STYLE_PRIMARY,
    "gift_r_30": STYLE_PRIMARY,
    "gift_r_90": STYLE_SUCCESS,
    "gift_r_240": STYLE_SUCCESS,
    "gift_r_white_30": STYLE_PRIMARY,
}


def keyboard_gift_tariff():
    return create_kb(
        1,
        styles=_STYLES_GIFT,
        gift_r_7="⚡ 7 дней - 99 руб",
        gift_r_30="⭐ 30 дней - 199 руб",
        gift_r_90="🔥 90 дней - 539 руб (выгода -10%)",
        gift_r_240="🏆 240 дней - 999 руб (выгода -40%)",
        # gift_r_white_30="📲 Мобильный тариф — 299 руб",
        back_to_main=BTN_BACK,
    )


def keyboard_subscription(sub_url, sub_url_white):
    buttons = []
    if sub_url:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔗 Подписка Регион VPN",
                    url=sub_url,
                    style=STYLE_PRIMARY,
                )
            ]
        )
    if sub_url_white:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📲 Мобильный тариф",
                    url=sub_url_white,
                    style=STYLE_PRIMARY,
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="🛟 Если страница не загружается",
                callback_data="import",
                style=STYLE_DANGER,
            )
        ]
    )
    buttons.append([InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def keyboard_import_os():
    return create_kb(
        1,
        styles={
            "import_android": STYLE_PRIMARY,
            "import_ios": STYLE_PRIMARY,
            "import_windows": STYLE_PRIMARY,
            "import_macos": STYLE_PRIMARY,
        },
        import_android="🟢 Android",
        import_ios="📱 iOS",
        import_windows="🪟 Windows",
        import_macos="💻 MacOS",
        back_to_main=BTN_BACK,
    )


def keyboard_import_app(os_callback: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ Happ",
                    callback_data=f"{os_callback}_happ",
                    style=STYLE_PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="📶 V2raytun",
                    callback_data=f"{os_callback}_v2",
                    style=STYLE_PRIMARY,
                )
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")],
        ]
    )


def keyboard_import_sub(app_callback: str, has_casual: bool, has_white: bool):
    buttons = []
    if has_casual:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔗 Подписка Регион VPN",
                    callback_data=f"{app_callback}_casual",
                    style=STYLE_PRIMARY,
                )
            ]
        )
    if has_white:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📲 Мобильный тариф",
                    callback_data=f"{app_callback}_white",
                    style=STYLE_PRIMARY,
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def keyboard_sub_after_buy(sub_url):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 В личный кабинет",
                    url=sub_url,
                    style=STYLE_PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛟 Если страница не загружается",
                    callback_data="import",
                    style=STYLE_DANGER,
                )
            ],
            [
                InlineKeyboardButton(
                    text="💝 Подарить подписку",
                    callback_data="buy_gift",
                    style=STYLE_SUCCESS,
                )
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")],
        ]
    )
    return keyboard


def keyboard_sub_after_free(sub_url):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 В личный кабинет",
                    url=sub_url,
                    style=STYLE_PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛟 Если страница не загружается",
                    callback_data="import",
                    style=STYLE_DANGER,
                )
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")],
        ]
    )
    return keyboard


def keyboard_payment_cancel():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍️ Купить подписку",
                    callback_data="buy_vpn",
                    style=STYLE_PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="💝 Подарить подписку",
                    callback_data="start_gift",
                    style=STYLE_SUCCESS,
                )
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")],
        ]
    )
    return keyboard


def keyboard_payment_method(tarif):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔹 СБП",
                    callback_data=f"sbp_{tarif}",
                    style=STYLE_SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏦 Карта РФ",
                    callback_data=f"card_{tarif}",
                    style=STYLE_PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐️ Telegram Stars",
                    callback_data=f"stars_{tarif}",
                    style=STYLE_PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🪙 Crypto bot",
                    callback_data=f"crypto_{tarif}",
                    style=STYLE_PRIMARY,
                )
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")],
        ]
    )
    return keyboard


def keyboard_payment_method_stock(tarif):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔹 СБП",
                    callback_data=f"sbp_{tarif}",
                    style=STYLE_SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏦 Карта РФ",
                    callback_data=f"card_{tarif}",
                    style=STYLE_PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐️ Telegram Stars",
                    callback_data=f"stars_{tarif}",
                    style=STYLE_PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🪙 Crypto bot",
                    callback_data=f"crypto_{tarif}",
                    style=STYLE_PRIMARY,
                )
            ],
        ]
    )
    return keyboard


def keyboard_payment_sbp(text, pay_url):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text,
                    url=pay_url,
                    style=STYLE_SUCCESS,
                )
            ]
        ]
    )


def keyboard_payment_stars(stars_amount):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Оплатить {stars_amount} ⭐️",
                    pay=True,
                    style=STYLE_SUCCESS,
                )
            ]
        ]
    )


def ref_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Пригласить друзей 🤝",
                    switch_inline_query="partner",
                    style=STYLE_SUCCESS,
                )
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")],
        ]
    )
    return keyboard


def keyboard_inline_ref(user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📡 Подключить Регион VPN",
                    url=f"{BOT_URL}?start=ref{user_id}",
                    style=STYLE_PRIMARY,
                )
            ]
        ]
    )


def keyboard_import_end(url_app: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬇️ Скачать приложение",
                    url=url_app,
                    style=STYLE_PRIMARY,
                )
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")],
        ]
    )
