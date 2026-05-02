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

# --- ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "SnosByBladeFrozen: Система активна"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8584754791:AAGyYVdKHBLgsaw5PmGGcO3wCEsqs5prcag'
CHANNEL_HANDLE = "@OsintResourcee"  # ИСПРАВЛЕНО: Две 'e' на конце
CHANNEL_URL = "https://t.me/OsintResourcee"

# ИММУНИТЕТ ВЛАДЕЛЬЦА (@BladeFrozen)
MY_ID = 8331626488
MY_USERNAME = "BladeFrozen"

# Данные почты для сноса
EMAIL_SENDER = "samir2012samiro3uehsjdhd@gmail.com"
EMAIL_PASSWORD = "sfuo wmzl tvat cpjy".replace(" ", "")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="Markdown")
dp = Dispatcher(bot)

# --- ПРОВЕРКА ПОДПИСКИ ---
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_HANDLE, user_id=user_id)
        return member.status != 'left'
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
        InlineKeyboardButton("📢 Подписаться на @OsintResourcee", url=CHANNEL_URL),
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

# --- МОДУЛЬ ОТПРАВКИ ЖАЛОБЫ (SMTP SSL 465) ---
def send_abuse_mail(username, uid, phone, reason):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = "abuse@telegram.org"
    
    subjects = {
        "terror": "Urgent: Terrorism promotion report",
        "harm": "Urgent: Suicide/Self-harm threat",
        "child": "Critical: Child Abuse report",
        "scam": "Fraud Report: Financial Scam"
    }
    msg['Subject'] = subjects.get(reason, "Abuse Report")
    
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
    if not await is_subscribed(message.from_user.id):
        await message.answer(f"🛑 **Доступ ограничен!**\n\nДля использования бота, подпишитесь на наш канал: {CHANNEL_HANDLE}", reply_markup=sub_menu())
        return
    await message.answer(f"💀 **SnosByBladeFrozen v2.7**\n\nСистема в сети. Готов к работе.", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == "check_subscription")
async def check_sub_cb(callback_query: types.CallbackQuery):
    if await is_subscribed(callback_query.from_user.id):
        await bot.answer_callback_query(callback_query.id, text="✅ Доступ открыт!")
        await bot.send_message(callback_query.from_user.id, "⚔️ Приветствуем! Теперь вам доступны все функции.", reply_markup=main_menu())
    else:
        await bot.answer_callback_query(callback_query.id, text="❌ Вы всё еще не подписаны!", show_alert=True)

@dp.message_handler(lambda message: message.text == "☢️ ЗАПУСТИТЬ СНОС")
async def start_snose(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        await message.answer("🛑 Сначала подпишитесь на канал!", reply_markup=sub_menu())
        return
    await message.answer("📥 **Введите данные цели:**\n`@username ID Номер` \n\nПример: `@target 12345 79001112233`")

@dp.message_handler(lambda message: len(message.text.split()) == 3)
async def get_target_data(message: types.Message):
    if not await is_subscribed(message.from_user.id): return
    
    data = message.text.split()
    username = data[0].replace('@', '')
    uid = data[1]
    phone = data[2]
    
    # ИММУНИТЕТ
    if uid == str(MY_ID) or username.lower() == MY_USERNAME.lower():
        await message.answer("🛡 **Иммунитет BladeFrozen активен.**\nАтака заблокирована системой.")
        return
    
    target_str = f"{username}_{uid}_{phone}"
    await message.answer(f"🎯 **Цель:** @{username}\n🆔 **ID:** `{uid}`\n\nВыберите причину:", reply_markup=reason_menu(target_str))

@dp.callback_query_handler(lambda c: c.data.startswith('sn_'))
async def process_abuse(callback_query: types.CallbackQuery):
    params = callback_query.data.split('_')
    reason, username, uid, phone = params[1], params[2], params[3], params[4]
    
    if uid == str(MY_ID) or username.lower() == MY_USERNAME.lower():
        await bot.answer_callback_query(callback_query.id, text="🛡 Иммунитет!")
        return

    await bot.answer_callback_query(callback_query.id, text="🚀 Жалоба отправляется...")
    
    if send_abuse_mail(username, uid, phone, reason):
        await bot.send_message(callback_query.from_user.id, f"✅ **Успех!**\nЖалоба на @{username} ушла в поддержку.")
    else:
        await bot.send_message(callback_query.from_user.id, "❌ Ошибка SMTP. Проверьте 2FA.")

@dp.message_handler(lambda message: message.text == "ℹ️ Инфо")
async def info_cmd(message: types.Message):
    await message.answer(f"🛠 **SnosByBladeFrozen**\n\nКанал: {CHANNEL_HANDLE}\nВладелец: @{MY_USERNAME}")

if __name__ == '__main__':
    keep_alive() # Запуск сервера для Render
    executor.start_polling(dp, skip_updates=True)
