import os
import re
import uuid
import asyncio
import logging
from typing import Optional, List, Dict

import yt_dlp
from shazamio import Shazam
import imageio_ffmpeg

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
    InlineQuery,
    InlineQueryResultAudio,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from dotenv import load_dotenv

# .env faylini yuklaymiz
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylida BOT_TOKEN ni belgilang.")

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# FFMPEG yo'lini aniqlash (Tizimda bo'lmasa imageio-ffmpeg dan oladi)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

# Yuklab olinadigan audio fayllar uchun vaqtinchalik papka
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
shazam = Shazam()

# Havolalarni (URL) aniqlash uchun regex
URL_REGEX = re.compile(
    r'^(https?:\/\/)?'  # http:// yoki https://
    r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'  # domen nomi
    r'(:\d+)?(\/.*)?$',
    re.IGNORECASE
)

# Inline query yoki boshqa xabarlar uchun audio xotira kesh (id -> audio_url/file_id)
# Maqsad: inline query yoki qayta yuklab olishda tezkor ishlash
AUDIO_CACHE: Dict[str, dict] = {}


def create_music_keyboard(song_title: str, query_id: str, web_url: Optional[str] = None) -> InlineKeyboardMarkup:
    """
    Har bir musiqaga biriktiriladigan inline tugmalar:
    1. Yuklab olish (Telegram ichida qayta saqlash/yuklash)
    2. Do‘stlarga jo‘natish (switch_inline_query orqali)
    3. Boshqa ilovalarga jo‘natish (Havola bo'lsa veb-brauzer yoki tashqi ilovada ochish)
    """
    buttons = [
        [
            InlineKeyboardButton(text="📥 Yuklab olish", callback_data=f"dl:{query_id}"),
            InlineKeyboardButton(text="↗️ Do‘stlarga jo‘natish", switch_inline_query=song_title[:60])
        ]
    ]
    if web_url:
        buttons.append([
            InlineKeyboardButton(text="🌐 Boshqa ilovada ochish", url=web_url)
        ])
    else:
        # Agar bevosita web_url bo'lmasa, qidiruv ssilkasi sifatida ochish
        search_share_url = f"https://www.google.com/search?q={song_title.replace(' ', '+')}+music"
        buttons.append([
            InlineKeyboardButton(text="🌐 Boshqa ilovalarga jo‘natish", url=search_share_url)
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def search_and_download_music(query: str, is_url: bool = False) -> Optional[dict]:
    """
    yt-dlp yordamida qo'shiq qidirish yoki havola orqali MP3 formatda yuklab olish.
    """
    unique_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"{unique_id}_%(title).50s.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_PATH,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    search_target = query if is_url else f"ytsearch1:{query}"

    loop = asyncio.get_running_loop()

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(search_target, download=True)
                if 'entries' in info:
                    if not info['entries']:
                        return None
                    info = info['entries'][0]

                # Yuklangan fayl nomini aniqlash
                filename = ydl.prepare_filename(info)
                # Kengaytmasi .mp3 ga o'zgaradi
                base, _ = os.path.splitext(filename)
                mp3_path = base + ".mp3"

                return {
                    "id": unique_id,
                    "title": info.get("title", "Noma'lum musiqa"),
                    "artist": info.get("uploader", info.get("channel", "Noma'lum ijrochi")),
                    "duration": info.get("duration", 0),
                    "file_path": mp3_path,
                    "webpage_url": info.get("webpage_url", None)
                }
            except Exception as e:
                logging.error(f"yt-dlp xatolik: {e}")
                return None

    return await loop.run_in_executor(None, _extract)


async def search_artist_top_tracks(artist_name: str, limit: int = 10) -> List[dict]:
    """
    Qo'shiqchi nomi bo'yicha eng mashhur 5-10 ta musiqasini qidirib topish.
    """
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }

    loop = asyncio.get_running_loop()

    def _get_tracks():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                search_query = f"ytsearch{limit}:{artist_name} audio"
                res = ydl.extract_info(search_query, download=False)
                tracks = []
                if 'entries' in res and res['entries']:
                    for entry in res['entries']:
                        if entry:
                            tracks.append({
                                "id": entry.get("id"),
                                "title": entry.get("title"),
                                "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                            })
                return tracks
            except Exception as e:
                logging.error(f"Ijrochi musiqalarini qidirishda xatolik: {e}")
                return []

    return await loop.run_in_executor(None, _get_tracks)


# ================== BOT BUYRUQLARI VA HANDLERLARI ==================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """
    /start buyrug'i uchun handler. Bot imkoniyatlari haqida to'liq yo'riqnoma beradi.
    """
    user_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
    welcome_text = (
        f"Assalomu alaykum, <b>{user_name}</b>! 🎵\n\n"
        "Men sizning ko‘p funksiyali musiqa botingizman.\n\n"
        "<b>Quyidagi imkoniyatlar mavjud:</b>\n"
        "1️⃣ <b>Qo‘shiq qidirish:</b> Musiqa nomini yozing (masalan: <i>Xamdam Sobirov Yillar</i>)\n"
        "2️⃣ <b>Havola orqali yuklash:</b> YouTube, Instagram, TikTok, SoundCloud va h.k. havolasini yuboring\n"
        "3️⃣ <b>Videodan musiqani aniqlash (Shazam):</b> Video yoki dumaloq video (video note) yuboring\n"
        "4️⃣ <b>Qo‘shiqchi musiqalari:</b> <code>/artist Qo‘shiqchi ismi</code> buyrug‘ini yuboring (masalan: <code>/artist Tohir Sodiqov</code>)\n\n"
        "Kerakli musiqani topish uchun shunchaki matn, havola yoki video yuboring!"
    )
    await message.answer(welcome_text, parse_mode="HTML")


@dp.message(Command("artist"))
async def cmd_artist(message: Message):
    """
    4-band: Qo‘shiqchi ismi bo‘yicha musiqalarini chiqarish.
    Foydalanish: /artist Qo'shiqchi ismi
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(
            "Iltimos, ijrochi ismini kiriting!\n"
            "Masalan: <code>/artist Sherali Jo'rayev</code> yoki <code>/artist Konsta</code>",
            parse_mode="HTML"
        )
        return

    artist_name = args[1].strip()
    status_msg = await message.answer(f"🔎 <b>{artist_name}</b> ijrosidagi eng sara musiqalar qidirilmoqda...", parse_mode="HTML")

    tracks = await search_artist_top_tracks(artist_name, limit=8)
    if not tracks:
        await status_msg.edit_text("❌ Ushbu ijrochi bo‘yicha musiqalar topilmadi.")
        return

    # Inline klaviatura tuzamiz
    inline_keyboard = []
    text_lines = [f"🎵 <b>{artist_name}</b> — Eng sara musiqalari:\n"]

    for idx, track in enumerate(tracks, 1):
        clean_title = track['title'][:55]
        text_lines.append(f"{idx}. {clean_title}")
        inline_keyboard.append([
            InlineKeyboardButton(
                text=f"▶️ {idx}. {clean_title}",
                callback_data=f"yt:{track['id']}"
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await status_msg.edit_text(
        "\n".join(text_lines) + "\n\nKerakli musiqani yuklab olish uchun quyidagi tugmalardan birini bosing:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.message(F.video | F.video_note)
async def handle_video_shazam(message: Message):
    """
    3-band: Video yoki Dumaloq video (video note) orqali musiqani aniqlash (Shazam funksiyasi)
    va to'liq MP3 variantini topib yuborish.
    """
    status_msg = await message.answer("🎧 Videodagi musiqa aniqlanmoqda (Shazam)...")

    temp_video = os.path.join(DOWNLOAD_DIR, f"shazam_{uuid.uuid4().hex[:8]}.mp4")
    try:
        # Video faylni yuklab olamiz
        file_id = message.video.file_id if message.video else message.video_note.file_id
        await bot.download(file_id, destination=temp_video)

        # Shazam orqali tanish
        out = await shazam.recognize(temp_video)
        track = out.get("track")

        if not track:
            await status_msg.edit_text("😔 Kechirasiz, videodagi musiqani aniqlab bo‘lmadi.")
            return

        title = track.get("title", "")
        subtitle = track.get("subtitle", "")
        full_title = f"{subtitle} - {title}" if subtitle else title

        await status_msg.edit_text(f"✅ Musiqa aniqlandi: <b>{full_title}</b>\n📥 To‘liq MP3 varianti yuklanmoqda...", parse_mode="HTML")

        # Musiqaning to'liq MP3 formatini YouTube orqali qidirib yuklaymiz
        music_data = await search_and_download_music(full_title, is_url=False)
        if not music_data or not os.path.exists(music_data["file_path"]):
            await status_msg.edit_text(f"✅ Musiqa nomi: <b>{full_title}</b>\n❌ Afsuski, musiqani yuklab olish imkoni bo‘lmadi.", parse_mode="HTML")
            return

        # Inline tugmalar yasaymiz
        q_id = music_data["id"]
        AUDIO_CACHE[q_id] = music_data
        kb = create_music_keyboard(full_title, q_id, music_data.get("webpage_url"))

        audio_file = FSInputFile(music_data["file_path"], filename=f"{full_title}.mp3")
        await message.answer_audio(
            audio=audio_file,
            title=title,
            performer=subtitle,
            duration=music_data.get("duration", 0),
            caption=f"🎵 <b>{full_title}</b>\n🔍 <i>Shazam orqali aniqlandi</i>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await status_msg.delete()

        # Faylni o'chiramiz
        if os.path.exists(music_data["file_path"]):
            os.remove(music_data["file_path"])

    except Exception as e:
        logging.error(f"Shazam xatolik: {e}")
        await status_msg.edit_text("❌ Videoni qayta ishlashda xatolik yuz berdi.")
    finally:
        if os.path.exists(temp_video):
            os.remove(temp_video)


@dp.callback_query(F.data.startswith("yt:"))
async def callback_download_track(callback: CallbackQuery):
    """
    Qo'shiqchining musiqalar ro'yxatidan tanlangan trekni yuklab beruvchi callback handler.
    """
    track_id = callback.data.split(":", 1)[1]
    url = f"https://www.youtube.com/watch?v={track_id}"

    await callback.answer("Yuklanmoqda...")
    status_msg = await callback.message.answer("⏳ Tanlangan musiqa yuklanmoqda, kuting...")

    music_data = await search_and_download_music(url, is_url=True)
    if not music_data or not os.path.exists(music_data["file_path"]):
        await status_msg.edit_text("❌ Musiqani yuklab bo‘lmadi.")
        return

    q_id = music_data["id"]
    AUDIO_CACHE[q_id] = music_data
    kb = create_music_keyboard(music_data["title"], q_id, music_data.get("webpage_url"))

    audio_file = FSInputFile(music_data["file_path"], filename=f"{music_data['title']}.mp3")
    await callback.message.answer_audio(
        audio=audio_file,
        title=music_data["title"],
        performer=music_data.get("artist"),
        duration=music_data.get("duration", 0),
        caption=f"🎵 <b>{music_data['title']}</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await status_msg.delete()

    if os.path.exists(music_data["file_path"]):
        os.remove(music_data["file_path"])


@dp.callback_query(F.data.startswith("dl:"))
async def callback_download_cached(callback: CallbackQuery):
    """
    'Yuklab olish' tugmasi bosilganda xabar berish yoki tasdiqlash.
    """
    await callback.answer("Ushbu musiqa allaqachon chatda yuklangan. Fayl ustiga bosib saqlab olishingiz mumkin! 💾", show_alert=True)


@dp.message(F.text)
async def handle_text_or_url(message: Message):
    """
    1-band: Qo‘shiq nomi bo‘yicha qidiruv
    2-band: Havola (URL) orqali musiqa yuklash (noto'g'ri bo'lsa ogohlantirish)
    """
    text = message.text.strip()

    # Agar matn URL manzil (havola) bo'lsa
    if URL_REGEX.match(text):
        status_msg = await message.answer("🔄 Havola tekshirilmoqda va audio ajratilmoqda...")

        music_data = await search_and_download_music(text, is_url=True)

        # Agar havoladan audio ajratib bo'lmasa yoki musiqa bo'lmagan sayt bo'lsa
        if not music_data or not os.path.exists(music_data["file_path"]):
            await status_msg.edit_text("⚠️ Bu musiqaning ssilkasi emas yoki ushbu havoladan audio yuklab bo‘lmadi.")
            return

        q_id = music_data["id"]
        AUDIO_CACHE[q_id] = music_data
        kb = create_music_keyboard(music_data["title"], q_id, music_data.get("webpage_url"))

        audio_file = FSInputFile(music_data["file_path"], filename=f"{music_data['title']}.mp3")
        await message.answer_audio(
            audio=audio_file,
            title=music_data["title"],
            performer=music_data.get("artist"),
            duration=music_data.get("duration", 0),
            caption=f"🎵 <b>{music_data['title']}</b>\n🔗 <i>Havoladan yuklandi</i>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await status_msg.delete()

        if os.path.exists(music_data["file_path"]):
            os.remove(music_data["file_path"])
        return

    # Agar matn qo'shiq nomi bo'lsa (Qidiruv)
    status_msg = await message.answer(f"🔍 <b>\"{text}\"</b> musiqasi qidirilmoqda...", parse_mode="HTML")

    music_data = await search_and_download_music(text, is_url=False)
    if not music_data or not os.path.exists(music_data["file_path"]):
        await status_msg.edit_text("❌ Hech qanday musiqa topilmadi. Iltimos, boshqa nom bilan qidirib ko‘ring.")
        return

    q_id = music_data["id"]
    AUDIO_CACHE[q_id] = music_data
    kb = create_music_keyboard(music_data["title"], q_id, music_data.get("webpage_url"))

    audio_file = FSInputFile(music_data["file_path"], filename=f"{music_data['title']}.mp3")
    await message.answer_audio(
        audio=audio_file,
        title=music_data["title"],
        performer=music_data.get("artist"),
        duration=music_data.get("duration", 0),
        caption=f"🎵 <b>{music_data['title']}</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await status_msg.delete()

    if os.path.exists(music_data["file_path"]):
        os.remove(music_data["file_path"])


@dp.inline_query()
async def inline_share_handler(inline_query: InlineQuery):
    """
    5-band: 'Do‘stlarga jo‘natish' (switch_inline_query) orqali boshqa chatlarga
    tezda ulashish uchun Inline Query handler.
    """
    query = inline_query.query.strip()
    if not query:
        return

    results = [
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=f"Musiqani ulashish: {query}",
            input_message_content=InputTextMessageContent(
                message_text=f"🎵 Do‘stim, ushbu musiqani tinglab ko‘r: <b>{query}</b>",
                parse_mode="HTML"
            ),
            description="Ushbu musiqani do‘stlaringiz bilan bo‘lishing"
        )
    ]
    await inline_query.answer(results=results, cache_time=5)


async def main():
    logging.info("Musiqa boti muvaffaqiyatli ishga tushdi!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
