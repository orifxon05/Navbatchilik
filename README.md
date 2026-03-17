# 🏢 Navbatchilik va SMS Ogohlantirish Tizimi (v5.0)

Ushbu loyiha TTJ (Talabalar Turar Joyi) uchun navbatchilik jadvalini boshqarish va talabalarga avtomatik SMS ogohlantirishlar yuborish uchun ishlab chiqilgan.

## 🚀 Tizim qismlari

1.  **Web Panel (Streamlit)**: Adminlar va foydalanuvchilar uchun qulay interfeys (app.py).
2.  **Ma'lumotlar Bazasi (Google Sheets)**: Barcha ma'lumotlar reall vaqt rejimida bulutda saqlanadi.
3.  **SMS Agent (Termux)**: Android telefonda ishlovchi, SMS yuborish vazifasini bajaruvchi skript (sms_agent_v5.py).

---

## 🛠 O'rnatish (Server/PC)

### 1. Kutubxonalarni o'rnatish
```bash
pip install streamlit pandas gspread oauth2client plotly requests
```

### 2. Google Sheets Sozlamalari
- [Google Cloud Console](https://console.cloud.google.com/) orqali Service Account yarating.
- JSON kalitni yuklab oling va loyiha papkasiga `credentials.json` nomi bilan saqlang.
- JSON ichidagi `client_email` ni Google Sheets faylingizga **Editor** sifatida qo'shing.

---

## 📱 SMS Agent (Termux) O'rnatish

Ushbu qism Android telefonda SMSlarni avtomatik yuborish uchun kerak.

### 1. Telefon tayyorgarligi
- [F-Droid](https://f-droid.org/) orqali **Termux** va **Termux:API** ilovalarini o'rnating.
- Telefon sozalamalaridan Termux'ga SMS yuborish va batareya cheklovlarini olib tashlash huquqini bering.

### 2. Termux ichida sozlash
```bash
pkg update && pkg upgrade
pkg install python termux-api
pip install requests gspread oauth2client
```

### 3. Skriptni ishga tushirish
- `sms_agent_v5.py` va `credentials.json` fayllarini telefonning asosiy xotirasiga yoki Termux papkasiga yuklang.
- Agentni ishga tushiring:
```bash
python sms_agent_v5.py
```

---

## ✨ Asosiy Xususiyatlar

### 🔧 Admin Panel (app.py)
- **Dinamik Qavatlar**: `SETTINGS` sahifasi orqali yangi etajlar (bazalar) qo'shish va parollarni o'zgartirish.
- **Talabalar Yuklash**: Excel fayldan talabalar ro'yxatini to'g'ridan-to'g'ri bulutga yuklash.
- **Tahrirlash**: Reall vaqt rejimida talabalar ma'lumotlarini o'zgartirish.
- **Xavfsizlik**: Noto'g'ri parol kiritilganda IP va qurilmani bloklash, Telegramga ogohlantirish yuborish.

### 📩 SMS Agent v5.0 (Dinamik)
- **Avtomatik Navbat**: Admin panelda navbatchilik belgilanishi bilan SMS navbatga tushadi.
- **Dinamik Konfiguratsiya**: Yangi etaj qo'shilsa, agent o'zi sozlamalarni Google Sheets'dan yangilab oladi.
- **Telegram Integratsiya**: Har bir yuborilgan SMS haqida adminga Telegram orqali hisobot beradi.
- **Wake Lock**: Telefon uyqu rejimiga ketsa ham agent ishlashda davom etadi.

---

## 📂 Fayllar strukturasi

- `app.py`: Streamlit asosiy ilovasi.
- `sms_agent_v5.py`: Termux SMS skripti.
- `credentials.json`: Google Cloud ulanish kaliti.
- `login_bg.png`: Tizim dizayni uchun fon rasmi.
- `QOLLANMA.md`: Foydalanish bo'yicha qo'shimcha ko'rsatmalar.

---

## ⚠️ Muhim Eslatma
SMS yuborish narxi tarifingizga qarab belgilanishi mumkin. Ko'p miqdorda SMS yuborganda aloqa operatori tomonidan cheklovlar qo'yilmasligi uchun `SMS_DELAY` vaqtini o'zgartirmaslik tavsiya etiladi.

**Muallif**: Orifxon Marufxonov
**Bog'lanish**: @Sheeyh_o5 (Telegram)
