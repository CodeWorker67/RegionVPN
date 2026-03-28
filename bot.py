from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from X3 import X3
from config import TG_TOKEN
from typing import Optional
from config_bd.utils import AsyncSQL

# Инициализация бота Telegram и классов БД и панели
bot: Optional[Bot] = Bot(token=TG_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
x3: Optional[X3] = X3()
sql: Optional[AsyncSQL] = AsyncSQL()


async def get_bot_username():
    # Получаем информацию о боте
    bot_user = await bot.get_me()
    if bot_user:
        return bot_user.username
    else:
        return 'None'