import base64
import datetime
import hashlib
import hmac
import uuid

import urllib3
import aiohttp

from config import PANEL_API_TOKEN, PANEL_URL, TRUE_SUB_LINK, MIRROR_SUB_LINK, SHORT_UUID_SECRET
from config_bd.utils import AsyncSQL
from logging_config import logger
import random
import string

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class X3:
    def __init__(self):
        """Инициализация класса с настройками подключения"""
        self.target_url = PANEL_URL
        self.api_token = PANEL_API_TOKEN
        
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_token}'
        }
        
        self.params = {
            "vyWdoTBH": "VmsLiQrN"
        }

        self._session: aiohttp.ClientSession = None
        self.working_host = self.target_url
        self.is_authenticated = True

    async def _get_session(self) -> aiohttp.ClientSession:
        """Возвращает активную сессию aiohttp, создавая её при необходимости."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=False)
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                connector=connector
            )
        return self._session

    async def close(self):
        """Закрывает сессию aiohttp (вызывать при завершении работы)."""
        if self._session and not self._session.closed:
            await self._session.close()

    def generate_client_id(self, tg_id):
        """shortUuid: HMAC-SHA256(секрет, tg_id), 15 символов; white — тот же метод с tg_id*100."""
        if not SHORT_UUID_SECRET:
            raise ValueError(
                "SHORT_UUID_SECRET не задан в окружении (.env) — нужен для генерации shortUuid"
            )
        key = SHORT_UUID_SECRET.encode("utf-8")
        msg = str(int(tg_id)).encode("utf-8")
        digest = hmac.new(key, msg, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return token[:15]

    def list_from_host(self, host):
        """Заглушка для совместимости со старым кодом"""
        return {'obj': [{'settings': '{"clients": []}'}]}

    async def test_connect(self):
        try:
            session = await self._get_session()
            async with session.get(
                    f"{self.target_url}/api/auth/status",
                    params=self.params,
                    timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                logger.info(f"Тест подключения: {response.status}")
                return response.status == 200
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False

    async def list(self, start):
        try:
            params = self.params
            params['size'] = 1000
            params['start'] = start
            session = await self._get_session()
            async with session.get(
                    f'{self.target_url}/api/users',
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    logger.info(f'Получены юзеры с {start}')
                    return await resp.json()
                else:
                    logger.error(f"HTTP {resp.status}: {await resp.text()}")
                    return {'response': {'users': []}}
        except Exception as e:
            logger.error(f"Ошибка запроса: {e}")
            return {'response': {'users': []}}

    def _generate_password(self, length=12):
        """Генерирует случайный пароль"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    async def addClient(self, day, user_id_str, user_id):
        """Добавляет нового клиента"""
        try:
            client_id = self.generate_client_id(user_id)
            if 'white' in user_id_str:
                client_id = self.generate_client_id(user_id * 100)
            current_time = datetime.datetime.now(datetime.timezone.utc)
            expire_time = current_time + datetime.timedelta(days=day)
            vless_uuid = str(uuid.uuid1())

            if 'white' in user_id_str:
                squad_1 = ['86133527-d770-4e0d-a567-75f8309cf22f']
                squad = squad_1
                trafficLimitStrategy = "MONTH"
                trafficLimitBytes = 80530636800
                hwidDeviceLimit = 1
            else:
                squad_1 = ['e743960c-ea57-4fab-8d4a-5b77a15246c3']
                squad_2 = ['13244df4-5b78-4b86-a95e-5794484bf691']
                squad = random.choice([squad_1, squad_2])
                trafficLimitStrategy = "NO_RESET"
                trafficLimitBytes = 0
                hwidDeviceLimit = 3
            desc = 'Регион VPN'
            data = {
                "username": user_id_str,
                "status": "ACTIVE",
                "shortUuid": client_id,
                "trojanPassword": self._generate_password(),
                "vlessUuid": vless_uuid,
                "ssPassword": self._generate_password(),
                "trafficLimitStrategy": trafficLimitStrategy,
                "trafficLimitBytes": trafficLimitBytes,
                "expireAt": expire_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                "createdAt": current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                "hwidDeviceLimit": hwidDeviceLimit,
                "telegramId": int(user_id),
                "description": desc,
                "activeInternalSquads": squad
            }

            logger.info(f"Добавление клиента {user_id_str}, срок до: {expire_time}")

            session = await self._get_session()
            async with session.post(
                    f"{self.target_url}/api/users",
                    json=data,
                    params=self.params,
                    timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                logger.info(f"Код ответа: {response.status}")

                if response.status in [200, 201]:
                    sql = AsyncSQL()
                    try:
                        response_data = await response.json()
                    except (aiohttp.ClientConnectionError, aiohttp.ContentTypeError, ValueError) as e:
                        # Сервер мог не вернуть JSON, но статус успешный
                        logger.warning(f"Не удалось прочитать JSON при добавлении {user_id}: {e}. Считаем успехом.")
                        subscription_end_date = expire_time.replace(tzinfo=datetime.timezone.utc)
                        if 'white' in user_id_str:
                            await sql.update_white_subscription_end_date(user_id, subscription_end_date)
                            await sql.update_white_subscription(user_id, client_id)
                        else:
                            await sql.update_subscription_end_date(user_id, subscription_end_date)
                            await sql.update_subscribtion(user_id, client_id)
                        logger.info(f"✅ Клиент {user_id} успешно добавлен (без JSON)")
                        return True
                    else:
                        if response_data.get("success", True):
                            subscription_end_date = expire_time.replace(tzinfo=datetime.timezone.utc)
                            if 'white' in user_id_str:
                                await sql.update_white_subscription_end_date(user_id, subscription_end_date)
                                await sql.update_white_subscription(user_id, client_id)
                            else:
                                await sql.update_subscription_end_date(user_id, subscription_end_date)
                                await sql.update_subscribtion(user_id, client_id)
                            logger.info(f"✅ Клиент {user_id} успешно добавлен")
                            return True
                        else:
                            logger.warning(f"❌ API вернул ошибку: {response_data}")
                            return False
                else:
                    error_text = await response.text() if response.content else "No body"
                    logger.error(f"❌ Ошибка добавления клиента: HTTP {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении клиента {user_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def updateClient(self, day, user_id_str, user_id):
        """Обновляет клиента - добавляет дни к подписке"""
        try:
            # Получаем данные пользователя
            user_response = await self.get_user_by_username(user_id_str)

            if not user_response or 'response' not in user_response:
                logger.error(f"❌ Пользователь {user_id_str} не найден")
                return False

            user = user_response['response']
            
            # Проверяем обязательные поля
            if 'uuid' not in user or 'expireAt' not in user:
                logger.error(f"❌ У пользователя {user_id_str} отсутствуют обязательные поля")
                return False

            uuid_user = user['uuid']
            
            # Парсим текущую дату истечения
            expire_at_str = user['expireAt']
            current_expire_at = datetime.datetime.fromisoformat(expire_at_str.replace('Z', '+00:00'))
            now = datetime.datetime.now(datetime.timezone.utc)

            # Определяем новую дату истечения
            if current_expire_at < now:
                # Подписка истекла - начинаем с текущего момента
                new_expire_at = now + datetime.timedelta(days=day)
                status = 'ACTIVE'  # Активируем подписку
                logger.info(f"Подписка пользователя {user_id_str} истекла. Активируем и добавляем {day} дней")
            else:
                # Подписка активна - добавляем к существующей дате
                new_expire_at = current_expire_at + datetime.timedelta(days=day)
                status = user.get('status', 'ACTIVE')
                logger.info(f"Подписка пользователя {user_id_str} активна. Добавляем {day} дней")

            # Обрабатываем activeInternalSquads
            raw_squads = user.get('activeInternalSquads', [])
            squads = []
            for s in raw_squads:
                if isinstance(s, dict) and 'uuid' in s:
                    squads.append(s['uuid'])
                elif isinstance(s, str):
                    squads.append(s)

            # Формируем данные для обновления
            data = {
                "uuid": uuid_user,
                "status": status,
                "expireAt": new_expire_at.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                "trafficLimitBytes": user.get('trafficLimitBytes', 0),
                "trafficLimitStrategy": user.get('trafficLimitStrategy', "NO_RESET"),
                "activeInternalSquads": squads
            }

            logger.info(f"Обновление пользователя {user_id_str}:")
            logger.info(f"  Старая дата: {current_expire_at.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"  Новая дата: {new_expire_at.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"  Добавлено дней: {day}")

            session = await self._get_session()
            async with session.patch(
                    f"{self.target_url}/api/users",
                    json=data,
                    params=self.params,
                    timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                logger.info(f"Код ответа updateClient: {response.status}")
                if response.status == 200:
                    sql = AsyncSQL()
                    try:
                        response_data = await response.json()
                    except (aiohttp.ClientConnectionError, aiohttp.ContentTypeError, ValueError) as e:
                        logger.warning(f"Не удалось прочитать JSON при обновлении {user_id}: {e}. Считаем успехом.")
                        if 'white' in user_id_str:
                            await sql.update_white_subscription_end_date(user_id, new_expire_at)
                        else:
                            await sql.update_subscription_end_date(user_id, new_expire_at)
                        logger.info(f"✅ Клиент {user_id} успешно обновлён (без JSON), добавлено {day} дней")
                        return True
                    else:
                        if response_data.get("success", True):
                            if 'white' in user_id_str:
                                await sql.update_white_subscription_end_date(user_id, new_expire_at)
                            else:
                                await sql.update_subscription_end_date(user_id, new_expire_at)
                            logger.info(f"✅ Клиент {user_id} успешно обновлён, добавлено {day} дней")
                            return True
                        else:
                            logger.error(f"❌ API вернул success=false: {response_data}")
                            return False
                else:
                    error_text = await response.text() if response.content else "No body"
                    logger.error(f"❌ Ошибка обновления: HTTP {response.status}, {error_text}")
                    return False

        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении клиента {user_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def get_user_by_username(self, username):
        try:
            session = await self._get_session()
            async with session.get(
                    f"{self.target_url}/api/users/by-username/{username}",
                    params=self.params,
                    timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    try:
                        return await resp.json()
                    except:
                        logger.error(f"Не удалось прочитать JSON для пользователя {username}")
                        return None
                else:
                    logger.error(f"Ошибка получения пользователя {username}: {await resp.text()}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя {username}: {e}")
            return None

    async def get_user_by_telegram_id(self, telegram_id):
        try:
            session = await self._get_session()
            async with session.get(
                    f"{self.target_url}/api/users/by-telegram-id/{telegram_id}",
                    params=self.params,
                    timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    try:
                        return await resp.json()
                    except:
                        return None
                else:
                    return None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя по telegram_id {telegram_id}: {e}")
            return None

    async def sublink(self, user_id: str):
        try:
            users = await self.get_user_by_username(user_id)
            if users and 'response' in users and users['response']:
                user = users['response']
                true_sublink = user.get('subscriptionUrl', '')
                mirror_sublink = true_sublink.replace(TRUE_SUB_LINK, MIRROR_SUB_LINK)
                return mirror_sublink
        except Exception as e:
            logger.error(f"Ошибка при получении ссылки для {user_id}: {e}")
        return ""

    async def activ(self, user_id: str):
        result = {'activ': '🔎 - Не подключён', 'time': '-'}
        try:
            users = await self.get_user_by_username(user_id)
            if not users or 'response' not in users or not users['response']:
                logger.info(f"Пользователь {user_id} не найден в системе")
                return result

            raw = users['response']
            user = raw[0] if isinstance(raw, list) else raw
            current_time = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)

            expiry_time_str = user.get('expireAt')
            if not expiry_time_str:
                return result

            expiry_dt = datetime.datetime.fromisoformat(expiry_time_str.replace('Z', '+00:00'))
            expiry_time = int(expiry_dt.timestamp() * 1000)

            expiry_dt_msk = expiry_dt + datetime.timedelta(hours=3)
            readable_time = expiry_dt_msk.strftime('%d-%m-%Y %H:%M') + ' МСК'
            result['time'] = readable_time

            if user.get('status') == 'ACTIVE' and expiry_time > current_time:
                result['activ'] = '✅ - Активен'
            else:
                result['activ'] = '❌ - Не Активен'

            return result

        except Exception as e:
            logger.error(f"Ошибка в методе activ для {user_id}: {e}")
            result['activ'] = '❌ - Внутренняя ошибка'
            return result

    async def activ_list(self):
        lst_users = []
        try:
            users_all = []
            for i in range(100):
                data = await self.list(1000 * i + 1)
                if data['response']['users']:
                    users_all.extend(data['response']['users'])
                else:
                    break
            logger.info(f'Всего юзеров в панели - {len(users_all)}')
            for user in users_all:
                if user.get('userTraffic', {}).get('firstConnectedAt'):
                    telegram_id = user.get('telegramId')
                    if telegram_id is not None:
                        lst_users.append(int(telegram_id))
            logger.info(f'Всего юзеров подключенных - {len(lst_users)}')
        except Exception as e:
            logger.error(f"Ошибка при получении списка активности: {e}")
        return lst_users

    async def get_all_users(self):
        """
        Возвращает список всех пользователей из панели (объекты пользователей),
        у которых description == 'New user - without pay'.
        """
        users_all = []
        try:
            for i in range(100):  # максимум 50 страниц
                data = await self.list(1000 * i + 1)
                if data['response']['users']:
                    users_all.extend(data['response']['users'])
                else:
                    break
            logger.info(f'Всего юзеров в панели - {len(users_all)}')
        except Exception as e:
            logger.error(f"Ошибка при получении всех пользователей: {e}")
        return users_all

    async def update_user_squads(self, user_uuid: str, squads: list):
        """
        Обновляет поле activeInternalSquads у пользователя по его UUID.
        :param user_uuid: UUID пользователя в панели
        :param squads: список squad UUID (например, ['2fcfd928-6f45-4a8c-a36b-742fca8efea0'])
        :return: True при успехе, False при ошибке
        """
        try:
            data = {
                "uuid": user_uuid,
                "activeInternalSquads": squads
            }
            session = await self._get_session()
            async with session.patch(
                    f"{self.target_url}/api/users",
                    json=data,
                    params=self.params,
                    timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    try:
                        response_data = await response.json()
                    except (aiohttp.ClientConnectionError, aiohttp.ContentTypeError, ValueError) as e:
                        logger.warning(
                            f"Не удалось прочитать JSON при обновлении squads для UUID {user_uuid}: {e}. Считаем успехом.")
                        return True
                    else:
                        if response_data.get("success", True):
                            logger.info(f"✅ Squad обновлён для UUID {user_uuid}")
                            return True
                        else:
                            logger.error(f"❌ API вернул ошибку: {response_data}")
                            return False
                else:
                    error_text = await response.text() if response.content else "No body"
                    logger.error(f"❌ Ошибка HTTP {response.status}: {error_text}")
                    return False
        except Exception as e:
            logger.error(f"❌ Исключение при обновлении squads: {e}")
            return False

    async def get_all_panel(self):
        """
        Возвращает список всех пользователей из панели (объекты пользователей),
        у которых description == 'New user - without pay'.
        """
        lst_users = []
        try:
            users_all = []
            for i in range(100):  # максимум 100 страниц
                data = await self.list(1000 * i + 1)
                if data['response']['users']:
                    users_all.extend(data['response']['users'])
                else:
                    break
            logger.info(f'Всего юзеров в панели - {len(users_all)}')
            for user in users_all:
                lst_users.append(user)
        except Exception as e:
            logger.error(f"Ошибка при получении всех пользователей: {e}")
        return lst_users

    async def set_expiration_date(self, username: str, target_date: datetime, user_id: int):
        """
        Устанавливает точную дату окончания подписки для пользователя в панели.
        - Если пользователь не существует, создаёт его через addClient (с day=0).
        - Если target_date меньше текущего времени UTC, заменяет на текущее время + 1 минута.
        - Возвращает (успех, реальная_установленная_дата_UTC) или (False, None).
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        effective_date = target_date if target_date > now else now + datetime.timedelta(minutes=1)

        # Проверяем существование пользователя
        user_data = await self.get_user_by_username(username)
        if not user_data or 'response' not in user_data:
            # Пользователь отсутствует – создаём
            if not await self.addClient(0, username, user_id):
                logger.error(f"Не удалось создать пользователя {username} для установки даты")
                return False, None
            # После создания получаем данные заново
            user_data = await self.get_user_by_username(username)
            if not user_data or 'response' not in user_data:
                logger.error(f"Не удалось получить данные созданного пользователя {username}")
                return False, None

        user = user_data['response']
        uuid_user = user['uuid']

        # Формируем данные для обновления (сохраняем остальные поля)
        traffic_limit_bytes = user.get('trafficLimitBytes', 0)
        traffic_limit_strategy = user.get('trafficLimitStrategy', 'NO_RESET')
        status = 'ACTIVE'  # Активируем подписку
        raw_squads = user.get('activeInternalSquads', [])
        squads = [s['uuid'] if isinstance(s, dict) else s for s in raw_squads]

        data = {
            "uuid": uuid_user,
            "expireAt": effective_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            "status": status,
            "trafficLimitBytes": traffic_limit_bytes,
            "trafficLimitStrategy": traffic_limit_strategy,
            "activeInternalSquads": squads
        }

        session = await self._get_session()
        try:
            async with session.patch(
                    f"{self.target_url}/api/users",
                    json=data,
                    params=self.params,
                    timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    try:
                        resp_json = await response.json()
                        if resp_json.get('success', True):
                            logger.info(f"✅ Установлена дата {effective_date} для {username}")
                            return True, effective_date
                        else:
                            logger.error(f"Ошибка API при установке даты: {resp_json}")
                            return False, None
                    except:
                        # Нет JSON, но статус 200 – считаем успехом
                        logger.warning(f"Установка даты для {username} вернула 200 без JSON, считаем успешной")
                        return True, effective_date
                else:
                    error_text = await response.text() if response.content else "No body"
                    logger.error(f"Ошибка HTTP {response.status} при установке даты: {error_text}")
                    return False, None
        except Exception as e:
            logger.error(f"Исключение при установке даты для {username}: {e}")
            return False, None
