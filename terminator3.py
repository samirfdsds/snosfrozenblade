import logging
import asyncio
import smtplib
import os
from threading import Thread
from flask import Flask
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask(__name__)

@app.route('/')
def index():
    return "SnosByBladeFrozen is LIVE and READY!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- КОНФИГУРАЦИЯ БОТА ---
API_TOKEN = '8584754791:AAGyYVdKHBLgsaw5PmGGcO3wCEsqs5prcag'
CHANNEL_HANDLE = "@OslntResourcee"  # ИСПРАВЛЕНО: 'l' вместо 'i' и две 'e'
CHANNEL_URL = "https://t.me/OslntResourcee"

# ТВОИ ДАННЫЕ (ИММУНИТЕТ)
MY_ID = 8331626488
MY_USERNAME = "BladeFrozen"

# ПОЧТА GMAIL
EMAIL_SENDER = "samir2012samiro3uehsjdhd@gmail.com"
EMAIL_PASSWORD = "sfuo wmzl tvat cpjy".replace(" ", "")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="Markdown")
dp = Dispatcher(bot)

# --- ПРОВЕРКА ПОДПИСКИ ---
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_HANDLE, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

# --- КЛАВИАТУРЫ ---
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(KeyboardButton("☢️ ЗАПУСТИТЬ СНОС"), KeyboardButton("ℹ️ Инфо"))
    return kb

def sub_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL),
        InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_sub")
    )
    return kb

def reason_menu(data):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💣 Терроризм / Насилие", callback_data=f"sn_terror_{data}"),
        InlineKeyboardButton("🔪 Селфхарм (Суицид)", callback_data=f"sn_harm_{data}"),
        InlineKeyboardButton("🔞 Детское насилие", callback_data=f"sn_child_{data}"),
        InlineKeyboardButton("💳 Мошенничество", callback_data=f"sn_scam_{data}")
    )
    return kb

# --- МОДУЛЬ SMTP (СНОС) ---
def send_abuse(username, uid, phone, reason):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = "abuse@telegram.org"
    msg['Subject'] = f"Urgent Report: {reason.upper()} Content"
    
    body = (f"Target Username: @{username.replace('@','')}\n"
            f"Target ID: {uid}\n"
            f"Target Phone: {phone}\n"
            f"Reason: {reason.upper()}\n\n"
            f"Please investigate and terminate this account immediately.")
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP ERROR: {e}")
        return False

# --- ОБРАБОТЧИКИ ---

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    print(f"🔥 БОТ ВЫЗВАН ПОЛЬЗОВАТЕЛЕМ {message.from_user.id}")
    if not await is_subscribed(message.from_user.id):
        await message.answer(f"🛑 **Доступ заблокирован!**\n\nДля работы сносера подпишитесь: {CHANNEL_HANDLE}", reply_markup=sub_menu())
        return
    await message.answer(f"💀 **SnosByBladeFrozen v2.8 АКТИВИРОВАН**", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_sub_cb(c: types.CallbackQuery):
    if await is_subscribed(c.from_user.id):
        await bot.answer_callback_query(c.id, "✅ Доступ разрешен!")
        await bot.send_message(c.from_user.id, "⚔️ Добро пожаловать, эксперт!", reply_markup=main_menu())
    else:
        await bot.answer_callback_query(c.id, "❌ Вы всё еще не подписаны!", show_alert=True)

@dp.message_handler(lambda m: m.text == "☢️ ЗАПУСТИТЬ СНОС")
async def snose_start(m: types.Message):
    if not await is_subscribed(m.from_user.id): return
    await m.answer("📥 **Введите данные цели:**\n`@username ID Номер` \n\nПример: `@durov 12345 79001112233`")

@dp.message_handler(lambda m: len(m.text.split()) == 3)
async def target_data(m: types.Message):
    if not await is_subscribed(m.from_user.id): return
    data = m.text.split()
    user, uid, phone = data[0].replace('@',''), data[1], data[2]
    
    if uid == str(MY_ID) or user.lower() == MY_USERNAME.lower():
        await m.answer("🛡 **ИММУНИТЕТ: Атака на владельца заблокирована!**")
        return
        
    await m.answer(f"🎯 **Цель:** @{user}\n🆔 **ID:** `{uid}`\n\nВыберите причину:", reply_markup=reason_menu(f"{user}_{uid}_{phone}"))

@dp.callback_query_handler(lambda c: c.data.startswith('sn_'))
async def snose_exec(c: types.CallbackQuery):
    p = c.data.split('_')
    # p[1]=reason, p[2]=user, p[3]=uid, p[4]=phone
    await bot.answer_callback_query(c.id, "🚀 Ракета запущена!")
    res = send_abuse(p[2], p[3], p[4], p[1])
    
    if res:
        await bot.send_message(c.from_user.id, f"✅ **Жалоба на @{p[2]} успешно отправлена!**")
    else:
        await bot.send_message(c.from_user.id, "❌ Ошибка SMTP. Проверьте настройки Gmail.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    executor.start_polling(dp, skip_updates=True)
    
