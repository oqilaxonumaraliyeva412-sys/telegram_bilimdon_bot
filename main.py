
import os
import random
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# BOT TOKEN (Render / .env o'zgaruvchisidan olinadi)
TOKEN = os.getenv("BOT_TOKEN", "9137423041:AAEBtoJnEwBcPV5s9yRqbbaZU02T28HvduE")

bot = telebot.TeleBot(TOKEN)

# DATABASE
db = sqlite3.connect("bilimdon.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    xp INTEGER DEFAULT 0,
    tests INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0
)
""")
db.commit()

# 15 TA FAN
subjects = [
    "📐 Matematika",
    "🌍 Geografiya",
    "📜 Tarix",
    "🇬🇧 Ingliz tili",
    "🧬 Biologiya",
    "⚗️ Kimyo",
    "⚡ Fizika",
    "📖 Ona tili",
    "📚 Adabiyot",
    "💻 Informatika",
    "🏛️ Huquq",
    "🌱 Tabiatshunoslik",
    "🕌 Tarbiya",
    "🎨 San'at",
    "🧠 Mantiq"
]

# FOYDALANUVCHI TESTLARI
sessions = {}


def register_user(user):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)",
        (user.id, user.first_name)
    )
    db.commit()


# MATEMATIKA UCHUN SAVOLLAR YARATISH
def generate_math_questions():
    questions = []

    for i in range(30):
        a = random.randint(5, 100)
        b = random.randint(2, 30)

        operation = random.choice(["+", "-", "*"])

        if operation == "+":
            answer = a + b
            question = f"{a} + {b} = ?"

        elif operation == "-":
            answer = a - b
            question = f"{a} - {b} = ?"

        else:
            answer = a * b
            question = f"{a} × {b} = ?"

        options = {answer}

        while len(options) < 4:
            options.add(answer + random.randint(-20, 20))

        options = list(options)
        random.shuffle(options)

        questions.append({
            "question": question,
            "options": options,
            "answer": answer
        })

    return questions


# ASOSIY MENYU
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    markup.row("📚 Fanlarni tanlash")
    markup.row("🏆 Mening natijam", "🥇 Reyting")
    markup.row("ℹ️ Bot haqida")

    return markup


# FANLAR MENYUSI
def subjects_menu():
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)

    for i, subject in enumerate(subjects):
        markup.add(
            telebot.types.InlineKeyboardButton(
                subject,
                callback_data=f"subject_{i}"
            )
        )

    return markup


# TESTNI BOSHLASH
def start_test(call, subject_index):
    user_id = call.from_user.id
    subject = subjects[subject_index]

    if subject_index != 0:
        bot.send_message(
            user_id,
            f"{subject} savollari tayyorlanmoqda. "
            "Hozircha matematika testini ishlashing mumkin."
        )
        return

    questions = generate_math_questions()

    sessions[user_id] = {
        "questions": questions,
        "current": 0,
        "correct": 0,
        "subject": subject
    }

    bot.send_message(
        user_id,
        f"🎓 {subject}\n"
        "Test boshlandi!\n\n"
        "Jami: 30 ta savol.\n"
        "Har bir to'g'ri javob = 1 ball."
    )

    send_question(user_id)


# SAVOLNI CHIQARISH
def send_question(user_id):
    session = sessions[user_id]

    index = session["current"]
    question = session["questions"][index]

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)

    for option in question["options"]:
        markup.add(
            telebot.types.InlineKeyboardButton(
                str(option),
                callback_data=f"answer_{option}"
            )
        )

    bot.send_message(
        user_id,
        f"📝 Savol {index + 1}/30\n\n"
        f"{question['question']}",
        reply_markup=markup
    )


# JAVOBLARNI TEKSHIRISH
@bot.callback_query_handler(
    func=lambda call: call.data.startswith("answer_")
)
def check_answer(call):
    user_id = call.from_user.id

    if user_id not in sessions:
        bot.answer_callback_query(
            call.id,
            "Test topilmadi!"
        )
        return

    session = sessions[user_id]

    index = session["current"]
    question = session["questions"][index]

    selected = int(call.data.split("_")[1])

    if selected == question["answer"]:
        session["correct"] += 1
        bot.answer_callback_query(
            call.id,
            "✅ To'g'ri javob!"
        )
    else:
        bot.answer_callback_query(
            call.id,
            "❌ Noto'g'ri javob!"
        )

    try:
        bot.edit_message_reply_markup(
            user_id,
            call.message.message_id,
            reply_markup=None
        )
    except Exception:
        pass

    session["current"] += 1

    if session["current"] >= 30:
        finish_test(user_id)
    else:
        send_question(user_id)


# TEST YAKUNI
def finish_test(user_id):
    session = sessions[user_id]

    correct = session["correct"]
    wrong = 30 - correct
    percent = correct * 100 // 30

    xp = correct * 10

    if correct <= 5:
        grade = "Ko'proq harakat qil! 💪"
    elif correct <= 10:
        grade = "Yaxshi, yana mashq qil! 👍"
    elif correct <= 15:
        grade = "Juda yaxshi! ⭐"
    elif correct <= 19:
        grade = "Ajoyib! 🔥"
    else:
        grade = "Mukammal! 🏆"

    cursor.execute("""
        UPDATE users
        SET xp = xp + ?,
            tests = tests + 1,
            correct = correct + ?
        WHERE user_id = ?
    """, (xp, correct, user_id))

    db.commit()

    bot.send_message(
        user_id,
        f"""
🏆 TEST YAKUNLANDI!

📚 Fan: {session['subject']}

✅ To'g'ri: {correct} ta
❌ Noto'g'ri: {wrong} ta

📊 Natija: {correct}/30
📈 Foiz: {percent}%

⭐ Yig'ilgan XP: +{xp}

{grade}
        """,
        reply_markup=main_menu()
    )

    del sessions[user_id]


# START
@bot.message_handler(commands=["start"])
def start(message):
    register_user(message.from_user)

    bot.send_message(
        message.chat.id,
        f"""
Assalomu alaykum, {message.from_user.first_name}! 👋

📚 BILIMDON BOTga xush kelibsiz!

Bu bot orqali 15 ta fandan
bilimingizni sinashingiz mumkin.

Har bir testda 30 ta savol mavjud.
        """,
        reply_markup=main_menu()
    )


# MENYU
@bot.message_handler(func=lambda message: True)
def menu(message):
    user_id = message.from_user.id

    if message.text == "📚 Fanlarni tanlash":
        bot.send_message(
            user_id,
            "📚 O'zingizga kerakli fanni tanlang:",
            reply_markup=subjects_menu()
        )

    elif message.text == "🏆 Mening natijam":
        cursor.execute(
            "SELECT xp, tests, correct FROM users WHERE user_id=?",
            (user_id,)
        )

        result = cursor.fetchone()

        if result:
            xp, tests, correct = result

            bot.send_message(
                user_id,
                f"""
🏆 SIZNING NATIJANGIZ

⭐ XP: {xp}
📝 Ishlangan testlar: {tests}
✅ To'g'ri javoblar: {correct}
                """
            )

    elif message.text == "🥇 Reyting":
        cursor.execute("""
            SELECT name, xp
            FROM users
            ORDER BY xp DESC
            LIMIT 10
        """)

        results = cursor.fetchall()

        text = "🏆 TOP 10 REYTING\n\n"

        for i, (name, xp) in enumerate(results, 1):
            text += f"{i}. {name} — {xp} XP\n"

        bot.send_message(user_id, text)

    elif message.text == "ℹ️ Bot haqida":
        bot.send_message(
            user_id,
            "📚 Bilimdon Bot — bilimni sinash "
            "va rivojlantirish uchun yaratilgan."
        )


# FAN TANLASH
@bot.callback_query_handler(
    func=lambda call: call.data.startswith("subject_")
)
def subject_selected(call):
    index = int(call.data.split("_")[1])

    bot.answer_callback_query(call.id)

    start_test(call, index)


# Render Free Web Service uchun Health-Check web server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bilimdon Bot muvaffaqiyatli ishlamoqda!")

    def log_message(self, format, *args):
        # Consolega ortiqcha ping xabarlarini chiqarmaydi
        return


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()


if __name__ == "__main__":
    # Render port tekshiruvidan o'tishi uchun alohida oqimda veb-server ishga tushiramiz
    threading.Thread(target=run_health_server, daemon=True).start()

    print("BILIMDON BOT ISHGA TUSHDI!")
    bot.infinity_polling(skip_pending=True)
