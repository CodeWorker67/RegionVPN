import urllib.parse

from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto

from bot import sql, x3
from keyboard import (
    keyboard_import_os,
    keyboard_import_app,
    keyboard_import_sub,
    keyboard_import_end,
    create_kb,
    BTN_BACK,
)
from lexicon import lexicon

router: Router = Router()

OS_CALLBACKS = {'import_android', 'import_ios', 'import_windows', 'import_macos'}

HAPP_PHOTOS = [
    'AgACAgIAAxkBAAIPmWnEKQRBvj4RG0McyGUKCyfy2MMAA84Zaxu4bCFK9rcoMhDWNSsBAAMCAAN5AAM6BA',
    'AgACAgIAAxkBAAIPu2nEKRIZIT3pNE9gsRkj4-_MVw1zAALPGWsbuGwhStCMPo97YAbTAQADAgADeQADOgQ',
]

V2_PHOTOS = [
    'AgACAgIAAxkBAAIQf2nEKWepYcZqa1QUuJJFas95QQVfAALTGWsbuGwhSv7MqSbIZegwAQADAgADeQADOgQ',
    'AgACAgIAAxkBAAIQk2nEKW9WBjzeB5iQ4zt4VKimPHEFAALUGWsbuGwhSvPA4dR652E3AQADAgADeQADOgQ',
    'AgACAgIAAxkBAAIQnmnEKXWEhq62u6Oxqgk-VeDVASFPAALVGWsbuGwhSvRfGK_Pm9yCAQADAgADeQADOgQ',
]

OS_DISPLAY = {
    'android': '🟢 Android',
    'ios': '📱 iOS',
    'windows': '🪟 Windows',
    'macos': '💻 MacOS',
}

APP_DISPLAY = {
    'happ': '✨ Happ',
    'v2': '📶 V2raytun',
}

IMPORT_URLS = {
    'android': {
        'happ': {
            'url_app': 'https://play.google.com/store/apps/details?id=com.happproxy',
            'url_import': 'happ://add/{sub_link}',
        },
        'v2': {
            'url_app': 'https://play.google.com/store/apps/details?id=com.v2raytun.android',
            'url_import': 'v2raytun://import/{sub_link}',
        },
    },
    'ios': {
        'happ': {
            'url_app': 'https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973',
            'url_import': 'happ://add/{sub_link}',
        },
        'v2': {
            'url_app': 'https://apps.apple.com/app/v2raytun/id6476628951',
            'url_import': 'v2raytun://import/{sub_link}',
        },
    },
    'windows': {
        'happ': {
            'url_app': 'https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe',
            'url_import': 'happ://add/{sub_link}',
        },
        'v2': {
            'url_app': 'https://v2raytun.com/',
            'url_import': 'v2raytun://import/{sub_link}',
        },
    },
    'macos': {
        'happ': {
            'url_app': 'https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973',
            'url_import': 'happ://add/{sub_link}',
        },
        'v2': {
            'url_app': 'https://apps.apple.com/ru/app/v2raytun/id6476628951',
            'url_import': 'v2raytun://import/{sub_link}',
        },
    },
}


@router.callback_query(F.data == 'import')
async def import_select_os(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        text=lexicon['import_start'],
        reply_markup=keyboard_import_os()
    )


@router.callback_query(F.data.in_(OS_CALLBACKS))
async def import_select_app(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        text=lexicon['import_select_app'],
        reply_markup=keyboard_import_app(callback.data)
    )


@router.callback_query(
    F.data.startswith('import_') &
    (F.data.endswith('_happ') | F.data.endswith('_v2'))
)
async def import_select_sub(callback: CallbackQuery):
    await callback.answer()
    user_data = await sql.get_user(callback.from_user.id)
    has_casual = has_white = False
    if user_data:
        if user_data[9]:
            has_casual = True
        if user_data[10]:
            has_white = True

    if not has_casual and not has_white:
        await callback.message.answer(
            text=lexicon['no_sub'],
            reply_markup=create_kb(1, back_to_main=BTN_BACK)
        )
        return

    await callback.message.answer(
        text=lexicon['import_select_sub'],
        reply_markup=keyboard_import_sub(callback.data, has_casual, has_white)
    )


@router.callback_query(
    F.data.startswith('import_') &
    (F.data.endswith('_casual') | F.data.endswith('_white'))
)
async def import_end(callback: CallbackQuery):
    await callback.answer()
    user_id = str(callback.from_user.id)

    if callback.data.endswith('_white'):
        sub_url = await x3.sublink(user_id + '_white')
        label = '📱 Мобильный тариф'
    else:
        sub_url = await x3.sublink(user_id)
        label = '🔗 Подписка Регион VPN'

    if not sub_url:
        await callback.message.answer(
            lexicon['import_error_link'],
            reply_markup=create_kb(1, back_to_main=BTN_BACK),
        )
        return

    parts = callback.data.split('_')
    os_key = parts[1]
    app_key = parts[2]

    urls = IMPORT_URLS[os_key][app_key]
    url_app = urls['url_app']

    if app_key == 'happ':
        lexicon_key = 'import_end_happ'
        photos = HAPP_PHOTOS
    else:
        lexicon_key = 'import_end_v2'
        photos = V2_PHOTOS

    caption = lexicon[lexicon_key].format(
        os=OS_DISPLAY[os_key],
        app=APP_DISPLAY[app_key],
        label=label,
        url_app=url_app,
        url_import=sub_url,
    )

    media = [InputMediaPhoto(media=file_id) for file_id in photos]
    media[0] = InputMediaPhoto(media=photos[0], caption=caption, parse_mode='HTML')

    await callback.message.answer_media_group(media=media)


