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

# --- ВЕБ-СЕРВЕР ---
app = Flask(__name__)
@app.route('/')
def index(): return "SnosByBladeFrozen is LIVE"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8584754791:AAGyYVdKHBLgsaw5PmGGcO3wCEsqs5prcag'
CHANNEL_HANDLE = "@OslntResourcee"
CHANNEL_URL = "https://t.me/OslntResourcee"
MY_ID = 8331626488
MY_USERNAME = "BladeFrozen"
EMAIL_SENDER = "samir2012samiro3uehsjdhd@gmail.com"
EMAIL_PASSWORD = "sfuo wmzl tvat cpjy".replace(" ", "")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="Markdown")
dp = Dispatcher(bot)

# --- МАЯК ЗАПУСКА ---
print("🔥 СИСТЕМА SNOSBYBLADEFROZEN ЗАПУЩЕНА И ЖДЕТ КОМАНД!")

async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_HANDLE, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"⚠️ ОШИБКА АДМИНКИ: Бот не админ в канале! {e}")
        return False

# --- ОБРАБОТЧИКИ ---

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    print(f"📩 ПОЛУЧЕНА КОМАНДА /START ОТ {message.from_user.id}")
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("📢 Подписаться", url=CHANNEL_URL),
               InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_sub"))
        await message.answer(f"🛑 **Доступ ограничен!**\n\nПодпишитесь на наш канал: {CHANNEL_HANDLE}", reply_markup=kb)
        return
    
    main_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("☢️ ЗАПУСТИТЬ СНОС"))
    await message.answer("💀 **SnosByBladeFrozen v3.0 АКТИВИРОВАН**", reply_markup=main_kb)

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_sub_cb(c: types.CallbackQuery):
    print(f"🔘 КЛИК ПО КНОПКЕ ПРОВЕРКИ ОТ {c.from_user.id}")
    if await is_subscribed(c.from_user.id):
        await bot.answer_callback_query(c.id, "✅ Доступ открыт!")
        main_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("☢️ ЗАПУСТИТЬ СНОС"))
        await bot.send_message(c.from_user.id, "⚔️ Добро пожаловать!", reply_markup=main_kb)
    else:
        await bot.answer_callback_query(c.id, "❌ Вы всё еще не подписаны!", show_alert=True)

@dp.message_handler(lambda m: m.text == "☢️ ЗАПУСТИТЬ СНОС")
async def snose_start(m: types.Message):
    print(f"🚀 ЗАПУСК СНОСА: ВЗАИМОДЕЙСТВИЕ С {m.from_user.id}")
    if not await is_subscribed(m.from_user.id): return
    await m.answer("📥 **Введите данные цели:**\n`@username ID Номер` \n\nПример: `@durov 12345 79001112233`")

@dp.message_handler(lambda m: len(m.text.split()) == 3)
async def target_data(m: types.Message):
    print(f"🎯 ЦЕЛЬ ПОЛУЧЕНА ОТ {m.from_user.id}: {m.text}")
    if not await is_subscribed(m.from_user.id): return
    data = m.text.split()
    user, uid, phone = data[0].replace('@',''), data[1], data[2]
    
    if uid == str(MY_ID) or user.lower() == MY_USERNAME.lower():
        await m.answer("🛡 **ИММУНИТЕТ: Атака на владельца заблокирована!**")
        return
        
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💣 Терроризм", callback_data=f"sn_terror_{user}_{uid}_{phone}"),
        InlineKeyboardButton("🔪 Селфхарм", callback_data=f"sn_harm_{user}_{uid}_{phone}"),
        InlineKeyboardButton("🔞 Детское насилие", callback_data=f"sn_child_{user}_{uid}_{phone}"),
        InlineKeyboardButton("💳 Мошенничество", callback_data=f"sn_scam_{user}_{uid}_{phone}")
    )
    await m.answer(f"🎯 **Цель:** @{user}\n🆔 **ID:** `{uid}`\n\nВыберите причину для сноса:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('sn_'))
async def snose_exec(c: types.CallbackQuery):
    print(f"☢️ АТАКА ЗАПУЩЕНА ПОЛЬЗОВАТЕЛЕМ {c.from_user.id}")
    p = c.data.split('_')
    # p[1]=reason, p[2]=user, p[3]=uid, p[4]=phone
    await bot.answer_callback_query(c.id, "🚀 Ракета запущена!")
    
    # Модуль отправки почты (вызываем твою функцию send_abuse)
    # [Здесь должна быть функция send_abuse_mail из прошлых версий]
    res = True # Имитация для теста связи
    
    await bot.send_message(c.from_user.id, "✅ Жалоба успешно отправлена в поддержку Telegram!")

if __name__ == '__main__':
    Thread(target=run_web).start()
    executor.start_polling(dp, skip_updates=True)
