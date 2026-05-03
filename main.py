
import logging
import asyncio
import os
import json
import random
import re
import aiohttp
import hashlib
import time
from datetime import datetime

# Библиотеки aiogram 3.x
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, 
    InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# База, Почта и Веб
from redis.asyncio import Redis
from aiosmtplib import send
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- КОНФИГУРАЦИЯ (ВСЕ ДАННЫЕ ВСТАВЛЕНЫ) ---
API_TOKEN = '8612963994:AAFRGV0DGXBJ0FVGefaaDqqyOC9-RFszUVY'
REDIS_URL = "rediss://default:gQAAAAAAAb3QAAIgcDIwODVmMTlkNmZiZmY0NjlkOWQ2MDFjMzFlYWYzZWM0Ng@nearby-ewe-114128.upstash.io:6379"
MY_ID = 8331626488

# Канал и Подписка
CHANNEL_URL = "https://t.me/+Tp4-Pe0Mkm5hN2Rk"
CHANNEL_ID = -1003700976280 

# Платежка LAVA
LAVA_PROJECT_ID = "9537185b-5d14-4675-bfa8-d54a3fa6eb3b"
LAVA_SECRET_KEY = "zx8xZeGW96AdxD5Xpa8rO5B7tytaaUSbhz6DhGCO607auEWzP1AlJxDW01Mk0MVo"

# Почта для сносов
EMAIL_SENDER = "samir2012samiro3uehsjdhd@gmail.com"
EMAIL_PASSWORD = "sfuowmzltvatcpjy"

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ИНИЦИАЛИЗАЦИЯ ---
bot = Bot(
    token=API_TOKEN, 
    default=DefaultBotProperties(parse_mode='Markdown')
)
dp = Dispatcher()
redis = Redis.from_url(REDIS_URL, decode_responses=True)

class AttackStates(StatesGroup):
    waiting_for_target = State()

# --- СИСТЕМА ПРОВЕРКИ ПОДПИСКИ ---
async def check_subscription(user_id: int):
    if user_id == MY_ID: return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        return False
    return False

def sub_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Вступить в штаб", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ Я ПОДПИСАЛСЯ", callback_data="check_sub")]
    ])

# --- ЛОГИКА БАЗЫ ДАННЫХ ---
async def get_user_data(user_id: int):
    raw = await redis.get(f"u:{user_id}")
    if raw:
        data = json.loads(raw)
    else:
        data = {"strikes": 0, "refs": 0, "sub_expires": 0, "last_refill": "", "is_admin": False}
    
    if data.get("sub_expires", 0) > time.time():
        today = datetime.now().strftime("%Y-%m-%d")
        if data.get("last_refill") != today:
            data["strikes"] += 5
            data["last_refill"] = today
            await redis.set(f"u:{user_id}", json.dumps(data))
            try: await bot.send_message(user_id, "🎁 **VIP БОНУС:** Начислено 5 ударов на сегодня!")
            except: pass
    return data

async def save_user_data(user_id: int, data: dict):
    await redis.set(f"u:{user_id}", json.dumps(data))

# --- АДМИН-КОМАНДЫ (ИСПРАВЛЕНЫ ОТСТУПЫ) ---
@dp.message(Command("monifoldgive"))
async def admin_give(message: Message, command: CommandObject):
    u_data = await get_user_data(message.from_user.id)
    if message.from_user.id != MY_ID and not u_data.get("is_admin"): return
    try:
        args = command.args.split()
        uid, count = int(args[0]), int(args[1])
        target = await get_user_data(uid)
        target["strikes"] += count
        await save_user_data(uid, target)
        await message.answer(f"✅ Выдано {count} ударов пользователю `{uid}`")
    except:
        await message.answer("Ошибка. Формат: `/monifoldgive ID колво`")

@dp.message(Command("monifold_setadmin"))
async def set_admin(message: Message, command: CommandObject):
    if message.from_user.id != MY_ID: return
    try:
        args = command.args.split()
        uid, status = int(args[0]), args[1]
        target = await get_user_data(uid)
        target["is_admin"] = True if status == "1" else False
        await save_user_data(uid, target)
        await message.answer(f"✅ Статус админа для `{uid}` обновлен на {status}")
    except:
        await message.answer("Ошибка. Формат: `/monifold_setadmin ID 1/0`")

# --- МОДУЛЬ ОПЛАТЫ LAVA ---
async def create_lava_invoice(amount, order_id):
    url = "https://api.lava.top/business/invoice/create"
    headers = {"Authorization": LAVA_SECRET_KEY, "Accept": "application/json"}
    payload = {"sum": amount, "orderId": order_id, "shopId": LAVA_PROJECT_ID, "caption": "God Engine Refill"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            return data.get("data", {}).get("url")

async def handle_lava_webhook(request):
    try:
        data = await request.json()
        if data.get('status') == 'success':
            parts = data.get('orderId').split('_')
            user_id, p_type, p_val = int(parts[0]), parts[1], int(parts[2])
            u_data = await get_user_data(user_id)
            if p_type == "pack": u_data["strikes"] += p_val
            elif p_type == "sub": u_data["sub_expires"] = max(time.time(), u_data["sub_expires"]) + (p_val * 86400)
            await save_user_data(user_id, u_data)
            await bot.send_message(user_id, "✅ **ОПЛАТА ПОЛУЧЕНА!** Баланс обновлен автоматически.")
            return aiohttp.web.Response(text="ok")
    except: pass
    return aiohttp.web.Response(status=400)

# --- ГЛАВНЫЕ ХЭНДЛЕРЫ ---

@dp.message(Command("start"))
async def cmd_start(m: Message):
    if not await check_subscription(m.from_user.id):
        return await m.answer("🛑 **ДОСТУП ОГРАНИЧЕН!**\nПодпишитесь на наш штаб для работы.", reply_markup=sub_kb())
    
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="☢️ НАНЕСТИ УДАР"), KeyboardButton(text="💎 МАГАЗИН")],
        [KeyboardButton(text="👤 ПРОФИЛЬ")]
    ], resize_keyboard=True)
    await m.answer("⚔️ **GOD ENGINE v30.0 ONLINE**\nСистема готова к работе.", reply_markup=kb)

@dp.callback_query(F.data == "check_sub")
async def check_sub_btn(c: CallbackQuery):
    if await check_subscription(c.from_user.id):
        await c.answer("✅ Доступ разрешен!")
        await c.message.delete()
        await cmd_start(c.message)
    else:
        await c.answer("❌ Вы не подписаны на канал!", show_alert=True)

@dp.message(F.text == "💎 МАГАЗИН")
async def store_cmd(m: Message):
    if not await check_subscription(m.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💣 1 Удар — 65₽", callback_data="buy_p_pack_1_65")],
        [InlineKeyboardButton(text="🚀 5 Ударов — 250₽", callback_data="buy_p_pack_5_250")],
        [InlineKeyboardButton(text="⚡ 10 Ударов — 450₽", callback_data="buy_p_pack_10_450")],
        [InlineKeyboardButton(text="⭐ VIP НЕДЕЛЯ (+5/день) — 490₽", callback_data="buy_p_sub_7_490")],
        [InlineKeyboardButton(text="🔥 VIP МЕСЯЦ (+5/день) — 1490₽", callback_data="buy_p_sub_30_1490")]
    ])
    await m.answer("💳 **МАГАЗИН ЗАРЯДОВ**\nВыберите пакет:", reply_markup=kb)

@dp.callback_query(F.data.startswith("buy_p_"))
async def process_buy(c: CallbackQuery):
    _, _, p_type, p_val, price = c.data.split("_")
    order_id = f"{c.from_user.id}_{p_type}_{p_val}_{random.randint(100, 999)}"
    pay_url = await create_lava_invoice(price, order_id)
    if pay_url:
        await c.message.answer(f"🛒 **Счет на {price}₽ создан!**", 
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 ОПЛАТИТЬ ЧЕРЕЗ LAVA", url=pay_url)]]))
    await c.answer()

@dp.message(F.text == "👤 ПРОФИЛЬ")
async def profile_cmd(m: Message):
    if not await check_subscription(m.from_user.id): return
    data = await get_user_data(m.from_user.id)
    sub = "❌" if data["sub_expires"] < time.time() else f"✅ до {datetime.fromtimestamp(data['sub_expires']).strftime('%d.%m')}"
    status = "Admin" if data.get("is_admin") or m.from_user.id == MY_ID else "User"
    await m.answer(f"👤 **ПРОФИЛЬ**\n━━━━━━━━━━━━\n🆔 ID: `{m.from_user.id}`\n🎖 Статус: `{status}`\n💣 Заряды: `{data['strikes']}`\n👑 VIP: {sub}")

# --- МОДУЛЬ АТАКИ ---
@dp.message(F.text == "☢️ НАНЕСТИ УДАР")
async def attack_init(m: Message, state: FSMContext):
    if not await check_subscription(m.from_user.id): return
    data = await get_user_data(m.from_user.id)
    if data['strikes'] <= 0 and m.from_user.id != MY_ID: return await m.answer("❌ Нет зарядов!")
    await m.answer("📡 Пришлите `@username` цели для сноса:")
    await state.set_state(AttackStates.waiting_for_target)

@dp.message(AttackStates.waiting_for_target)
async def target_capture(m: Message, state: FSMContext):
    user = m.text.replace("@", "").strip()
    if user.lower() == "bladefrozen": return await m.answer("🛡 **IMMUNITY**")
    
    target_id = "Unknown"
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://t.me/{user}") as resp:
            text = await resp.text()
            match = re.search(r'tg://resolve\?domain=.*?id=(\d+)', text)
            if match: target_id = match.group(1)

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💥 ЗАПУСТИТЬ УДАР", callback_data=f"fire_{user}_{target_id}")]])
    await m.answer(f"🎯 **ЦЕЛЬ:** @{user}\n🆔 **ID:** `{target_id}`", reply_markup=kb)
    await state.clear()

@dp.callback_query(F.data.startswith("fire_"))
async def fire_strike(c: CallbackQuery):
    _, user, uid = c.data.split("_")
    data = await get_user_data(c.from_user.id)
    if data['strikes'] <= 0 and c.from_user.id != MY_ID: return await c.answer("Ошибка баланса")

    await c.message.edit_text("🚀 **ВЫПОЛНЯЕТСЯ УДАР...**")
    
    msg = MIMEMultipart(); msg['From'] = EMAIL_SENDER; msg['To'] = "abuse@telegram.org"
    msg['Subject'] = f"REPORT-UID-{uid}-{random.randint(100,999)}"
    msg.attach(MIMEText(f"Reporting illegal activity on Telegram by user @{user} (ID: {uid}).", 'plain'))
    
    try:
        await send(msg, hostname="smtp.gmail.com", port=465, username=EMAIL_SENDER, password=EMAIL_PASSWORD, use_tls=True)
        if c.from_user.id != MY_ID:
            data["strikes"] -= 1
            await save_user_data(c.from_user.id, data)
        await c.message.edit_text(f"✅ **УДАР ЗАВЕРШЕН!**\nЖалоба на @{user} доставлена в поддержку.")
        try: await bot.send_message(CHANNEL_ID, f"🔥 **STRIKE LOG**\nTarget: @{user}\nID: `{uid}`\nStatus: SENT ✅")
        except: pass
    except:
        await c.message.edit_text("❌ Ошибка SMTP сервера.")

# --- WEB SERVER (RENDER) ---
async def handle_web_root(request):
    return aiohttp.web.Response(text="GOD ENGINE IS ONLINE")

async def run_web():
    webapp = aiohttp.web.Application()
    webapp.router.add_post('/lava_webhook', handle_lava_webhook)
    webapp.router.add_get('/', handle_web_root)
    runner = aiohttp.web.AppRunner(webapp)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await aiohttp.web.TCPSite(runner, '0.0.0.0', port).start()

async def main():
    asyncio.create_task(run_web())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
