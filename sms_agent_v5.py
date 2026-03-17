#!/usr/bin/env python3
"""
=============================================================================
SMS AGENT v5.0 - Ishonchli SMS Yuborish Tizimi
=============================================================================
Muallif: Orifxon Marufxonov
Versiya: 5.0
=============================================================================

TERMUXDA O'RNATISH:
1. Bu faylni ~/termux_agent.py ga saqlang
2. credentials.json ni ~/ ga ko'chiring
3. Ishga tushirish: python ~/termux_agent.py

WIDGET YARATISH:
mkdir -p ~/.shortcuts
echo 'python ~/termux_agent.py' > ~/.shortcuts/SMS
chmod +x ~/.shortcuts/SMS
=============================================================================
"""

import time
import os
import subprocess
import sys

# Kutubxonalarni tekshirish
try:
    import requests
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError as e:
    print(f"XATO: Kerakli kutubxona topilmadi: {e}")
    print("O'rnatish: pip install requests gspread oauth2client")
    sys.exit(1)

# =============================================================================
# SOZLAMALAR
# =============================================================================
# Avtomatik ravishda SETTINGS dan yuklanadi
SETTINGS_SHEET_NAME = "Navbatchilik_Jadvali"
SETTINGS_WORKSHEET = "SETTINGS"

# Default (zaxira) konfiguratsiya
DEFAULT_FLOOR_SHEETS = {
    "4-etaj": "Navbatchilik_Jadvali",
    "3-etaj": "TTJ 3-etaj Navbatchilik"
}

CREDS_FILE = os.path.expanduser("~/credentials.json")
TELEGRAM_TOKEN = "8259734572:AAGeJLKmmruLByDjx81gdi1VcjNt3ZnX894"
ADMIN_CHAT_ID = "7693191223"

# SMS orasidagi kutish vaqti (sekund)
SMS_DELAY = 3

# Google Sheet tekshirish orasidagi vaqt (sekund)
CHECK_INTERVAL = 15

# =============================================================================
# YORDAMCHI FUNKSIYALAR
# =============================================================================

def log(message, level="INFO"):
    """Konsolga log yozish"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def send_telegram(message):
    """Telegramga xabar yuborish"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": ADMIN_CHAT_ID, "text": message}, timeout=10)
        return True
    except Exception as e:
        log(f"Telegram xatosi: {e}", "ERROR")
        return False

def validate_phone(phone):
    """Telefon raqamini tekshirish va tozalash"""
    if not phone:
        return None
    
    # String ga aylantirish
    phone = str(phone)
    
    # Keraksiz belgilarni olib tashlash
    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    phone = phone.replace("(", "").replace(")", "").replace(".0", "")
    
    # Faqat raqamlarni olish
    phone = ''.join(filter(str.isdigit, phone))
    
    # Uzunlikni tekshirish (O'zbekiston: 12 yoki 9 raqam)
    if len(phone) < 9:
        return None
    
    # Agar 9 ta raqam bo'lsa, 998 qo'shish
    if len(phone) == 9:
        phone = "998" + phone
    
    return phone

def send_sms(phone, message):
    """Termux orqali SMS yuborish"""
    try:
        # Telefon raqamini tekshirish
        clean_phone = validate_phone(phone)
        if not clean_phone:
            log(f"Noto'g'ri telefon raqami: {phone}", "ERROR")
            return False
        
        log(f"SMS yuborilmoqda: {clean_phone}")
        
        # Termux SMS buyrug'i
        result = subprocess.run(
            ["termux-sms-send", "-n", clean_phone, message],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            log(f"SMS yuborildi: {clean_phone}", "OK")
            return True
        else:
            log(f"SMS xatosi: {result.stderr}", "ERROR")
            return False
            
    except subprocess.TimeoutExpired:
        log(f"SMS timeout: {phone}", "ERROR")
        return False
    except Exception as e:
        log(f"SMS xatosi: {e}", "ERROR")
        return False

# =============================================================================
# GOOGLE SHEETS
# =============================================================================

def get_google_client():
    """Google Sheets clientini olish"""
    if not os.path.exists(CREDS_FILE):
        log(f"credentials.json topilmadi: {CREDS_FILE}", "ERROR")
        send_telegram(f"XATO: credentials.json topilmadi!")
        return None
    
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        log(f"Google Sheets ulanish xatosi: {e}", "ERROR")
        return None

def load_floor_config(client):
    """Google Sheets SETTINGS dan qavatlar konfiguratsiyasini yuklash"""
    try:
        log("Konfiguratsiya yuklanmoqda...")
        settings_spreadsheet = client.open(SETTINGS_SHEET_NAME)
        settings_sheet = settings_spreadsheet.worksheet(SETTINGS_WORKSHEET)
        all_data = settings_sheet.get_all_values()
        
        if len(all_data) < 2:
            return DEFAULT_FLOOR_SHEETS
            
        header = [h.strip().lower() for h in all_data[0]]
        rows = all_data[1:]
        
        config = {}
        for row in rows:
            row_dict = dict(zip(header, row))
            floor_id = row_dict.get("floor_id", "").strip()
            sheet_name = row_dict.get("sheet_name", "").strip()
            if floor_id and sheet_name:
                config[floor_id] = sheet_name
        
        log(f"Yuklandi: {len(config)} ta qavat")
        return config if config else DEFAULT_FLOOR_SHEETS
    except Exception as e:
        log(f"Konfiguratsiya yuklashda xato (Default ishlatiladi): {e}", "WARN")
        return DEFAULT_FLOOR_SHEETS

def process_sms_queue(client):
    """SMS navbatini qayta ishlash - barcha etajlarni tekshirish"""
    total_sent = 0
    total_errors = 0
    
    # Dinamik ravishda qavatlarni yuklash
    floor_sheets = load_floor_config(client)
    
    # Har bir etajning SMS navbatini tekshirish
    for floor_name, sheet_name in floor_sheets.items():
        try:
            spreadsheet = client.open(sheet_name)
            
            # SMS_QUEUE sahifasini olish
            try:
                queue_sheet = spreadsheet.worksheet("SMS_QUEUE")
            except:
                log(f"{floor_name}: SMS_QUEUE topilmadi", "WARN")
                continue
            
            # Barcha ma'lumotlarni olish
            all_data = queue_sheet.get_all_values()
            
            if len(all_data) <= 1:
                continue  # Faqat header bor
            
            sent_count = 0
            error_count = 0
            
            for row_idx, row in enumerate(all_data):
                # Birinchi qator - header
                if row_idx == 0:
                    continue
                
                # Qator uzunligini tekshirish
                if len(row) < 3:
                    continue
                
                phone = row[0]
                message = row[1]
                status = row[2]
                
                # Faqat PENDING statusli SMSlarni yuborish
                if status != "PENDING":
                    continue
                
                # Telefon raqamini tekshirish
                clean_phone = validate_phone(phone)
                if not clean_phone:
                    log(f"Noto'g'ri raqam, o'tkazildi: {phone}", "WARN")
                    queue_sheet.update_cell(row_idx + 1, 3, "INVALID_PHONE")
                    error_count += 1
                    continue
                
                # Talaba ismini olish
                student_name = row[4] if len(row) > 4 else ""
                
                # SMS yuborish
                if send_sms(clean_phone, message):
                    queue_sheet.update_cell(row_idx + 1, 3, "SENT")
                    sent_count += 1
                    # Har bir SMS yuborilganda Telegramga xabar
                    send_telegram(f"✅ SMS yuborildi: {student_name} ({clean_phone[-4:]})")
                else:
                    queue_sheet.update_cell(row_idx + 1, 3, "ERROR")
                    error_count += 1
                    send_telegram(f"❌ SMS xato: {student_name} ({clean_phone[-4:]})")
                
                # SMSlar orasida kutish
                time.sleep(SMS_DELAY)
            
            # Etaj bo'yicha yakuniy xabar
            if sent_count > 0 or error_count > 0:
                log(f"{floor_name}: {sent_count} yuborildi, {error_count} xato")
                send_telegram(f"📊 {floor_name}: {sent_count} ta SMS yuborildi, {error_count} ta xato")
            
            total_sent += sent_count
            total_errors += error_count
            
        except Exception as e:
            log(f"{floor_name} xatosi: {e}", "ERROR")
            send_telegram(f"⚠️ {floor_name} xatosi: {e}")
    
    return total_sent, total_errors

# =============================================================================
# ASOSIY LOOP
# =============================================================================

def main():
    """Asosiy funksiya"""
    
    # Wake lock (Termux uyquga ketmasligi uchun)
    try:
        os.system("termux-wake-lock")
    except:
        pass
    
    log("=" * 50)
    log("SMS AGENT v5.0 ishga tushdi!")
    log("=" * 50)
    
    # Telegram xabari
    send_telegram("SMS Agent v5.0 ishga tushdi!")
    
    # Asosiy loop
    while True:
        try:
            # Google Sheets ga ulanish
            client = get_google_client()
            
            if not client:
                log("Google Sheets ga ulanib bo'lmadi, qayta urinish...", "ERROR")
                time.sleep(30)
                continue
            
            # SMS navbatini tekshirish
            result = process_sms_queue(client)
            
            if isinstance(result, tuple):
                sent, errors = result
                if sent > 0 or errors > 0:
                    msg = f"Natija: {sent} yuborildi"
                    if errors > 0:
                        msg += f", {errors} xato"
                    send_telegram(msg)
                    log(msg)
            
            # Kutish
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("Agent to'xtatildi (Ctrl+C)")
            send_telegram("SMS Agent to'xtatildi")
            break
            
        except Exception as e:
            log(f"Xato: {e}", "ERROR")
            time.sleep(30)

# =============================================================================
# ISHGA TUSHIRISH
# =============================================================================

if __name__ == "__main__":
    main()
