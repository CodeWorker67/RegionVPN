import asyncio

from bot import x3, sql
from logging_config import logger


async def check_connect():
    """Проверка подключившихся пользователей к впн и обновление в базе Is_pay_null"""

    await x3.test_connect()
    lst_active = await x3.activ_list()
    logger.info(f'Всего активных юзеров - {len(lst_active)}')

    cnt = 0
    for user_id in lst_active:
        user_data = await sql.get_user(user_id)
        if user_data is not None:
            if not user_data[5]:
                try:
                    await sql.update_is_connect(user_id, True)
                    logger.info(f'{user_id} подключался к ВПН')
                    cnt += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.error(e)
    logger.info(f'Обновлено в БД - {cnt}')
