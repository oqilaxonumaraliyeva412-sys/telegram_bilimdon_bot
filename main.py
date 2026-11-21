import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # ixtiyoriy admin ID

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylini tekshiring.")

bot = telebot.TeleBot(TOKEN)

# DATABASE
db = sqlite3.connect("services.db", check_same_thread=False)
cursor = db.cursor()
db_lock = threading.Lock()

with db_lock:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        full_name TEXT,
        service_type TEXT,
        price TEXT,
        phone TEXT,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        full_name TEXT,
        username TEXT
    )
    """)
    db.commit()

# Holatlar (oddiy dict)
user_states = {}

PRICES = {
    "tg_bot": {
        "title": "🤖 Telegram bot yaratish",
        "price": "80,000 so'm",
        "desc": (
            "Oddiy va qulay Telegram bot:\n"
            "• Menyu va chiroyli tugmalar\n"
            "• Foydalanuvchilar bilan qulay muloqot\n"
            "• Ma'lumotlar bazasi (SQLite) va buyurtmalarni saqlash\n"
            "• Tezkor va barqaror ishlash"
        )
    },
    "tg_bot_hard": {
        "title": "⚙️ Og'ir (murakkab) Telegram bot",
        "price": "130,000 so'm",
        "desc": (
            "Katta imkoniyatlarga ega og'ir Telegram bot:\n"
            "• Murakkab mantiq va ko'p bosqichli FSM tizimi\n"
            "• To'lov tizimlari va tashqi API integratsiyalari\n"
            "• Kengaytirilgan admin boshqaruvi va statistika\n"
            "• Serverda 24/7 uzluksiz ishlash imkoniyati"
        )
    }
}

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_bot = types.KeyboardButton("🤖 Telegram bot (80,000 so'm)")
    btn_hard_bot = types.KeyboardButton("⚙️ Og'ir bot (130,000 so'm)")
    btn_prices = types.KeyboardButton("💰 Barcha narxlar")
    btn_order = types.KeyboardButton("✍️ Buyurtma berish")
    btn_contact = types.KeyboardButton("📞 Bog'lanish")
    markup.add(btn_bot, btn_hard_bot)
    markup.add(btn_prices, btn_order)
    markup.add(btn_contact)
    return markup

def get_order_inline():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🤖 Telegram bot — 80,000 so'm", callback_data="order_tg_bot"),
        types.InlineKeyboardButton("⚙️ Og'ir Telegram bot — 130,000 so'm", callback_data="order_tg_bot_hard")
    )
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name or "Mijoz"
    username = message.from_user.username or ""

    with db_lock:
        cursor.execute(
            "INSERT OR REPLACE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
            (user_id, full_name, username)
        )
        db.commit()

    text = (
        f"Assalomu alaykum, {full_name}!\n\n"
        "Telegram bot yaratish xizmati botiga xush kelibsiz.\n\n"
        "📌 Bizning narxlar:\n"
        "• 🤖 **Telegram bot yasash**: 80,000 so'm\n"
        "• ⚙️ **Og'ir Telegram bot yasash**: 130,000 so'm\n\n"
        "Kerakli bo'limni tanlang 👇"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "💰 Barcha narxlar")
def show_all_prices(message):
    text = (
        "📊 **Telegram bot yasash narxlari:**\n\n"
        "1. 🤖 **Telegram bot yasash** — `80,000 so'm`\n"
        "   - Menyu, tugmalar, aloqa va ma'lumotlar bazasi.\n\n"
        "2. ⚙️ **Og'ir Telegram bot yasash** — `130,000 so'm`\n"
        "   - Murakkab tizimlar, API, to'lovlar, maxsus admin boshqaruvi.\n\n"
        "Buyurtma berish uchun quyidagi tugmani bosing:"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✍️ Buyurtma berish", callback_data="start_order_flow"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🤖 Telegram bot (80,000 so'm)")
def info_tg_bot(message):
    item = PRICES["tg_bot"]
    text = f"**{item['title']}**\n\n💵 **Narxi:** {item['price']}\n\n{item['desc']}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✍️ Buyurtma berish", callback_data="order_tg_bot"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "⚙️ Og'ir bot (130,000 so'm)")
def info_hard_bot(message):
    item = PRICES["tg_bot_hard"]
    text = f"**{item['title']}**\n\n💵 **Narxi:** {item['price']}\n\n{item['desc']}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✍️ Buyurtma berish", callback_data="order_tg_bot_hard"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📞 Bog'lanish")
def contact_info(message):
    text = (
        "📞 **Biz bilan bog'lanish:**\n\n"
        "Savollaringiz yoki buyurtmangiz bo'lsa murojaat qiling:\n\n"
        "💬 Telegram: @admin\n"
        "📱 Telefon: +998 (90) 123-45-67\n"
        "⏰ Ish vaqti: 24/7"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "✍️ Buyurtma berish")
def order_start(message):
    bot.send_message(
        message.chat.id,
        "Qaysi xizmat bo'yicha buyurtma bermoqchisiz? Tanlang:",
        reply_markup=get_order_inline()
    )

@bot.callback_query_handler(func=lambda call: call.data in ["start_order_flow", "order_tg_bot", "order_tg_bot_hard"])
def handle_service_selection(call):
    bot.answer_callback_query(call.id)
    if call.data == "start_order_flow":
        bot.send_message(
            call.message.chat.id,
            "Qaysi xizmat turini buyurtma qilasiz?",
            reply_markup=get_order_inline()
        )
        return

    key = call.data.replace("order_", "")
    service = PRICES.get(key)
    if not service:
        return

    user_states[call.from_user.id] = {
        "step": "WAIT_PHONE",
        "service_key": key,
        "service_title": service["title"],
        "price": service["price"]
    }

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
    btn_cancel = types.KeyboardButton("❌ Bekor qilish")
    markup.add(btn_phone)
    markup.add(btn_cancel)

    bot.send_message(
        call.message.chat.id,
        f"Siz tanladingiz: **{service['title']}**\nNarxi: **{service['price']}**\n\n"
        "Iltimos, siz bilan bog'lanishimiz uchun telefon raqamingizni yuboring yoki yozib qoldiring:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "❌ Bekor qilish")
def cancel_order(message):
    user_states.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "Buyurtma bekor qilindi. Bosh menyuga qaytdingiz.",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(content_types=['contact', 'text'])
def handle_order_flow(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if not state:
        if message.text not in [
            "🤖 Telegram bot (80,000 so'm)",
            "⚙️ Og'ir bot (130,000 so'm)",
            "💰 Barcha narxlar",
            "✍️ Buyurtma berish",
            "📞 Bog'lanish"
        ]:
            bot.send_message(
                message.chat.id,
                "Kerakli bo'limni menyudan tanlang 👇",
                reply_markup=get_main_keyboard()
            )
        return

    step = state.get("step")

    if step == "WAIT_PHONE":
        if message.contact:
            phone = message.contact.phone_number
        else:
            phone = message.text.strip()

        state["phone"] = phone
        state["step"] = "WAIT_COMMENT"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("⏩ O'tkazib yuborish"))
        markup.add(types.KeyboardButton("❌ Bekor qilish"))

        bot.send_message(
            message.chat.id,
            "Rahmat! Bot haqida qanday qo'shimcha talablaringiz bo'lsa yozib qoldiring "
            "(yoki '⏩ O'tkazib yuborish' tugmasini bosing):",
            reply_markup=markup
        )

    elif step == "WAIT_COMMENT":
        if message.text == "⏩ O'tkazib yuborish":
            comment = "Qo'shimcha izoh yo'q"
        else:
            comment = message.text

        state["comment"] = comment
        user = message.from_user

        with db_lock:
            cursor.execute("""
            INSERT INTO orders (user_id, username, full_name, service_type, price, phone, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user.id,
                f"@{user.username}" if user.username else "Mavjud emas",
                user.full_name,
                state["service_title"],
                state["price"],
                state["phone"],
                state["comment"]
            ))
            db.commit()

        success_text = (
            "✅ **Buyurtmangiz qabul qilindi!**\n\n"
            f"📌 **Xizmat:** {state['service_title']}\n"
            f"💰 **Narxi:** {state['price']}\n"
            f"📱 **Telefon:** {state['phone']}\n"
            f"📝 **Izoh:** {state['comment']}\n\n"
            "Tez orada siz bilan bog'lanamiz. Rahmat!"
        )

        bot.send_message(
            message.chat.id,
            success_text,
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

        if ADMIN_ID:
            admin_msg = (
                "🔔 **Yangi buyurtma!**\n\n"
                f"👤 Mijoz: {user.full_name} ({f'@{user.username}' if user.username else 'usernamesiz'})\n"
                f"🆔 ID: `{user.id}`\n"
                f"📌 Xizmat: {state['service_title']}\n"
                f"💰 Narx: {state['price']}\n"
                f"📱 Telefon: `{state['phone']}`\n"
                f"📝 Izoh: {state['comment']}"
            )
            try:
                bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
            except Exception:
                pass

        user_states.pop(user_id, None)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot muvaffaqiyatli ishlamoqda!")

    def log_message(self, format, *args):
        return

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

if __name__ == "__main__":
    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()

    print("TELEGRAM BOT YARATISH VA NARXLAR BOTI ISHGA TUSHDI!")
    bot.infinity_polling(skip_pending=True)
