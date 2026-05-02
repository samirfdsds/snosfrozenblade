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

# --- ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ ---
app = Flask(__name__)
@app.route('/')
def index(): return "SnosByBladeFrozen: Система активна и готова к бою"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8584754791:AAGtZpb37q4DsF1KORfBQKbHwhoHcQLavlk'
CHANNEL_HANDLE = "@OslntResource"  # ИСПРАВЛЕНО: Теперь одна 'e'
CHANNEL_URL = "https://t.me/OslntResource"

# ИММУНИТЕТ ВЛАДЕЛЬЦА (@BladeFrozen)
MY_ID = 8331626488
MY_USERNAME = "BladeFrozen"

# Данные почты
EMAIL_SENDER = "samir2012samiro3uehsjdhd@gmail.com"
EMAIL_PASSWORD = "sfuo wmzl tvat cpjy".replace(" ", "")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="Markdown")
dp = Dispatcher(bot)

# --- ФУНКЦИЯ ПРОВЕРКИ ПОДПИСКИ ---
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_HANDLE, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"⚠️ Ошибка проверки подписки: {e}")
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
        InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_subscription")
    )
    return kb

def reason_menu(target_data):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💣 Терроризм / Насилие", callback_data=f"sn_terror_{target_data}"),
        InlineKeyboardButton("🔪 Селфхарм (Суицид)", callback_data=f"sn_harm_{target_data}"),
        InlineKeyboardButton("🔞 Детское насилие", callback_data=f"sn_child_{target_data}"),
        InlineKeyboardButton("💳 Мошенничество", callback_data=f"sn_scam_{target_data}")
    )
    return kb

# --- МОДУЛЬ ОТПРАВКИ ЖАЛОБЫ ---
def send_abuse_mail(username, uid, phone, reason):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = "abuse@telegram.org"
    
    subjects = {
        "terror": "Urgent: Terrorism and violent content report",
        "harm": "Urgent: Suicide or Self-harm threat report",
        "child": "Critical: Child Abuse material report",
        "scam": "Fraud Report: Financial Scam and Deception"
    }
    msg['Subject'] = subjects.get(reason, "Abuse Report")
    
    body = (f"Hello Telegram Support Team,\n\n"
            f"I am reporting a user for violation of your Terms of Service.\n\n"
            f"Target Details:\n"
            f"Username: @{username.replace('@','')}\n"
            f"User ID: {uid}\n"
            f"Phone: {phone}\n"
            f"Reason: {reason.upper()}\n\n"
            f"Please investigate and take appropriate actions.")
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"🔴 SMTP ERROR: {e}")
        return False

# --- ОБРАБОТЧИКИ ---

async def on_startup(dispatcher):
    await bot.delete_webhook(drop_pending_updates=True)
    print("🔥 SNOSBYBLADEFROZEN В СЕТИ И ГОТОВ К УДАРАМ!")

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        await message.answer(f"🛑 **Доступ ограничен!**\n\nДля использования SnosByBladeFrozen подпишитесь на наш канал: {CHANNEL_HANDLE}", reply_markup=sub_menu())
        return
    await message.answer(f"💀 **SnosByBladeFrozen v3.2 АКТИВИРОВАН**\nВыберите действие в меню ниже:", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == "check_subscription")
async def check_sub_callback(callback_query: types.CallbackQuery):
    if await is_subscribed(callback_query.from_user.id):
        await bot.answer_callback_query(callback_query.id, text="✅ Доступ открыт!")
        await bot.send_message(callback_query.from_user.id, "⚔️ Добро пожаловать в систему!", reply_markup=main_menu())
    else:
        await bot.answer_callback_query(callback_query.id, text="❌ Вы всё еще не подписаны!", show_alert=True)

@dp.message_handler(lambda message: message.text == "☢️ ЗАПУСТИТЬ СНОС")
async def start_snose(message: types.Message):
    if not await is_subscribed(message.from_user.id): return
    await message.answer("📥 **Введите данные цели:**\n`@username ID Номер` \n\nПример: `@durov 12345 79001112233`")

@dp.message_handler(lambda message: len(message.text.split()) == 3)
async def get_target_data(message: types.Message):
    if not await is_subscribed(message.from_user.id): return
    data = message.text.split()
    username = data[0].replace('@', '')
    uid = data[1]
    phone = data[2]
    
    if uid == str(MY_ID) or username.lower() == MY_USERNAME.lower():
        await message.answer("🛡 **ИММУНИТЕТ: Атака на владельца заблокирована.**")
        return
    
    target_str = f"{username}_{uid}_{phone}"
    await message.answer(f"🎯 **Цель:** @{username}\n🆔 **ID:** `{uid}`\n\n⚖️ Выберите причину для сноса:", reply_markup=reason_menu(target_str))

@dp.callback_query_handler(lambda c: c.data.startswith('sn_'))
async def process_abuse(c: types.CallbackQuery):
    p = c.data.split('_')
    # p[1]=reason, p[2]=user, p[3]=uid, p[4]=phone
    await bot.answer_callback_query(c.id, text="🚀 Ракета запущена...")
    
    if send_abuse_mail(p[2], p[3], p[4], p[1]):
        await bot.send_message(c.from_user.id, f"✅ **Жалоба на @{p[2]} отправлена в поддержку!**")
    else:
        await bot.send_message(c.from_user.id, "❌ **Ошибка SMTP.** Проверьте настройки Gmail.")

if __name__ == '__main__':
    Thread(target=run_web).start()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
