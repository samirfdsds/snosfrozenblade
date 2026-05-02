import logging
import asyncio
import smtplib
import os
import re
import random
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
def index(): return "SnosByBladeFrozen v1.0: COMMANDER ONLINE"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8780556440:AAGWHXukzX-DkZCixb4RYag2ef_a7Z3DXw8'
CHANNEL_HANDLE = "@OslntResource" 
LOG_CHANNEL = "@OslntResource" # Сюда будут лететь отчеты об атаках
MY_ID = 8331626488
MY_USERNAME = "BladeFrozen"

# ГЛАВНОЕ ОРУДИЕ
PRIMARY_MAIL = ("samir2012samiro3uehsjdhd@gmail.com", "sfuowmzltvatcpjy")
GLOBAL_FLEET = [PRIMARY_MAIL]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="Markdown")
dp = Dispatcher(bot)

# --- МОДУЛИ ИНТЕЛЛЕКТА ---

async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_HANDLE, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

async def auto_fetch_id(username):
    # Тот самый парсер t.me, который мы делали в начале
    import aiohttp
    url = f'https://t.me/{username.replace("@","")}'
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    uid_match = re.search(r'<a href="/im\?p=(.*?)">', html)
                    if uid_match:
                        return uid_match.group(1).replace('u', '')
        except: pass
    return None

def send_strike(target_user, target_id, target_phone, protocol, mail_data):
    email, password = mail_data
    msg = MIMEMultipart()
    msg['From'] = email
    msg['To'] = "abuse@telegram.org"
    
    # ЮРИДИЧЕСКИЕ ПРОТОКОЛЫ
    protocols = {
        "legal": f"Official Legal Request: Violation of Digital Rights by @{target_user}",
        "emergency": f"EMERGENCY: Immediate Life Threat Report (UID: {target_id})",
        "security": f"Security Breach Alert: Illegal Content Distribution"
    }
    
    msg['Subject'] = protocols.get(protocol, "Abuse Report")
    body = f"STRIKE PROTOCOL: {protocol.upper()}\nTarget: @{target_user}\nID: {target_id}\nPhone: {target_phone}\n\nEvidence attached. Proceed with termination."
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
        server.login(email, password)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

# --- ИНТЕРФЕЙС ---
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🎯 АВТО-ЗАХВАТ"), KeyboardButton("☢️ РУЧНОЙ СНОС"))
    kb.add(KeyboardButton("➕ ДОБАВИТЬ ОРУДИЕ"), KeyboardButton("🐝 СТАТУС РОЯ"))
    return kb

# --- ОБРАБОТЧИКИ ---

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("📢 Подписаться", url="https://t.me/OslntResource"),
                                        InlineKeyboardButton("🔄 Проверить", callback_data="check_sub"))
        await message.answer("🛑 **ДОСТУП ЗАБЛОКИРОВАН**\nВступите в штаб: @OslntResource", reply_markup=kb)
        return
    await message.answer(f"💀 **SnosByBladeFrozen v8.0 «STRIKE COMMANDER»**\n\nСистема готова к деплою.", reply_markup=main_menu())

@dp.message_handler(lambda m: m.text == "🎯 АВТО-ЗАХВАТ")
async def auto_target(m: types.Message):
    await m.answer("📡 **Введите @username цели.**\nБот сам найдет ID и подготовит атаку.")

@dp.message_handler(lambda m: m.text.startswith('@') and " " not in m.text)
async def process_auto_capture(m: types.Message):
    if not await is_subscribed(m.from_user.id): return
    username = m.text.replace('@', '')
    
    wait = await m.answer(f"🔎 **Сканирую цель @{username}...**")
    uid = await auto_fetch_id(username)
    
    if uid:
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("⚡️ ЗАПУСТИТЬ ЗАЛП (Все почты)", callback_data=f"fire_all_{username}_{uid}_NONE"),
               InlineKeyboardButton("🛡 ОТМЕНА", callback_data="cancel"))
        await wait.edit_text(f"🎯 **ЦЕЛЬ ЗАХВАЧЕНА!**\n\n👤 Юзер: @{username}\n🆔 ID: `{uid}`\n\nГотовы нанести удар?", reply_markup=kb)
    else:
        await wait.edit_text("❌ **Ошибка захвата.** Цель скрыла данные или не существует.")

@dp.message_handler(lambda m: m.text == "☢️ РУЧНОЙ СНОС")
async def manual_start(m: types.Message):
    await m.answer("📥 Введите данные: `@username ID Номер` \n(Если номера нет, пиши 'None')")

@dp.callback_query_handler(lambda c: c.data.startswith('fire_'))
async def fire_swarm(c: types.CallbackQuery):
    p = c.data.split('_')
    # mode[1], user[2], uid[3], phone[4]
    
    status = await bot.send_message(c.from_user.id, f"🚀 **РОЙ ВЫЛЕТЕЛ!**\nЗадействовано орудий: `{len(GLOBAL_FLEET)}`")
    
    success = 0
    for acc in GLOBAL_FLEET:
        if send_strike(p[2], p[3], p[4], "legal", acc): success += 1
        await asyncio.sleep(1)
        
    report = f"✅ **УДАР ЗАВЕРШЕН!**\n\n🎯 Цель: @{p[2]}\n🔥 Успешных попаданий: `{success}`\n📡 Отчет отправлен в @OslntResource"
    await status.edit_text(report)
    
    # ОТПРАВКА В ЛОГ-КАНАЛ
    try:
        await bot.send_message(LOG_CHANNEL, f"🔥 **STRIKE REPORT**\n\n👤 Цель: @{p[2]}\n🆔 ID: `{p[3]}`\n🚀 Мощность: `{success} писем` \n⚔️ Оператор: `{c.from_user.id}`")
    except: pass

@dp.message_handler(lambda m: m.text == "➕ ДОБАВИТЬ ОРУДИЕ")
async def add_mail(m: types.Message):
    await m.answer("📝 Введите: `почта:пароль_приложения` \nВаше орудие поможет всему сообществу!")

@dp.message_handler(lambda m: ":" in m.text)
async def handle_add(m: types.Message):
    try:
        e, p = m.text.split(':')
        GLOBAL_FLEET.append((e.strip(), p.strip().replace(" ","")))
        await m.answer(f"✅ **Орудие принято!** Всего стволов: `{len(GLOBAL_FLEET)}`")
    except: pass

if __name__ == '__main__':
    Thread(target=run_web).start()
    executor.start_polling(dp, skip_updates=True)
