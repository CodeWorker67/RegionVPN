import logging

from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, Date, Float, event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

DB_URL = "sqlite+aiosqlite:///config_bd/regionvpn.db"
engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase, AsyncAttrs):
    pass


class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    ref = Column(String(100), nullable=True)
    is_delete = Column(Boolean, default=False)
    in_panel = Column(Boolean, default=False)
    is_connect = Column(Boolean, default=False)
    create_user = Column(DateTime, default=datetime.now)
    in_chanel = Column(Boolean, default=False)
    reserve_field = Column(Boolean, default=False)
    subscription_end_date = Column(DateTime, nullable=True)
    white_subscription_end_date = Column(DateTime, nullable=True)
    last_notification_date = Column(Date, nullable=True)
    last_broadcast_status = Column(String(100), nullable=True)
    last_broadcast_date = Column(DateTime, nullable=True)
    stamp = Column(String(100), nullable=False)
    ttclid = Column(String(100), nullable=True)
    subscribtion = Column(String(255), nullable=True)
    white_subscription = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    activation_pass = Column(String(255), nullable=True)
    field_str_1 = Column(String(255), nullable=True)
    field_str_2 = Column(String(255), nullable=True)
    field_str_3 = Column(String(255), nullable=True)
    field_bool_1 = Column(Boolean, default=False)
    field_bool_2 = Column(Boolean, default=False)
    field_bool_3 = Column(Boolean, default=False)


class Gifts(Base):
    __tablename__ = 'gifts'

    gift_id = Column(String(36), primary_key=True)
    giver_id = Column(BigInteger, nullable=False)
    duration = Column(Integer, nullable=False)
    recepient_id = Column(BigInteger, nullable=True)
    white_flag = Column(Boolean, default=False)
    flag = Column(Boolean, default=False)


class Payments(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    amount = Column(Integer, nullable=False)
    time_created = Column(DateTime, default=datetime.now)
    is_gift = Column(Boolean, default=False)
    status = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)
    payload = Column(String, nullable=True)


class PaymentsCards(Base):
    __tablename__ = 'payments_cards'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    amount = Column(Integer, nullable=False)
    time_created = Column(DateTime, default=datetime.now)
    is_gift = Column(Boolean, default=False)
    status = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)
    payload = Column(String, nullable=True)


class PaymentsPlategaCrypto(Base):
    __tablename__ = 'payments_platega_crypto'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    amount = Column(Integer, nullable=False)
    time_created = Column(DateTime, default=datetime.now)
    is_gift = Column(Boolean, default=False)
    status = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)
    payload = Column(String, nullable=True)


class PaymentsStars(Base):
    __tablename__ = 'payments_stars'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    amount = Column(Integer, nullable=False)
    time_created = Column(DateTime, default=datetime.now)
    is_gift = Column(Boolean, default=False)
    status = Column(String, default='confirmed')
    payload = Column(String, nullable=True)


class PaymentsCryptobot(Base):
    __tablename__ = 'payments_cryptobot'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    time_created = Column(DateTime, default=datetime.now)
    is_gift = Column(Boolean, default=False)
    status = Column(String, default='pending')
    invoice_id = Column(String, nullable=True)
    payload = Column(String, nullable=True)


class WhiteCounter(Base):
    __tablename__ = 'white_counter'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    time_created = Column(DateTime, default=datetime.now)


class Online(Base):
    __tablename__ = 'online'

    online_id = Column(Integer, primary_key=True, autoincrement=True)
    online_date = Column(DateTime, default=datetime.now, nullable=False)
    users_panel = Column(Integer, nullable=False)
    users_active = Column(Integer, nullable=False)
    users_pay = Column(Integer, nullable=False)
    users_trial = Column(Integer, nullable=False)


# Функция для создания таблиц (запустить один раз)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)