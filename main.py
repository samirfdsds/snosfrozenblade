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

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, 
    InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton,
    ChatJoinRequest
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from redis.asyncio import Redis
from aiosmtplib import send
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ========================= КОНФИГУРАЦИЯ =========================
API_TOKEN = '8612963994:AAFRGV0DGXBJ0FVGefaaDqqyOC9-RFszUVY'
REDIS_URL = "rediss://default:gQAAAAAAAb3QAAIgcDIwODVmMTlkNmZiZmY0NjlkOWQ2MDFjMzFlYWYzZWM0Ng@nearby-ewe-114128.upstash.io:6379"

OWNER_ID = 529380916                    # ← Новый главный владелец
CHANNEL_URL = "https://t.me/+FfrOy9J7PnJkOTdk"
CHANNEL_ID = -1003700976280 

LAVA_PROJECT_ID = "9537185b-5d14-4675-bfa8-d54a3fa6eb3b"
LAVA_SECRET_KEY = "zx8xZeGW96AdxD5Xpa8rO5B7tytaaUSbhz6DhGCO607auEWzP1AlJxDW01Mk0MVo"

EMAIL_SENDER = "samir2012samiro3uehsjdhd@gmail.com"
EMAIL_PASSWORD = "sfuowmzltvatcpjy"

# ================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(
    token=API_TOKEN, 
    default=DefaultBotProperties(parse_mode='Markdown')
)
dp = Dispatcher()
redis = Redis.from_url(REDIS_URL, decode_responses=True)

class AttackStates(StatesGroup):
    waiting_for_target = State()

# ====================== ПРОВЕРКИ ПРАВ ======================
async def is_owner(user_id: int):
    return user_id == OWNER_ID

async def is_invincible(user_id: int):
    if await is_owner(user_id): return True
    data = await get_user_data(user_id)
    return data.get("is_invincible", False)

async def is_admin(user_id: int):
    if await is_owner(user_id) or await is_invincible(user_id): return True
    data = await get_user_data(user_id)
    return data.get("is_admin", False)

# ====================== БАЗА ДАННЫХ ======================
async def get_user_data(user_id: int):
    raw = await redis.get(f"u:{user_id}")
    if raw:
        data = json.loads(raw)
    else:
        data = {
            "strikes": 0,
            "refs": 0,
            "sub_expires": 0,
            "last_refill": "",
            "is_admin": False,
            "is_invincible": False
        }
    return data

async def save_user_data(user_id: int, data: dict):
    await redis.set(f"u:{user_id}", json.dumps(data))

# ====================== АВТО-ПРИЕМ В КАНАЛ ======================
@dp.chat_join_request()
async def auto_approve(chat_join: ChatJoinRequest):
    try:
        await chat_join.approve()
        await bot.send_message(
            chat_join.from_user.id,
            "✅ **Заявка одобрена!**\nДобро пожаловать в Cipizza.\nНажмите /start"
        )
    except Exception as e:
        logger.error(f"Auto-approve error: {e}")

# ====================== ПРОВЕРКА ПОДПИСКИ ======================
async def check_subscription(user_id: int):
    if user_id == OWNER_ID: return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        return False
    return False

def sub_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Вступить в канал", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ Я ПОДПИСАЛСЯ", callback_data="check_sub")]
    ])

# ====================== АДМИН КОМАНДЫ ======================
@dp.message(Command("setinvincible"))
async def set_invincible(message: Message, command: CommandObject):
    if not await is_owner(message.from_user.id):
        return await message.answer("⛔ Только владелец может выдавать неприкосновенность.")
    try:
        uid, status = command.args.split()
        uid = int(uid)
        val = status == "1"
        data = await get_user_data(uid)
        data["is_invincible"] = val
        await save_user_data(uid, data)
        await message.answer(f"✅ Пользователь `{uid}` теперь {'**НЕПРИКОСНОВЕННЫЙ**' if val else 'обычный пользователь'}")
    except:
        await message.answer("Формат: `/setinvincible ID 1` или `/setinvincible ID 0`")

@dp.message(Command("monifoldgive"))
async def admin_give(message: Message, command: CommandObject):
    if not await is_admin(message.from_user.id): return
    try:
        uid, count = command.args.split()
        target = await get_user_data(int(uid))
        target["strikes"] += int(count)
        await save_user_data(int(uid), target)
        await message.answer(f"✅ Выдано {count} ударов пользователю `{uid}`")
    except:
        await message.answer("Формат: `/monifoldgive ID количество`")

@dp.message(Command("monifold_setadmin"))
async def set_admin(message: Message, command: CommandObject):
    if not await is_owner(message.from_user.id): return
    try:
        uid, status = command.args.split()
        uid = int(uid)
        val = status == "1"
        data = await get_user_data(uid)
        data["is_admin"] = val
        await save_user_data(uid, data)
        await message.answer(f"✅ Обычный админ для `{uid}` {'включён' if val else 'выключен'}")
    except:
        await message.answer("Формат: `/monifold_setadmin ID 1/0`")

# ====================== LAVA ======================
async def create_lava_invoice(amount, order_id):
    url = "https://api.lava.top/business/invoice/create"
    headers = {"Authorization": LAVA_SECRET_KEY, "Accept": "application/json"}
    payload = {"sum": amount, "orderId": order_id, "shopId": LAVA_PROJECT_ID, "caption": "Cipizza Refill"}
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
            elif p_type == "sub": u_data["sub_expires"] = max(time.time(), u_data.get("sub_expires", 0)) + (p_val * 86400)
            await save_user_data(user_id, u_data)
            await bot.send_message(user_id, "✅ **ОПЛАТА ПРОШЛА УСПЕШНО!**")
            return aiohttp.web.Response(text="ok")
    except: pass
    return aiohttp.web.Response(status=400)

# ====================== ОСНОВНЫЕ КОМАНДЫ ======================
@dp.message(Command("start"))
async def cmd_start(m: Message):
    if not await check_subscription(m.from_user.id):
        return await m.answer("🛑 **ДОСТУП ОГРАНИЧЕН!**\nПодпишитесь на канал для доступа.", reply_markup=sub_kb())
    
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="☢️ НАНЕСТИ УДАР"), KeyboardButton(text="💎 МАГАЗИН")],
        [KeyboardButton(text="👤 ПРОФИЛЬ")]
    ], resize_keyboard=True)
    await m.answer("⚔️ **CIPIZZA v34.0**\nСистема активна.", reply_markup=kb)

@dp.callback_query(F.data == "check_sub")
async def check_sub_btn(c: CallbackQuery):
    if await check_subscription(c.from_user.id):
        await c.answer("✅ Доступ открыт!", show_alert=True)
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
        [InlineKeyboardButton(text="⭐ VIP НЕДЕЛЯ — 490₽", callback_data="buy_p_sub_7_490")],
        [InlineKeyboardButton(text="🔥 VIP МЕСЯЦ — 1490₽", callback_data="buy_p_sub_30_1490")]
    ])
    await m.answer("💎 **CIPIZZA STORE**", reply_markup=kb)

@dp.callback_query(F.data.startswith("buy_p_"))
async def process_buy(c: CallbackQuery):
    _, _, p_type, p_val, price = c.data.split("_")
    order_id = f"{c.from_user.id}_{p_type}_{p_val}_{random.randint(100, 999)}"
    pay_url = await create_lava_invoice(price, order_id)
    if pay_url:
        await c.message.answer(f"🛒 Счёт на {price}₽ создан", 
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 ОПЛАТИТЬ", url=pay_url)]]))
    await c.answer()

@dp.message(F.text == "👤 ПРОФИЛЬ")
async def profile_cmd(m: Message):
    if not await check_subscription(m.from_user.id): return
    data = await get_user_data(m.from_user.id)
    if await is_owner(m.from_user.id):
        status = "👑 ВЛАДЕЛЕЦ"
    elif await is_invincible(m.from_user.id):
        status = "🛡️ НЕПРИКОСНОВЕННЫЙ"
    elif data.get("is_admin"):
        status = "🛠 Администратор"
    else:
        status = "Пользователь"
    
    sub = "❌" if data["sub_expires"] < time.time() else f"✅ до {datetime.fromtimestamp(data['sub_expires']).strftime('%d.%m')}"
    await m.answer(f"👤 **ПРОФИЛЬ CIPIZZA**\n━━━━━━━━━━━━\n🆔 ID: `{m.from_user.id}`\n🎖 Статус: {status}\n💣 Заряды: `{data['strikes']}`\n👑 VIP: {sub}")

@dp.message(F.text == "☢️ НАНЕСТИ УДАР")
async def attack_init(m: Message, state: FSMContext):
    if not await check_subscription(m.from_user.id): return
    data = await get_user_data(m.from_user.id)
    if data['strikes'] <= 0 and not await is_owner(m.from_user.id):
        return await m.answer("❌ У вас закончились заряды!")
    await m.answer("📡 Отправьте `@username` цели:")
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

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💥 ЗАПУСТИТЬ", callback_data=f"fire_{user}_{target_id}")]])
    await m.answer(f"🎯 **ЦЕЛЬ:** @{user}\n🆔 **ID:** `{target_id}`", reply_markup=kb)
    await state.clear()

@dp.callback_query(F.data.startswith("fire_"))
async def fire_strike(c: CallbackQuery):
    _, user, uid = c.data.split("_")
    data = await get_user_data(c.from_user.id)
    if data['strikes'] <= 0 and not await is_owner(c.from_user.id):
        return await c.answer("❌ Нет зарядов!")

    await c.message.edit_text("🚀 **УДАР ВЫПОЛНЯЕТСЯ...**")
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = "abuse@telegram.org"
    msg['Subject'] = f"CRITICAL REPORT {random.randint(10000,99999)}"
    msg.attach(MIMEText(f"Reporting illegal content from @{user} (ID: {uid}).", 'plain'))
    
    try:
        await send(msg, hostname="smtp.gmail.com", port=465, username=EMAIL_SENDER, password=EMAIL_PASSWORD, use_tls=True)
        if not await is_owner(c.from_user.id):
            data["strikes"] -= 1
            await save_user_data(c.from_user.id, data)
        await c.message.edit_text(f"✅ **УДАР УСПЕШНО ОТПРАВЛЕН**\nЖалоба на @{user} доставлена.")
    except:
        await c.message.edit_text("❌ Ошибка отправки жалобы.")

# ====================== WEB SERVER ======================
async def handle_web_root(request):
    return aiohttp.web.Response(text="CIPIZZA IS ONLINE")

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
