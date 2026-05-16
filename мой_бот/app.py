import telebot
import requests
import sqlite3
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
import time
import random
import os
from flask import Flask
import threading

TOKEN = '8352640245:AAFlnxkvrHpW5foObSupcWTb3xOgYSYuujw'
OCR_API_KEY = 'K85192594388957'

FREE_LIMIT = 4
PREMIUM_LIGHT_LIMIT = 10
PREMIUM_PRO_LIMIT = 999999
PREMIUM_LIGHT_PRICE = 25
PREMIUM_PRO_PRICE = 50
REFERRAL_BONUS = 3
REFERRAL_INCOME_PERCENT = 10

bot = telebot.TeleBot(TOKEN)
active_tasks = {}

def init_db():
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            photos_today INTEGER DEFAULT 0,
            last_date TEXT,
            premium_level INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT 0,
            referral_count INTEGER DEFAULT 0,
            bonus_photos INTEGER DEFAULT 0,
            username TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT photos_today, last_date, premium_level, referred_by, referral_count, bonus_photos, username FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'photos_today': row[0], 'last_date': row[1], 'premium_level': row[2], 'referred_by': row[3], 'referral_count': row[4], 'bonus_photos': row[5], 'username': row[6]}
    else:
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect('bot_users.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (user_id, photos_today, last_date, premium_level, referred_by, referral_count, bonus_photos, username) VALUES (?, 0, ?, 0, 0, 0, 0, ?)', (user_id, today, ''))
        conn.commit()
        conn.close()
        return {'photos_today': 0, 'last_date': today, 'premium_level': 0, 'referred_by': 0, 'referral_count': 0, 'bonus_photos': 0, 'username': ''}

def update_user(user_id, photos_today=None, premium_level=None, bonus_photos=None, username=None):
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    if photos_today is not None:
        cursor.execute('UPDATE users SET photos_today = ?, last_date = ? WHERE user_id = ?', (photos_today, datetime.now().strftime('%Y-%m-%d'), user_id))
    if premium_level is not None:
        cursor.execute('UPDATE users SET premium_level = ? WHERE user_id = ?', (premium_level, user_id))
    if bonus_photos is not None:
        cursor.execute('UPDATE users SET bonus_photos = ? WHERE user_id = ?', (bonus_photos, user_id))
    if username is not None:
        cursor.execute('UPDATE users SET username = ? WHERE user_id = ?', (username, user_id))
    conn.commit()
    conn.close()

def generate_example():
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    op = random.choice(['+', '-', '*'])
    if op == '+': return f"{a} + {b}", a + b
    elif op == '-': return f"{a} - {b}", a - b
    else: return f"{a} * {b}", a * b

def quick_buttons():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("🎲 Случайный пример", callback_data="generate"))
    markup.add(InlineKeyboardButton("📊 Мои фото", callback_data="stats"))
    markup.add(InlineKeyboardButton("🏠 Главное меню", callback_data="menu"))
    return markup

def main_menu(user_id):
    user = get_user(user_id)
    if user['premium_level'] == 2: status = "👑 Premium Pro (безлимит)"
    elif user['premium_level'] == 1: status = "🌟 Premium Light (10 фото/день)"
    else: status = "🔓 Бесплатный (4 фото/день)"
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("📊 Мои фото", callback_data="stats"))
    markup.add(InlineKeyboardButton("🎲 Случайный пример", callback_data="generate"))
    markup.add(InlineKeyboardButton("🏆 Топ пользователей", callback_data="top"))
    markup.add(InlineKeyboardButton("👥 Привести друга", callback_data="referral"))
    markup.add(InlineKeyboardButton("⭐ Premium Light (25⭐)", callback_data="buy_premium_light"))
    markup.add(InlineKeyboardButton("👑 Premium Pro (50⭐)", callback_data="buy_premium_pro"))
    markup.add(InlineKeyboardButton("❓ Помощь", callback_data="help"))
    return markup, status

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    update_user(user_id, username=message.from_user.username or '')
    markup, status = main_menu(user_id)
    bot.send_message(message.chat.id, f"🚀 Добро пожаловать!\n\nТвой статус: {status}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    if call.data == "menu":
        markup, status = main_menu(user_id)
        bot.edit_message_text(f"🏠 Главное меню\n\nТвой статус: {status}", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif call.data == "stats":
        user = get_user(user_id)
        bot.send_message(call.message.chat.id, f"📊 Статистика\nФото сегодня: {user['photos_today']}\nДрузей: {user['referral_count']}")
    elif call.data == "generate":
        example, answer = generate_example()
        active_tasks[user_id] = {'example': example, 'answer': answer}
        bot.send_message(call.message.chat.id, f"🎲 Реши пример:\n\n{example} = ?", reply_markup=quick_buttons())
    elif call.data == "top":
        bot.send_message(call.message.chat.id, "🏆 Топ пользователей\nСкоро появится!")
    elif call.data == "referral":
        bot.send_message(call.message.chat.id, f"👥 Твоя ссылка:\nhttps://t.me/{bot.get_me().username}?start=ref_{user_id}")
    elif call.data == "help":
        bot.send_message(call.message.chat.id, "❓ Помощь\nПросто напиши пример или отправь фото!")
    elif call.data == "buy_premium_light":
        bot.send_invoice(call.message.chat.id, title="⭐ Premium Light", description="10 фото в день", invoice_payload="light", provider_token="", currency="XTR", prices=[telebot.types.LabeledPrice("Premium Light", PREMIUM_LIGHT_PRICE)])
    elif call.data == "buy_premium_pro":
        bot.send_invoice(call.message.chat.id, title="👑 Premium Pro", description="Безлимит фото", invoice_payload="pro", provider_token="", currency="XTR", prices=[telebot.types.LabeledPrice("Premium Pro", PREMIUM_PRO_PRICE)])

@bot.pre_checkout_query_handler(func=lambda query: True)
def handle_pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def handle_payment(message):
    update_user(message.from_user.id, premium_level=1 if message.successful_payment.invoice_payload == "light" else 2)
    bot.send_message(message.chat.id, "✅ Premium активирован!")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()
    if user_id in active_tasks:
        try:
            user_answer = int(text)
            if user_answer == active_tasks[user_id]['answer']:
                bot.reply_to(message, f"✅ Правильно! {active_tasks[user_id]['example']} = {active_tasks[user_id]['answer']}", reply_markup=quick_buttons())
            else:
                bot.reply_to(message, f"❌ Неправильно! {active_tasks[user_id]['example']} = {active_tasks[user_id]['answer']}", reply_markup=quick_buttons())
            del active_tasks[user_id]
        except:
            bot.reply_to(message, "❓ Напиши число!")
    else:
        bot.reply_to(message, "Напиши /start для начала")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "📸 Фото получено, но распознавание временно отключено для этой версии. Напиши пример текстом!")

app = Flask(__name__)
@app.route('/')
def index():
    return "Bot is running!"

def run_bot():
    init_db()
    print("✅ Бот запущен!")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

 
