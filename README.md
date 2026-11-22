# Musiqa Boti (Aiogram 3.x)

Ushbu bot Telegram uchun ko‘p funksiyali musiqa boti bo‘lib, quyidagi vazifalarni to‘liq bajaradi:
1. **Qo‘shiq nomi bo‘yicha qidiruv** va MP3 formatda yuborish.
2. **Havola orqali yuklash** (YouTube, Instagram, TikTok, SoundCloud va h.k.). Agar havola yaroqsiz bo‘lsa: `"Bu musiqaning ssilkasi emas"` xabari chiqariladi.
3. **Videodan musiqani aniqlash (Shazam)**: Oddiy video yoki dumaloq video (video note) yuborilganda undagi musiqani aniqlab, to‘liq MP3 variantini yuboradi.
4. **Qo‘shiqchi ismi bo‘yicha barcha musiqalarini chiqarish**: `/artist Qo‘shiqchi nomi` orqali eng sara taronalarini inline tugmalar bilan chiqaradi va tanlanganini yuklab beradi.
5. **Inline tugmalar**:
   - `📥 Yuklab olish`
   - `↗️ Do‘stlarga jo‘natish` (`switch_inline_query`)
   - `🌐 Boshqa ilovada ochish` (Tashqi ilovada ochish va ulashish)

---

## 🛠 O‘rnatish va Ishga tushirish

### 1. Kerakli kutubxonalarni o‘rnatish:
Terminalda (yoki buyruqlar satrida) quyidagi buyruqni bajaring:
```bash
pip install -r requirements.txt
```
yoki alohida:
```bash
pip install aiogram yt-dlp shazamio python-dotenv aiofiles imageio-ffmpeg
```

*(Eslatma: `imageio-ffmpeg` kutubxonasi tufayli kompyuteringizga alohida FFmpeg dasturini o‘rnatib, yo‘l (PATH) kiritib o‘tirish shart emas — u avtomatik ishlaydi).*

---

### 2. Bot tokenini sozlash:
1. Telegramda [@BotFather](https://t.me/BotFather) ga kiring va `/newbot` buyrug‘i orqali yangi bot yarating.
2. BotFather bergan tokenni loyiha papkasidagi `.env` fayliga kiriting:
```env
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
```
*(Loyiha ichidagi [.env](file:///c:/Users/MADI/Desktop/First_my_creating_bot/.env) faylida tokenni saqlang).*

---

### 3. Inline rejimini yoqish (Do‘stlarga jo‘natish tugmasi ishlashi uchun):
1. [@BotFather](https://t.me/BotFather) ga o‘ting;
2. `/mybots` buyrug‘ini yuborib, botingizni tanlang;
3. **Bot Settings** -> **Inline Mode** bo‘limiga kiring;
4. **Turn on** tugmasini bosing (bu `switch_inline_query` tugmasi ishlashi uchun kerak).

---

### 4. Botni ishga tushirish:
Terminalda:
```bash
python main.py
```
yoki virtual muhitda:
```bash
.\.venv\Scripts\python.exe main.py
```

