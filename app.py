"""
============================================================================
NAVBATCHILIK - Yotoqxona Navbatchilik Tizimi
============================================================================

Copyright (c) 2024 Orifxon Marufxonov
Barcha huquqlar himoyalangan / All Rights Reserved

Bog'lanish: @Sheeyh_o5 (Telegram)
============================================================================
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import requests
import plotly.express as px
import plotly.graph_objects as go

# --- GOOGLE CLIENT (birinchi bo'lishi kerak) ---
@st.cache_resource
def get_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 1. Streamlit Cloud Secrets (Agar internetda bo'lsa)
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    # 2. Lokal fayl (Agar kompyuterda bo'lsa)
    elif os.path.exists("credentials.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    else:
        st.error("Kalit topilmadi! (credentials.json ham, Secrets ham yo'q)")
        st.stop()
        
    client = gspread.authorize(creds)
    return client

# --- TELEGRAM SOZLAMALARI ---
TELEGRAM_TOKEN = "8259734572:AAGeJLKmmruLByDjx81gdi1VcjNt3ZnX894"
ADMIN_CHAT_ID = "7693191223"

# ============================================================================
# GOOGLE SHEETS SETTINGS - DINAMIK KONFIGURATSIYA
# ============================================================================

SETTINGS_SHEET_NAME = "Navbatchilik_Jadvali"  # SETTINGS sahifasi shu Sheet'da
SETTINGS_WORKSHEET = "SETTINGS"  # Worksheet nomi

@st.cache_data(ttl=600)  # 10 daqiqa kesh (Kvota tejash uchun)
def load_floor_config():
    """Google Sheets SETTINGS dan qavatlar konfiguratsiyasini yuklash (get_all_values bilan)"""
    try:
        client = get_client()
        settings_sheet = client.open(SETTINGS_SHEET_NAME).worksheet(SETTINGS_WORKSHEET)
        all_data = settings_sheet.get_all_values()
        
        if len(all_data) < 2:
            return get_default_config()
            
        header = [h.strip().lower() for h in all_data[0]]
        rows = all_data[1:]
        
        config = {}
        for row in rows:
            # Row mapping
            row_dict = dict(zip(header, row))
            floor_id = row_dict.get("floor_id", "").strip()
            if floor_id:
                config[floor_id] = {
                    "name": row_dict.get("name", ""),
                    "password": str(row_dict.get("password", "")).strip(),
                    "sheet_name": row_dict.get("sheet_name", ""),
                    "telegram_group": str(row_dict.get("telegram_group", "")).strip()
                }
        
        return config if config else get_default_config()
    except Exception as e:
        # Xatolik bo'lsa default qaytaramiz (lekin log qilgan holda)
        return get_default_config()

def get_default_config():
    """Default konfiguratsiya (SETTINGS yo'q bo'lsa)"""
    return {
        "4-etaj": {
            "name": "4-etaj (O'g'il bolalar)",
            "password": "sheeyh",
            "sheet_name": "Navbatchilik_Jadvali",
            "telegram_group": "-1002435484678"
        },
        "3-etaj": {
            "name": "3-etaj (Qizlar)",
            "password": "3etaj",
            "sheet_name": "TTJ 3-etaj Navbatchilik",
            "telegram_group": "-1003566186790"
        }
    }

def init_settings_sheet():
    """SETTINGS sahifasini yaratish (agar yo'q bo'lsa)"""
    try:
        client = get_client()
        spreadsheet = client.open(SETTINGS_SHEET_NAME)
        
        # SETTINGS worksheet bormi?
        try:
            spreadsheet.worksheet(SETTINGS_WORKSHEET)
            return True  # Allaqachon bor
        except:
            # Yo'q, yaratamiz
            ws = spreadsheet.add_worksheet(title=SETTINGS_WORKSHEET, rows=100, cols=5)
            ws.append_row(["floor_id", "name", "password", "sheet_name", "telegram_group"])
            
            # Default ma'lumotlarni qo'shish
            ws.append_row(["4-etaj", "4-etaj (O'g'il bolalar)", "sheeyh", 
                          "Navbatchilik_Jadvali", "-1002435484678"])
            ws.append_row(["3-etaj", "3-etaj (Qizlar)", "3etaj", 
                          "TTJ 3-etaj Navbatchilik", "-1003566186790"])
            
            return True
    except Exception as e:
        st.error(f"SETTINGS yaratishda xatolik: {e}")
        return False

# Joriy etaj (session_state da saqlanadi)
def get_current_floor():
    config = load_floor_config()
    return st.session_state.get("current_floor", list(config.keys())[0])

def get_current_config():
    config = load_floor_config()
    floor = get_current_floor()
    return config.get(floor, list(config.values())[0])

TTJ_GROUP_ID = "-1002435484678"  # Default (4-etaj)

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": ADMIN_CHAT_ID, "text": message}, timeout=3)
    except:
        pass

def send_to_ttj_group(message):
    """TTJ guruhiga xabar yuborish (joriy etajga qarab)"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        # Joriy etajning Telegram guruhini olish
        config = get_current_config()
        group_id = config.get("telegram_group", TTJ_GROUP_ID)
        
        requests.post(url, data={
            "chat_id": group_id, 
            "text": message, 
            "parse_mode": "HTML"
        }, timeout=5)
    except:
        pass

# ============================================================================
# HELPER FUNCTIONS (Sheet & Data)
# ============================================================================

def get_sheet_name():
    """Joriy etajning Google Sheet nomini olish"""
    config = get_current_config()
    return config.get("sheet_name", GOOGLE_SHEET_NAME)

def get_or_create_spreadsheet(sheet_name):
    """Faylni ochish yoki topilmasa avtomatik yaratish"""
    client = get_client()
    try:
        return client.open(sheet_name)
    except gspread.exceptions.SpreadsheetNotFound:
        try:
            # Yangi Spreadsheet yaratish
            sh = client.create(sheet_name)
            ws = sh.sheet1
            headers = ["Ism", "Familiya", "Xona raqami", "Telefon raqami", "Telegram ID"]
            ws.append_row(headers)
            
            # Xabar yuborish
            send_telegram_alert(f"🆕 YANGI BAZA YARATILDI!\n\n🏢 Qavat: {sheet_name}\n📂 Fayl Google Drive'da avtomatik ochildi.")
            return sh
        except Exception as create_error:
            # Agar yaratishda xatolik bo'lsa (masalan Quota Exceeded), demak fayl yo'q va biz yarata olmadik.
            # Foydalanuvchiga aniq yechimni ko'rsatamiz.
            sa_email = "bot-user@ornate-course-481512-n2.iam.gserviceaccount.com"
            
            st.error(f"❌ XATOLIK: '{sheet_name}' fayli topilmadi!")
            st.warning("⚠️ Bot yangi fayl yaratmoqchi bo'ldi, lekin Google Drive xotirangiz to'lgan (Quota Exceeded).")
            
            st.info(f"✅ YECHIM: Iltimos, Google Drive'da '{sheet_name}' nomli Excel fayl yarating va unga quyidagi emailni 'Editor' qilib qo'shing:")
            st.code(sa_email, language="text")
            
            st.caption("Fayl nomini to'g'ri yozganingizga ishonch hosil qiling (katta-kichik harflar bir xil bo'lishi kerak).")
            st.stop()
            # raise Exception(f"Yangi baza yaratishda xatolik: {create_error}")

@st.cache_data(ttl=300) # 5 daqiqa kesh
def load_full_data(sheet_name):
    """Barcha ma'lumotlarni keshlab o'qish"""
    try:
        sh = get_or_create_spreadsheet(sheet_name)
        return sh.sheet1.get_all_values()
    except Exception as e:
        raise e

def get_main_sheet():
    sheet_name = get_sheet_name()
    sh = get_or_create_spreadsheet(sheet_name)
    return sh.sheet1

def get_queue_sheet():
    """SMS navbati - har bir etajning o'z Sheet'ida saqlanadi (alohida)"""
    client = get_client()
    # Joriy etajning Sheet nomini olish
    current_floor = get_current_floor()
    # Agar current_floor bo'lmasa yoki config bo'sh bo'lsa default
    try:
        f_config = load_floor_config()
        sheet_name = f_config[current_floor]["sheet_name"]
    except:
        sheet_name = "Navbatchilik_Jadvali"

    try:
        return client.open(sheet_name).worksheet("SMS_QUEUE")
    except:
        # SMS_QUEUE sahifasi yo'q bo'lsa, yaratish
        try:
            ws = client.open(sheet_name).add_worksheet(title="SMS_QUEUE", rows="500", cols="6")
            ws.append_row(["TELEFON", "XABAR", "STATUS", "VAQT", "ISM"])
            return ws
        except:
             return None # Agar yaratib bo'lmasa

def validate_phone(phone):
    """Telefon raqamini tekshirish va tozalash"""
    if not phone:
        return None
    phone = str(phone).replace("+", "").replace(" ", "").replace("-", "")
    phone = phone.replace("(", "").replace(")", "").replace(".0", "")
    phone = ''.join(filter(str.isdigit, phone))
    if len(phone) < 9:
        return None
    if len(phone) == 9:
        phone = "998" + phone
    return phone

def add_to_sms_queue(queue_sheet, phone, message, student_name=""):
    """SMS navbatiga xavfsiz qo'shish"""
    if not queue_sheet: return False
    
    clean_phone = validate_phone(phone)
    if not clean_phone:
        return False
    timestamp = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
    queue_sheet.append_row([clean_phone, message, "PENDING", timestamp, student_name])
    return True

# ============================================================================
# XAVFSIZLIK TIZIMI / SECURITY SYSTEM
# Copyright (c) 2024 Orifxon Marufxonov
# ============================================================================

# Xavfsizlik sozlamalari
MAX_LOGIN_ATTEMPTS = 5  # Maksimal urinishlar soni
BLOCK_TIME_MINUTES = 30  # Bloklash vaqti (daqiqa)
ALERT_THRESHOLD = 3  # Ogohlantirishdan oldin urinishlar

def get_security_state():
    """Xavfsizlik holatini olish"""
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0
    if "blocked_until" not in st.session_state:
        st.session_state.blocked_until = None
    if "last_attempt_time" not in st.session_state:
        st.session_state.last_attempt_time = None
    return st.session_state

def is_blocked():
    """Foydalanuvchi bloklangan yoki yo'qligini tekshirish"""
    state = get_security_state()
    if state.blocked_until:
        if datetime.now() < state.blocked_until:
            return True
        else:
            # Bloklash muddati tugadi
            state.blocked_until = None
            state.login_attempts = 0
    return False

def record_failed_login():
    """Muvaffaqiyatsiz kirishni qayd qilish"""
    state = get_security_state()
    state.login_attempts += 1
    state.last_attempt_time = datetime.now()
    
    # Ogohlantirishni yuborish
    if state.login_attempts >= ALERT_THRESHOLD:
        send_security_alert(state.login_attempts)
    
    # Maksimal urinishlardan oshsa bloklash
    if state.login_attempts >= MAX_LOGIN_ATTEMPTS:
        state.blocked_until = datetime.now() + timedelta(minutes=BLOCK_TIME_MINUTES)
        send_block_alert()

def reset_login_attempts():
    """Muvaffaqiyatli kirishdan keyin urinishlarni tozalash"""
    state = get_security_state()
    state.login_attempts = 0
    state.blocked_until = None

def send_security_alert(attempts):
    """Xavfsizlik ogohlantirishi yuborish"""
    tashkent_time = (datetime.utcnow() + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S')
    msg = f"""🚨 XAVFSIZLIK OGOHLANTIRISHI!

⚠️ Shubhali faoliyat aniqlandi!
📊 Noto'g'ri parol urinishlari: {attempts}
🕐 Vaqt: {tashkent_time} (Toshkent)

Agar bu siz bo'lmasangiz, parolni o'zgartiring!"""
    send_telegram_alert(msg)

def send_block_alert():
    """Bloklash haqida xabar yuborish"""
    tashkent_time = (datetime.utcnow() + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S')
    msg = f"""🔒 FOYDALANUVCHI BLOKLANDI!

❌ {MAX_LOGIN_ATTEMPTS} marta noto'g'ri parol kiritildi
⏱️ Bloklash muddati: {BLOCK_TIME_MINUTES} daqiqa
🕐 Vaqt: {tashkent_time} (Toshkent)

Ehtimol brute-force hujumi!"""
    send_telegram_alert(msg)

def get_tashkent_time():
    """Toshkent vaqtini olish (UTC+5)"""
    return (datetime.utcnow() + timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S')

def get_device_type():
    """Qurilma turini aniqlash"""
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        user_agent = headers.get("User-Agent", "").lower() if headers else ""
        
        if "android" in user_agent or "mobile" in user_agent:
            return "📱 Mobil ilova"
        elif "iphone" in user_agent or "ipad" in user_agent:
            return "🍎 iOS qurilma"
        else:
            return "💻 Kompyuter/Brauzer"
    except:
        return "🌐 Noma'lum qurilma"

def send_successful_login_alert():
    """Muvaffaqiyatli kirish haqida xabar"""
    device = get_device_type()
    tashkent_time = get_tashkent_time()
    
    # Joriy etaj nomini olish
    floor = st.session_state.get("current_floor", "4-etaj")
    f_config_alert = load_floor_config()
    floor_name = f_config_alert.get(floor, {}).get("name", floor)
    
    msg = f"""✅ TIZIMGA KIRISH

🏢 Etaj: {floor_name}
🕐 Vaqt: {tashkent_time} (Toshkent)
{device}

Agar bu siz bo'lmasangiz - darhol parolni o'zgartiring!"""
    send_telegram_alert(msg)

def log_activity(action, details=""):
    """Muhim faoliyatni qayd qilish va xabar yuborish"""
    tashkent_time = get_tashkent_time()
    msg = f"""📋 FAOLIYAT LOGI

📌 Harakat: {action}
📝 Tafsilotlar: {details}
🕐 Vaqt: {tashkent_time} (Toshkent)"""
    send_telegram_alert(msg)

def send_telegram_to_student(telegram_id, message, student_name=""):
    """Talabaga shaxsiy Telegram xabar yuborish"""
    if not telegram_id:
        return False
    
    # telegram_id ni tozalash
    tg_id = str(telegram_id).replace(".0", "").strip()
    if not tg_id or tg_id == "nan" or len(tg_id) < 5:
        return False
    
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, data={
            "chat_id": tg_id,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        
        if response.status_code == 200:
            # Muvaffaqiyatli - adminga xabar
            send_telegram_alert(f"✅ TG: {student_name} ({tg_id}) - xabar yuborildi")
            return True
        else:
            # Xato tafsilotlari
            error_info = response.json().get('description', 'Noma\'lum xato')
            send_telegram_alert(f"❌ TG: {student_name} ({tg_id}) - {error_info}")
            return False
    except Exception as e:
        send_telegram_alert(f"❌ TG: {student_name} ({tg_id}) - xato: {str(e)[:50]}")
        return False

# --- KONFIGURATSIYA ---
GOOGLE_SHEET_NAME = "Navbatchilik_Jadvali"

DUTY_TYPES = {
    "Katta Oshxona (2 kishi)": 1,
    "Kichik Oshxona (2 kishi)": 2,
    "Katta Dush (2 kishi)": 3,
    "Kichik Dush (1 kishi)": 4
}
SMS_TEMPLATES = {
    1: "Siz bugun Katta oshxonaga navbatchisiz. Ishingizga omad!",
    2: "Siz bugun Kichik oshxonaga navbatchisiz. Ishingizga omad!",
    3: "Siz bugun Katta dushga navbatchisiz. Ishingizga omad!",
    4: "Siz bugun Kichik dushga navbatchisiz. Ishingizga omad!"
}

# --- NARYAD KONFIGURATSIYA ---
NARYAD_TYPES = {
    "Qo'shimcha Zal": 11,
    "Zina": 12,
    "Kirxona": 13,
    "Sabzavotxona": 14,
    "Manaviyat": 15,
    "Kladovka": 16,
    "Katta Oshxona": 21,
    "Kichik Oshxona": 22,
    "Katta Dush": 23,
    "Kichik Dush": 24
}
# Naryad joylari nomlari (SMS uchun)
NARYAD_NAMES = {
    11: "Qo'shimcha Zal",
    12: "Zina",
    13: "Kirxona",
    14: "Sabzavotxona",
    15: "Manaviyat",
    16: "Kladovka",
    21: "Katta Oshxona",
    22: "Kichik Oshxona",
    23: "Katta Dush",
    24: "Kichik Dush"
}


st.set_page_config(
    page_title="Navbatchilik Tizimi", 
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# ZAMONAVIY DIZAYN - Glassmorphism + 3D Tugmalar
# ============================================================================
st.markdown("""
<style>
    /* ===== ASOSIY RANGLAR ===== */
    :root {
        --primary: #00D4AA;
        --primary-dark: #00B894;
        --accent: #00CEC9;
        --bg-dark: #0a0a0a;
        --bg-card: rgba(17, 17, 17, 0.8);
        --glass: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(0, 212, 170, 0.3);
        --text: #ffffff;
        --text-muted: #888888;
    }
    
    /* ===== UMUMIY STILLAR ===== */
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%);
    }
    
    /* ===== GLASSMORPHISM KARTALAR ===== */
    .glass-card {
        background: var(--glass);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 20px;
        padding: 25px;
        margin: 10px 0;
        box-shadow: 0 8px 32px rgba(0, 212, 170, 0.1);
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0, 212, 170, 0.2);
        border-color: var(--primary);
    }
    
    /* ===== 3D TUGMALAR ===== */
    .stButton > button {
        background: linear-gradient(145deg, #00D4AA, #00B894) !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 30px !important;
        color: #0a0a0a !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        box-shadow: 
            0 6px 20px rgba(0, 212, 170, 0.4),
            0 3px 6px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
        transition: all 0.2s ease !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 
            0 10px 30px rgba(0, 212, 170, 0.5),
            0 5px 10px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
    }
    
    .stButton > button:active {
        transform: translateY(1px) !important;
        box-shadow: 
            0 2px 10px rgba(0, 212, 170, 0.3),
            inset 0 2px 4px rgba(0, 0, 0, 0.2) !important;
    }
    
    /* ===== FORM SUBMIT TUGMALARI ===== */
    .stFormSubmitButton > button {
        background: linear-gradient(145deg, #00D4AA, #00B894) !important;
        border: none !important;
        border-radius: 12px !important;
        color: #0a0a0a !important;
        font-weight: 700 !important;
        box-shadow: 
            0 6px 20px rgba(0, 212, 170, 0.4),
            0 3px 6px rgba(0, 0, 0, 0.3) !important;
        transition: all 0.2s ease !important;
    }
    
    .stFormSubmitButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 30px rgba(0, 212, 170, 0.5) !important;
    }
    
    /* ===== TABLAR ===== */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--glass);
        border-radius: 15px;
        padding: 5px;
        gap: 5px;
        border: 1px solid var(--glass-border);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        color: var(--text-muted);
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(145deg, #00D4AA, #00B894) !important;
        color: #0a0a0a !important;
    }
    
    /* ===== INPUT MAYDONLARI ===== */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background: var(--glass) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 10px !important;
        color: var(--text) !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 20px rgba(0, 212, 170, 0.3) !important;
    }
    
    /* ===== JADVALLAR ===== */
    .stDataFrame {
        background: var(--glass) !important;
        border-radius: 15px !important;
        border: 1px solid var(--glass-border) !important;
        overflow: hidden;
    }
    
    /* ===== METRIKALAR ===== */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        background: linear-gradient(145deg, #00D4AA, #00CEC9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    [data-testid="stMetricLabel"] {
        color: var(--text-muted) !important;
        font-weight: 500 !important;
    }
    
    /* ===== SARLAVHALAR ===== */
    h1, h2, h3 {
        background: linear-gradient(145deg, #ffffff, #00D4AA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800 !important;
    }
    
    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a0a 0%, #1a1a2e 100%) !important;
        border-right: 1px solid var(--glass-border) !important;
    }
    
    /* ===== EXPANDER ===== */
    .streamlit-expanderHeader {
        background: var(--glass) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 10px !important;
    }
    
    /* ===== INFO/WARNING/ERROR ===== */
    .stAlert {
        background: var(--glass) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 10px !important;
    }
    
    /* ===== GLOW EFFEKT ===== */
    .glow-text {
        text-shadow: 0 0 20px rgba(0, 212, 170, 0.5);
    }
    
    /* ===== ANIMATSIYALAR ===== */
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 20px rgba(0, 212, 170, 0.3); }
        50% { box-shadow: 0 0 40px rgba(0, 212, 170, 0.6); }
    }
    
    .pulse-glow {
        animation: pulse 2s infinite;
    }
    
    /* ===== MICRO-ANIMATSIYALAR ===== */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-30px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    @keyframes scaleIn {
        from { opacity: 0; transform: scale(0.9); }
        to { opacity: 1; transform: scale(1); }
    }
    
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    
    /* Animatsiya klasslari */
    .animate-fade { animation: fadeIn 0.5s ease-out; }
    .animate-slide { animation: slideIn 0.4s ease-out; }
    .animate-scale { animation: scaleIn 0.3s ease-out; }
    .animate-float { animation: float 3s ease-in-out infinite; }
    
    /* Hover effektlari */
    .hover-lift {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .hover-lift:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 20px 40px rgba(0, 212, 170, 0.3);
    }
    
    /* Click effekti */
    .click-effect:active {
        transform: scale(0.95);
        transition: transform 0.1s;
    }
    
    /* ===== GLASSMORPHISM YAXSHILANGAN ===== */
    .glass-premium {
        background: linear-gradient(135deg, 
            rgba(255, 255, 255, 0.1) 0%, 
            rgba(255, 255, 255, 0.05) 50%,
            rgba(0, 212, 170, 0.05) 100%);
        backdrop-filter: blur(25px) saturate(180%);
        -webkit-backdrop-filter: blur(25px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 24px;
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.1),
            0 0 0 1px rgba(0, 212, 170, 0.1);
    }
    
    /* ===== ZEBRA STRIPING JADVALLAR ===== */
    [data-testid="stDataFrame"] table tbody tr:nth-child(odd) {
        background: rgba(0, 212, 170, 0.05) !important;
    }
    
    [data-testid="stDataFrame"] table tbody tr:nth-child(even) {
        background: rgba(0, 0, 0, 0.2) !important;
    }
    
    [data-testid="stDataFrame"] table tbody tr:hover {
        background: rgba(0, 212, 170, 0.15) !important;
        transition: background 0.2s ease;
    }
    
    [data-testid="stDataFrame"] table thead tr {
        background: linear-gradient(145deg, rgba(0, 212, 170, 0.2), rgba(0, 206, 201, 0.1)) !important;
    }
    
    [data-testid="stDataFrame"] table th {
        color: #00D4AA !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 2px solid rgba(0, 212, 170, 0.3) !important;
    }
    
    /* ===== SCROLL BAR ===== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-dark);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary);
        border-radius: 10px;
    }
    
    /* ===== 📱 MOBIL RESPONSIVE ===== */
    @media (max-width: 768px) {
        /* Tugmalar kichikroq */
        .stButton > button {
            padding: 10px 15px !important;
            font-size: 12px !important;
            letter-spacing: 0.5px !important;
        }
        
        /* Sarlavhalar kichikroq */
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1rem !important; }
        
        /* Metrikalar kichikroq */
        [data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
        }
        
        /* Kolonlar vertikal */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }
        
        /* Padding kamroq */
        .block-container {
            padding: 1rem !important;
        }
        
        /* Kartalar kichikroq */
        .glass-card, .glass-premium {
            padding: 15px !important;
            border-radius: 15px !important;
        }
        
        /* Form elementlari */
        .stTextInput > div > div > input {
            font-size: 16px !important; /* iOS zoom oldini olish */
        }
    }
    
    @media (max-width: 480px) {
        /* Juda kichik ekranlar */
        .stButton > button {
            padding: 8px 12px !important;
            font-size: 11px !important;
        }
        
        h1 { font-size: 1.2rem !important; }
        
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }
    }
    
    /* ===== HIDE STREAMLIT BRANDING ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Check Logout Action
if st.query_params.get("action") == "logout":
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

def check_password():
    """Returns `True` if the user had the correct password."""
    
    # URL orqali sessiyani tiklash (Refresh bo'lganda joyida qolish uchun)
    if st.query_params.get("auth") == "ok":
        st.session_state["password_correct"] = True
        
        # Rol va qavatni tiklash
        floor = st.query_params.get("floor")
        role = st.query_params.get("role")
        
        if role == "admin":
            st.session_state["is_admin"] = True
            st.session_state["current_floor"] = "admin"
        elif floor:
            st.session_state["is_admin"] = False
            st.session_state["current_floor"] = floor
            
        return True
    

    if st.session_state.get("password_correct", False):
        return True
    
    # Bloklash tekshiruvi
    if is_blocked():
        state = get_security_state()
        remaining = state.blocked_until - datetime.now()
        minutes_left = int(remaining.total_seconds() / 60) + 1
        st.error(f"🔒 Siz {minutes_left} daqiqaga bloklangansiz! Keyinroq urinib ko'ring.")
        st.warning(f"⚠️ Sabab: Juda ko'p noto'g'ri parol urinishlari")
        return False

    # Rasmni base64 ga o'tkazish
    import base64
    with open("login_bg.png", "rb") as f:
        bg_image = base64.b64encode(f.read()).decode()
    
    # Fullscreen background CSS
    st.markdown(f"""
    <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bg_image}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        
        /* Login box styling */
        .login-box {{
            background: rgba(0, 0, 0, 0.7);
            padding: 40px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            max-width: 400px;
            margin: 0 auto;
            margin-top: 5vh;
        }}
        
        .login-title {{
            color: #4FC3F7;
            text-align: center;
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .login-subtitle {{
            color: #aaa;
            text-align: center;
            font-style: italic;
            margin-bottom: 30px;
        }}
        
        /* Hide Streamlit branding */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}
        
        /* Tepadagi ortiqcha qora qutini yashirish */
        [data-testid="stHeader"] {{
            display: none !important;
        }}
        
        /* Bo'sh block containerlarni yashirish */
        .block-container:empty {{
            display: none !important;
        }}
        
        /* Sidebar yashirish */
        section[data-testid="stSidebar"] {{
            display: none !important;
        }}
        
        /* Birinchi bo'sh elementni yashirish */
        .main .block-container > div:first-child:empty {{
            display: none !important;
        }}
        
        /* Streamlit input wrapper */
        .stTextInput > div:first-child {{
            background: transparent !important;
    </style>
    """, unsafe_allow_html=True)
    
    # Login sarlavhasi (markazda)
    st.markdown("""
    <div style="text-align: center; margin-top: 15vh;">
        <p style="color: #4FC3F7; font-size: 32px; margin-bottom: 10px;">🔒 Tizimga kirish</p>
        <p style="color: #aaa; font-style: italic; margin-bottom: 30px;">TTJ Yotoqxona Navbatchilik Tizimi</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Qolgan urinishlar haqida ogohlantirish
    state = get_security_state()
    if state.login_attempts > 0:
        remaining_attempts = MAX_LOGIN_ATTEMPTS - state.login_attempts
        if remaining_attempts <= 3:
            st.warning(f"⚠️ Qolgan urinishlar: {remaining_attempts}")
    
    # Form (Enter bilan ishlaydi)
    with st.form("login_form"):
        password = st.text_input("Parolni kiriting", type="password", placeholder="Parolni kiriting va Enter bosing...", label_visibility="collapsed")
        submit_button = st.form_submit_button("🚀 Kirish", use_container_width=True)

        if submit_button:
            # Parollarni tekshirish
            password_clean = password.strip()
            
            # --- ADMIN LOGIN ---
            if password_clean == "admin05":
                reset_login_attempts()
                st.session_state["password_correct"] = True
                st.session_state["is_admin"] = True
                st.session_state["current_floor"] = "admin"
                # URL ga to'g'ri ma'lumot yozish
                st.query_params["auth"] = "ok"
                st.query_params["floor"] = "admin"
                st.query_params["role"] = "admin"
                send_telegram_alert("🔧 ADMIN PANEL'ga kirish!")
                st.rerun()

# --- DYNAMIC FLOOR LOGIN ---
            found_floor = None
            f_config_all = load_floor_config()
            for f_id, f_conf in f_config_all.items():
                if f_conf.get("password") and password_clean == str(f_conf.get("password")):
                    found_floor = f_id
                    break
            
            if found_floor:
                reset_login_attempts()
                st.session_state["password_correct"] = True
                st.session_state["is_admin"] = False
                st.session_state["current_floor"] = found_floor
                # URL ga to'g'ri ma'lumot yozish
                st.query_params["auth"] = "ok"
                st.query_params["floor"] = found_floor
                st.query_params["role"] = "user"
                send_successful_login_alert()
                st.rerun()
            else:
                record_failed_login()
                st.error("😕 Parol xato! Qaytadan urinib ko'ring.")
                st.rerun()
                
    return False

if not check_password():
    st.stop()

# ============================================================================
# ADMIN PANEL
# ============================================================================
if st.session_state.get("is_admin", False):
    # --- HEADER & NAVIGATION ---
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(255, 87, 51, 0.1) 0%, rgba(251, 133, 0, 0.1) 100%);
            border-radius: 15px;
            padding: 15px 25px;
            border: 1px solid rgba(255, 87, 51, 0.3);
        ">
            <h2 style="color: #FF5733; margin: 0;">🔧 ADMIN PANEL</h2>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.write("") # Spacing
        if st.button("🚪 Tizimdan Chiqish", type="secondary", use_container_width=True):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()
            
    # Qavatlarga o'tish
    with st.expander("👁️ Qavat ko'rinishiga o'tish (Saytni ko'rish)"):
        f_config_nav = load_floor_config()
        f_cols = st.columns(len(f_config_nav))
        for i, (f_id, f_conf) in enumerate(f_config_nav.items()):
            c_idx = i % 4 # Max 4 columns
            with f_cols[c_idx]:
                if st.button(f"🏠 {f_conf['name']}", key=f"nav_to_{f_id}", use_container_width=True):
                    st.session_state["is_admin"] = False
                    st.session_state["current_floor"] = f_id
                    
                    # URL parametrlarini yangilash (Parolsiz kirish uchun)
                    st.query_params["auth"] = "ok"
                    st.query_params["floor"] = f_id
                    st.query_params["role"] = "user"
                    
                    st.rerun()
    
    st.write("---")
    
    # Initialize Settings Sheet just in case
    init_settings_sheet()
    
    tab1, tab2, tab3 = st.tabs(["🏢 QAVATLAR SOZLAMALARI", "📤 TALABALAR YUKLASH", "📝 MA'LUMOTLARNI TAHRIRLASH"])
    
    with tab1:
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.subheader("⚙️ Qavat Sozlamalari")
        with col_t2:
            if st.button("🔄 Yangilash (Cache Clear)", help="Agar o'zgarishlar ko'rinmasa, shu tugmani bosing"):
                st.cache_data.clear()
                st.rerun()
        st.subheader("⚙️ Qavatlar Konfiguratsiyasi")
        st.info("Jadval ichidagi ma'lumotlarni o'zgartirib, pastdagi 'Saqlash' tugmasini bosing.")
        
        # Load current settings from sheet
        try:
            client = get_client()
            settings_ws = client.open(SETTINGS_SHEET_NAME).worksheet(SETTINGS_WORKSHEET)
            data = settings_ws.get_all_values() # get_all_records o'rniga values ishlatamiz xavfsizlik uchun
            
            if len(data) > 0:
                header = data[0]
                rows = data[1:]
                df_settings = pd.DataFrame(rows, columns=header)
                
                # DATA EDITOR - Tahrirlash uchun
                edited_settings = st.data_editor(
                    df_settings, 
                    num_rows="dynamic", 
                    use_container_width=True,
                    key="settings_editor"
                )
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("💾 Sozlamalarni Saqlash", type="primary"):
                        try:
                            # Tozalash va yangilash
                            settings_ws.clear()
                            
                            # Header va ma'lumotlarni birlashtirish
                            new_data = [edited_settings.columns.tolist()] + edited_settings.astype(str).values.tolist()
                            
                            # Explicit range 'A1' ishlatamiz yangi versiyalar uchun
                            settings_ws.update('A1', new_data)
                            
                            st.success("✅ Sozlamalar muvaffaqiyatli saqlandi!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Saqlashda xatoga yo'l qo'yildi: {e}")
            else:
                st.warning("Sozlamalar bo'sh yoki o'qib bo'lmadi.")

        except Exception as e:
            st.error(f"Sozlamalarni yuklashda xatolik: {e}")

    with tab2:
        st.subheader("📤 Excel Fayl Yuklash")
        
        # Dropdown for selecting target floor
        f_config_upload = load_floor_config()
        floor_options = list(f_config_upload.keys())
        target_floor_id = st.selectbox("Qaysi qavatga yuklash kerak?", floor_options, 
                                     format_func=lambda x: f_config_upload[x]["name"] if x in f_config_upload else x)
        
        if target_floor_id:
            target_sheet_name = f_config_upload[target_floor_id].get("sheet_name", GOOGLE_SHEET_NAME)
            st.info(f"📝 Tanlangan Sheet: **{target_sheet_name}**")
            
            uploaded_file = st.file_uploader("Excel faylni yuklang", type=['xlsx', 'xls', 'csv'], help="Tanlashda 'Fayllar' (Files) bo'limiga kiring")
            
            if uploaded_file:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df_upload = pd.read_csv(uploaded_file)
                    else:
                        df_upload = pd.read_excel(uploaded_file)
                        
                    st.write("Yuklangan ma'lumotlar:", df_upload.head())
                    st.caption(f"Jami: {len(df_upload)} qator")
                    
                    if st.button("🚀 Google Sheets'ga Yozish"):
                        try:
                            # Open or create target sheet
                            sh = get_or_create_spreadsheet(target_sheet_name)
                            target_ws = sh.sheet1
                            
                            # Convert to strings
                            data_to_upload = df_upload.fillna("").astype(str).values.tolist()
                            
                            # Check headers
                            first_row = target_ws.row_values(1)
                            if not first_row:
                                target_ws.append_row(df_upload.columns.tolist())
                            
                            # Append rows
                            target_ws.append_rows(data_to_upload)
                                
                            st.success(f"✅ {len(data_to_upload)} qator muvaffaqiyatli qo'shildi!")
                            send_telegram_alert(f"📤 ADMIN: {len(data_to_upload)} ta talaba yuklandi ({target_sheet_name})")
                            
                        except Exception as e:
                            st.error(f"Google Sheets xatosi: {e}")
                except Exception as e:
                    st.error(f"Faylni o'qishda xatolik: {e}")

    with tab3:
        st.subheader("📝 Talabalar Ro'yxatini Tahrirlash")
        
        # Etaj tanlash
        f_config_edit = load_floor_config()
        floor_options_edit = list(f_config_edit.keys())
        edit_floor_id = st.selectbox("Tahrirlash uchun qavatni tanlang", floor_options_edit, 
                                   format_func=lambda x: f_config_edit[x]["name"] if x in f_config_edit else x,
                                   key="edit_floor_select")
        
        if edit_floor_id:
            target_sheet_name = f_config_edit[edit_floor_id].get("sheet_name", GOOGLE_SHEET_NAME)
            
            # Yuklash tugmasi
            if st.button("🔄 Ma'lumotlarni Yuklash", key="load_data_edit"):
                st.session_state["data_loaded_for_edit"] = True
            
            if st.session_state.get("data_loaded_for_edit", False):
                try:
                    # 1. Client olish
                    client = get_client()
                    
                    # 2. Sheetni ochish (yoki yaratish)
                    try:
                        sh = get_or_create_spreadsheet(target_sheet_name)
                    except Exception as sheet_err:
                        st.error(f"❌ Fayl bilan ishlashda xato: {sheet_err}")
                        sa_email = "bot-user@ornate-course-481512-n2.iam.gserviceaccount.com"
                        st.info(f"💡 Agar fayl sizda bo'lsa, uni quyidagi email bilan 'Share' qilganingizni tekshiring: {sa_email}")
                        st.stop()
                    
                    # 3. Worksheetni olish
                    ws = sh.sheet1
                    
                    # 4. Ma'lumotlarni o'qish
                    try:
                        data = ws.get_all_values()
                    except Exception as read_error:
                        st.error(f"⚠️ Ma'lumotlarni o'qishda muammo: {read_error}")
                        st.stop()
                    
                    if len(data) > 0:
                        headers = data[0]
                        rows = data[1:]
                        
                        # DataFrame yaratish
                        unique_headers = []
                        seen = {}
                        for h in headers:
                            h_str = str(h).strip() # Headerlarni tozalash
                            if h_str in seen:
                                seen[h_str] += 1
                                unique_headers.append(f"{h_str}_{seen[h_str]}")
                            else:
                                seen[h_str] = 0
                                unique_headers.append(h_str)
                        
                        try:
                            df_edit = pd.DataFrame(rows, columns=unique_headers)
                        except Exception as e:
                            st.error(f"Jadval tuzishda xatolik: {e}")
                            st.write("Headerlar:", unique_headers)
                            st.write("Birinchi qator:", rows[0] if rows else "Bo'sh")
                            st.stop()
                        
                        st.subheader(f"📋 {target_sheet_name}")
                        st.caption(f"Jami talabalar: {len(df_edit)}")
                        
                        # Tahrirlash oynasi
                        edited_df = st.data_editor(
                            df_edit,
                            num_rows="dynamic",
                            use_container_width=True,
                            key="student_data_editor"
                        )
                        
                        st.warning("⚠️ 'Saqlash' tugmasini bosganingizda Google Sheetdagi ESKI ma'lumotlar o'chib, yangisi yoziladi!")
                        
                        if st.button("💾 O'zgarishlarni Saqlash", type="primary", key="save_student_data"):
                            try:
                                ws.clear()
                                # Header va ma'lumotlarni tayyorlash
                                update_values = [edited_df.columns.tolist()] + edited_df.fillna("").astype(str).values.tolist()
                                ws.update(values=update_values)
                                st.success("✅ Ma'lumotlar saqlandi!")
                                st.balloons()
                                # Keshni tozalash
                                st.cache_data.clear()
                            except Exception as e:
                                st.error(f"Saqlashda xatolik: {e}")
                    else:
                        st.info("Jadval bo'sh.")
                except Exception as e:
                    st.error(f"Kutilmagan xatolik: {type(e).__name__} - {e}")

    st.stop() # Stop execution so admin sees only this panel







# --- HEADER & NAVIGATION ---
current_config = get_current_config()
floor_name = current_config.get("name", "4-etaj")

# 1. Sidebar (Menyu)
with st.sidebar:
    st.title("Menyu")
    st.write(f"🏢 **{floor_name}**")
    if st.button("🚪 Tizimdan Chiqish", key="logout_sidebar", type="primary", use_container_width=True):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()



# --- MA'LUMOTNI O'QISH ---
try:
    # Keshlab o'qish (sheet_name o'zgarmasa keshdan oladi)
    s_name = get_sheet_name()
    all_values = load_full_data(s_name)
    
    if not all_values:
        st.error("Jadval bo'sh!")
        st.stop()
        
    # Headerlarni olish
    headers = all_values[0]
    
    # Bugungi sana headerda bormi?
    # Dublikatlarni tekshirish va to'g'irlash
    unique_headers = []
    seen = {}
    
    for h in headers:
        if h in seen:
            seen[h] += 1
            unique_headers.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            unique_headers.append(h)
            
    # DataFrame yaratish
    df = pd.DataFrame(all_values[1:], columns=unique_headers)
    
    # Telefon raqamini tozalash
    if 'telefon raqami' in df.columns:
        df['telefon raqami'] = df['telefon raqami'].astype(str).str.replace(".0", "", regex=False)
except Exception as e:
    import traceback
    st.error(f"❌ Google Sheetga ulanishda xatolik: {e}")
    with st.expander("🔍 Texnik tafsilotlar (Debug)"):
        st.code(traceback.format_exc())
    st.stop()

st.markdown(f"""
<div style="background: linear-gradient(135deg, rgba(0, 212, 170, 0.1) 0%, rgba(0, 206, 201, 0.1) 100%); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(0, 212, 170, 0.3); border-radius: 20px; padding: 25px 40px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 8px 32px rgba(0, 212, 170, 0.15);">
<div>
<h1 style="margin: 0; font-size: 28px; font-weight: 800; background: linear-gradient(145deg, #ffffff, #00D4AA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">🏢 Navbatchilik Tizimi</h1>
<p style="margin: 5px 0 0 0; color: #888; font-size: 14px;">TTJ Yotoqxona Boshqaruv Paneli</p>
</div>
<div style="display: flex; gap: 15px; align-items: center;">
<div style="background: linear-gradient(145deg, #00D4AA, #00B894); padding: 12px 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0, 212, 170, 0.4);">
<span style="color: #0a0a0a; font-weight: 700; font-size: 16px;">📍 {floor_name}</span>
</div>
<a href="?action=logout" target="_self" style="text-decoration: none;">
<div style="background: rgba(255, 87, 51, 0.15); border: 1px solid rgba(255, 87, 51, 0.4); color: #ff5733; padding: 12px 25px; border-radius: 12px; font-weight: 700; font-size: 16px; transition: all 0.3s ease; display: flex; align-items: center; gap: 8px; cursor: pointer;">
<span>🚪</span>
<span>CHIQISH</span>
</div>
</a>
</div>
</div>
""", unsafe_allow_html=True)


# ============================================================================
# 3D KARTALAR BILAN MENYU
# ============================================================================

# Menyu kartalar uchun CSS
st.markdown("""
<style>
    /* ===== 3D MENYU KARTALARI ===== */
    .menu-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        margin: 30px 0;
        perspective: 1000px;
    }
    
    @media (max-width: 768px) {
        .menu-container {
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
    }
    
    .menu-card {
        background: linear-gradient(145deg, rgba(17, 17, 17, 0.9), rgba(30, 30, 30, 0.8));
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(0, 212, 170, 0.2);
        border-radius: 20px;
        padding: 30px 20px;
        text-align: center;
        cursor: pointer;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        transform-style: preserve-3d;
        box-shadow: 
            0 10px 30px rgba(0, 0, 0, 0.3),
            0 5px 15px rgba(0, 212, 170, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .menu-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(0, 212, 170, 0.2),
            transparent
        );
        transition: left 0.5s;
    }
    
    .menu-card:hover::before {
        left: 100%;
    }
    
    .menu-card:hover {
        transform: translateY(-15px) rotateX(10deg) scale(1.02);
        border-color: rgba(0, 212, 170, 0.6);
        box-shadow: 
            0 25px 50px rgba(0, 0, 0, 0.4),
            0 15px 30px rgba(0, 212, 170, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
    }
    
    .menu-card.active {
        background: linear-gradient(145deg, rgba(0, 212, 170, 0.2), rgba(0, 206, 201, 0.15));
        border-color: rgba(0, 212, 170, 0.8);
        transform: translateY(-8px);
        box-shadow: 
            0 20px 40px rgba(0, 212, 170, 0.25),
            0 10px 20px rgba(0, 0, 0, 0.3),
            inset 0 0 30px rgba(0, 212, 170, 0.1);
    }
    
    .menu-icon {
        font-size: 48px;
        margin-bottom: 15px;
        display: block;
        transform: translateZ(30px);
        transition: transform 0.3s ease;
    }
    
    .menu-card:hover .menu-icon {
        transform: translateZ(50px) scale(1.2);
    }
    
    .menu-title {
        color: #ffffff;
        font-size: 18px;
        font-weight: 700;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .menu-card.active .menu-title {
        background: linear-gradient(145deg, #00D4AA, #00CEC9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .menu-desc {
        color: #888;
        font-size: 12px;
        margin-top: 8px;
    }
    
    .menu-badge {
        position: absolute;
        top: 10px;
        right: 10px;
        background: linear-gradient(145deg, #00D4AA, #00B894);
        color: #0a0a0a;
        font-size: 11px;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        box-shadow: 0 3px 10px rgba(0, 212, 170, 0.4);
    }
    
    /* Glow Effect for Active Card */
    .menu-card.active::after {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(
            circle at center,
            rgba(0, 212, 170, 0.1) 0%,
            transparent 50%
        );
        animation: glow-pulse 3s infinite;
        pointer-events: none;
    }
    
    @keyframes glow-pulse {
        0%, 100% { opacity: 0.5; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.1); }
    }
    
    /* Section Divider */
    .section-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(0, 212, 170, 0.5), transparent);
        margin: 30px 0;
        border-radius: 2px;
    }
</style>
""", unsafe_allow_html=True)

# Session state'da active menyu
if "active_menu" not in st.session_state:
    st.session_state.active_menu = "navbatchilik"

# Query param orqali menyuni aniqlash
if "menu" in st.query_params:
    st.session_state.active_menu = st.query_params["menu"]

# --- 3D MENU CARDS ---
auth_ok = st.query_params.get("auth", "")
floor_id = st.query_params.get("floor", "")
role_type = st.query_params.get("role", "")
base_params = f"auth={auth_ok}&floor={floor_id}&role={role_type}"

st.markdown(f"""
<div class="menu-container">
    <a href="?menu=navbatchilik&{base_params}" target="_self" style="text-decoration: none;">
        <div class="menu-card {'active' if st.session_state.active_menu == 'navbatchilik' else ''}">
            <span class="menu-icon">📝</span>
            <div class="menu-title">Navbatchilik</div>
        </div>
    </a>
    <a href="?menu=naryad&{base_params}" target="_self" style="text-decoration: none;">
        <div class="menu-card {'active' if st.session_state.active_menu == 'naryad' else ''}">
            <span class="menu-icon">🛠️</span>
            <div class="menu-title">Naryad</div>
        </div>
    </a>
    <a href="?menu=statistika&{base_params}" target="_self" style="text-decoration: none;">
        <div class="menu-card {'active' if st.session_state.active_menu == 'statistika' else ''}">
            <span class="menu-icon">📊</span>
            <div class="menu-title">Statistika</div>
        </div>
    </a>
    <a href="?menu=xabarlar&{base_params}" target="_self" style="text-decoration: none;">
        <div class="menu-card {'active' if st.session_state.active_menu == 'xabarlar' else ''}">
            <span class="menu-icon">📨</span>
            <div class="menu-title">Xabarlar</div>
        </div>
    </a>
</div>
<div class="section-divider"></div>
""", unsafe_allow_html=True)

# --- NAVBATCHILIK SAHIFASI ---
if st.session_state.active_menu == "navbatchilik":
    # --- UI ---
    col1, col2 = st.columns([1, 3])
    with col1:
        selected_date = st.date_input("Sanani tanlang", datetime.now(), key="navbatchilik_date")
        date_str = selected_date.strftime("%Y.%m.%d")
    st.info(f"Tanlangan sana: **{date_str}**")

    # Ism va Xona bo'yicha saralash (o'sish tartibida)
    # Har bir talaba uchun display string va original index mapping
    student_display_to_idx = {}
    for idx, row in df.iterrows():
        display_str = f"{row['ism familiya']} ({row['xona']})"
        student_display_to_idx[display_str] = idx
    
    student_options = sorted(student_display_to_idx.keys())

    with st.form("duty_form"):
        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)
        
        ka_o = c1.multiselect("🍳 Katta Oshxona", options=student_options, max_selections=2, placeholder="Ism yoki xona raqamini yozing")
        ki_o = c2.multiselect("🥪 Kichik Oshxona", options=student_options, max_selections=2, placeholder="Ism yoki xona raqamini yozing")
        ka_d = c3.multiselect("🚿 Katta Dush", options=student_options, max_selections=2, placeholder="Ism yoki xona raqamini yozing")
        ki_d = c4.multiselect("🛁 Kichik Dush", options=student_options, max_selections=1, placeholder="Ism yoki xona raqamini yozing")
        
        submitted = st.form_submit_button("💾 Saqlash va SMS Navbatiga Qo'shish", type="primary")

    if submitted:
        selections = []
        for s in ka_o: selections.append((s, 1))
        for s in ki_o: selections.append((s, 2))
        for s in ka_d: selections.append((s, 3))
        for s in ki_d: selections.append((s, 4))
        
        if not selections:
            st.warning("Hech kim tanlanmadi!")
        else:
            try:
                # 1. Asosiy Jadvalga yozish
                sheet = get_main_sheet()
                headers = sheet.row_values(1)
                if date_str not in headers:
                    sheet.update_cell(1, len(headers) + 1, date_str)
                    headers = sheet.row_values(1)
                
                date_col_idx = headers.index(date_str) + 1
                queue_sheet = get_queue_sheet()
                # Toshkent vaqti (UTC+5)
                timestamp = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
                
                progress_bar = st.progress(0)
                
                for i, (student_str, type_id) in enumerate(selections):
                    # To'g'ri indeksni olish (mapping orqali)
                    idx = student_display_to_idx[student_str]
                    row_idx = idx + 2
                    
                    # Asosiy jadvalga ID yozish
                    sheet.update_cell(row_idx, date_col_idx, type_id)
                    
                    # SMS Navbatiga yozish (validatsiya bilan)
                    phone = df.at[idx, 'telefon raqami']
                    student_name = df.at[idx, 'ism familiya']
                    msg = SMS_TEMPLATES[type_id]
                    add_to_sms_queue(queue_sheet, phone, msg, student_name)
                    
                    # Telegramga xabar yuborish (agar telegram_id bo'lsa)
                    if 'telegram_id' in df.columns:
                        tg_id = df.at[idx, 'telegram_id']
                        send_telegram_alert(f"🔍 DEBUG: {student_name} - tg_id = '{tg_id}'")
                        tg_msg = f"📋 <b>Navbatchilik</b>\n\n{msg}\n\n📅 Sana: {date_str}"
                        send_telegram_to_student(tg_id, tg_msg, student_name)
                    else:
                        send_telegram_alert(f"⚠️ telegram_id ustuni topilmadi! Ustunlar: {list(df.columns)}")
                    
                
                # ADMINGA XABAR YUBORISH
                send_telegram_alert("🚨 DIQQAT: Yangi navbatchilar belgilandi!\n\n📲 Iltimos, telefoningizdagi 'SMS Widget' tugmasini bosing.")
                
                # TTJ GURUHIGA XABAR YUBORISH
                group_msg = f"📅 <b>Bugungi Navbatchilar ({date_str})</b>\n\n"
                
                if ka_o:
                    group_msg += "🍳 <b>Katta Oshxona:</b>\n"
                    for s in ka_o:
                        group_msg += f"  • {s}\n"
                    group_msg += "\n"
                
                if ki_o:
                    group_msg += "🥪 <b>Kichik Oshxona:</b>\n"
                    for s in ki_o:
                        group_msg += f"  • {s}\n"
                    group_msg += "\n"
                
                if ka_d:
                    group_msg += "🚿 <b>Katta Dush:</b>\n"
                    for s in ka_d:
                        group_msg += f"  • {s}\n"
                    group_msg += "\n"
                
                if ki_d:
                    group_msg += "🛁 <b>Kichik Dush:</b>\n"
                    for s in ki_d:
                        group_msg += f"  • {s}\n"
                    group_msg += "\n"
                
                group_msg += "✅ <i>Ishingizga omad!</i>"
                send_to_ttj_group(group_msg)

                st.success("✅ Muvaffaqiyatli saqlandi! SMSlar navbatga qo'shildi. Telefoningiz internetga ulanganda ular avtomatik ketadi.")
                st.cache_data.clear()
                st.rerun()
                
            except Exception as e:
                st.error(f"Xatolik: {e}")

    st.markdown("---")
    st.subheader("📋 Asosiy Jadval")
    st.dataframe(df, use_container_width=True)

    st.subheader(f"📨 SMS Navbati Statusi ({floor_name})")
    try:
        qs = get_queue_sheet()
        # Ustun nomlarini belgilash (endi ETAJ yo'q)
        expected_headers = ["TELEFON", "XABAR", "STATUS", "VAQT", "ISM"]
        
        # get_all_records o'rniga get_all_values ishlatamiz
        all_q_values = qs.get_all_values()
        
        q_data = []
        if len(all_q_values) > 1:
            # Headerlarni tekshirish (agar birinchi qator header bo'lmasa)
            current_headers = all_q_values[0]
            # Agar headerlar kutilganidek bo'lsa, 1-qatordan boshlab ma'lumotni olamiz
            # Aks holda, hammasini ma'lumot deb olamiz (lekin bu xavfli)
            
            # Oddiy yondashuv: Har doim 1-qator header deb faraz qilamiz
            # Va har bir qatorni expected_headers'ga map qilamiz
            for row in all_q_values[1:]:
                # Qator uzunligi headerlar soniga to'g'ri kelmasa, to'ldiramiz yoki qirqamiz
                if len(row) < len(expected_headers):
                    row += [""] * (len(expected_headers) - len(row))
                item = dict(zip(expected_headers, row[:len(expected_headers)]))
                q_data.append(item)
        
        if q_data and len(q_data) > 0:
            queue_df = pd.DataFrame(q_data)
            
            if len(queue_df) > 0:
                # Tarixni teskarisiga aylantiramiz (eng yangisi tepada)
                queue_df = queue_df[::-1]
                st.dataframe(queue_df, use_container_width=True, height=300)
                st.caption(f"📊 Jami: {len(queue_df)} ta xabar")
            else:
                st.info(f"📭 {floor_name} uchun SMS navbati bo'sh")
        else:
            st.info("📭 SMS navbati bo'sh - hali xabar yuborilmagan")
    except Exception as e:
        st.warning(f"⚠️ SMS navbatini yuklashda xatolik: {e}")

# --- NARYAD SAHIFASI ---
if st.session_state.active_menu == "naryad":
    st.subheader("🛠️ Naryad Taqsimoti")
    
    # --- UI ---
    col1, col2 = st.columns([1, 3])
    with col1:
        naryad_date = st.date_input("Sanani tanlang", datetime.now(), key="naryad_date")
        naryad_date_str = naryad_date.strftime("%Y.%m.%d")
    st.info(f"Tanlangan sana: **{naryad_date_str}**")

    # Ism va Xona bo'yicha saralash (mapping bilan)
    naryad_display_to_idx = {}
    for idx, row in df.iterrows():
        display_str = f"{row['ism familiya']} ({row['xona']})"
        naryad_display_to_idx[display_str] = idx
    
    naryad_student_options = sorted(naryad_display_to_idx.keys())

    with st.form("naryad_form"):
        # Kun kiritish
        st.markdown("##### 📅 Naryad muddati")
        naryad_kunlar = st.number_input("Necha kunga naryad?", min_value=1, max_value=30, value=1, step=1)
        
        st.markdown("##### 🏠 Boshqa Joylar")
        nc1, nc2 = st.columns(2)
        nc3, nc4 = st.columns(2)
        nc5, nc6 = st.columns(2)
        
        qosh_zal = nc1.multiselect("🏠 Qo'shimcha Zal", options=naryad_student_options, placeholder="Ism yoki xona raqamini yozing")
        zina = nc2.multiselect("🪜 Zina", options=naryad_student_options, placeholder="Ism yoki xona raqamini yozing")
        kirxona = nc3.multiselect("🧹 Kirxona", options=naryad_student_options, placeholder="Ism yoki xona raqamini yozing")
        sabzavotxona = nc4.multiselect("🥕 Sabzavotxona", options=naryad_student_options, placeholder="Ism yoki xona raqamini yozing")
        manaviyat = nc5.multiselect("📚 Manaviyat", options=naryad_student_options, placeholder="Ism yoki xona raqamini yozing")
        kladovka = nc6.multiselect("📦 Kladovka", options=naryad_student_options, placeholder="Ism yoki xona raqamini yozing")
        
        st.markdown("##### 🍳 Oshxona va Dush")
        oc1, oc2 = st.columns(2)
        oc3, oc4 = st.columns(2)
        
        n_ka_oshxona = oc1.multiselect("🍳 Katta Oshxona", options=naryad_student_options, placeholder="Ism yoki xona raqamini yozing", key="n_ka_o")
        n_ki_oshxona = oc2.multiselect("🥪 Kichik Oshxona", options=naryad_student_options, placeholder="Ism yoki xona raqamini yozing", key="n_ki_o")
        n_ka_dush = oc3.multiselect("🚿 Katta Dush", options=naryad_student_options, placeholder="Ism yoki xona raqamini yozing", key="n_ka_d")
        n_ki_dush = oc4.multiselect("🛁 Kichik Dush", options=naryad_student_options, placeholder="Ism yoki xona raqamini yozing", key="n_ki_d")
        
        naryad_submitted = st.form_submit_button("💾 Saqlash va SMS Navbatiga Qo'shish", type="primary")

    if naryad_submitted:
        naryad_selections = []
        for s in qosh_zal: naryad_selections.append((s, 11))
        for s in zina: naryad_selections.append((s, 12))
        for s in kirxona: naryad_selections.append((s, 13))
        for s in sabzavotxona: naryad_selections.append((s, 14))
        for s in manaviyat: naryad_selections.append((s, 15))
        for s in kladovka: naryad_selections.append((s, 16))
        for s in n_ka_oshxona: naryad_selections.append((s, 21))
        for s in n_ki_oshxona: naryad_selections.append((s, 22))
        for s in n_ka_dush: naryad_selections.append((s, 23))
        for s in n_ki_dush: naryad_selections.append((s, 24))
        
        if not naryad_selections:
            st.warning("Hech kim tanlanmadi!")
        else:
            try:
                # 1. Asosiy Jadvalga yozish
                sheet = get_main_sheet()
                headers = sheet.row_values(1)
                if naryad_date_str not in headers:
                    sheet.update_cell(1, len(headers) + 1, naryad_date_str)
                    headers = sheet.row_values(1)
                
                date_col_idx = headers.index(naryad_date_str) + 1
                queue_sheet = get_queue_sheet()
                # Toshkent vaqti (UTC+5)
                timestamp = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
                
                progress_bar = st.progress(0)
                
                for i, (student_str, type_id) in enumerate(naryad_selections):
                    # To'g'ri indeksni olish (mapping orqali)
                    idx = naryad_display_to_idx[student_str]
                    row_idx = idx + 2
                    
                    # Asosiy jadvalga ID yozish
                    sheet.update_cell(row_idx, date_col_idx, type_id)
                    
                    # SMS Navbatiga yozish (kun bilan)
                    phone = df.at[idx, 'telefon raqami']
                    student_name = df.at[idx, 'ism familiya']
                    joy_nomi = NARYAD_NAMES[type_id]
                    msg = f"Siz {naryad_kunlar} kunga {joy_nomi}ga naryadchisiz. Ishingizga omad!"
                    add_to_sms_queue(queue_sheet, phone, msg, student_name)
                    
                    # Telegramga xabar yuborish (agar telegram_id bo'lsa)
                    if 'telegram_id' in df.columns:
                        tg_id = df.at[idx, 'telegram_id']
                        tg_msg = f"🛠 <b>Naryad</b>\n\n{msg}\n\n📅 Sana: {naryad_date_str}"
                        send_telegram_to_student(tg_id, tg_msg, student_name)
                    
                    progress_bar.progress((i + 1) / len(naryad_selections))
                
                # ADMINGA XABAR YUBORISH
                send_telegram_alert("🚨 DIQQAT: Yangi naryadchilar belgilandi!\n\n📲 Iltimos, telefoningizdagi 'SMS Widget' tugmasini bosing.")
                
                # TTJ GURUHIGA XABAR YUBORISH
                naryad_group_msg = f"🛠 <b>Naryad ({naryad_date_str}) - {naryad_kunlar} kunga</b>\n\n"
                
                naryad_items = [
                    ("🏠", "Qo'shimcha Zal", qosh_zal),
                    ("🪜", "Zina", zina),
                    ("🧹", "Kirxona", kirxona),
                    ("🥕", "Sabzavotxona", sabzavotxona),
                    ("📚", "Manaviyat", manaviyat),
                    ("📦", "Kladovka", kladovka),
                    ("🍳", "Katta Oshxona", n_ka_oshxona),
                    ("🥪", "Kichik Oshxona", n_ki_oshxona),
                    ("🚿", "Katta Dush", n_ka_dush),
                    ("🛁", "Kichik Dush", n_ki_dush),
                ]
                
                for emoji, name, students in naryad_items:
                    if students:
                        naryad_group_msg += f"{emoji} <b>{name}:</b>\n"
                        for s in students:
                            naryad_group_msg += f"  • {s}\n"
                        naryad_group_msg += "\n"
                
                naryad_group_msg += "✅ <i>Ishingizga omad!</i>"
                send_to_ttj_group(naryad_group_msg)

                st.success("✅ Muvaffaqiyatli saqlandi! SMSlar navbatga qo'shildi. Telefoningiz internetga ulanganda ular avtomatik ketadi.")
                st.cache_data.clear()
                st.rerun()
                
            except Exception as e:
                st.error(f"Xatolik: {e}")

    st.markdown("---")
    st.subheader("📋 Asosiy Jadval")
    st.dataframe(df, use_container_width=True)
    
    # Naryad statistikasi
    st.subheader("🏆 Naryad Statistikasi")
    date_cols = [c for c in df.columns if len(str(c)) == 10 and c[4] == '.' and c[7] == '.']
    
    if date_cols:
        naryad_stats = df[['ism familiya', 'xona']].copy()
        # Naryad IDlari: 11-17 va 21-24
        def count_naryad(row):
            count = 0
            for col in date_cols:
                val = str(row[col]).strip()
                if val.isdigit():
                    num = int(val)
                    if (num >= 11 and num <= 17) or (num >= 21 and num <= 24):
                        count += 1
            return count
        
        naryad_stats['Jami Naryad'] = df.apply(count_naryad, axis=1)
        naryad_stats = naryad_stats.sort_values(by="Jami Naryad", ascending=False).reset_index(drop=True)
        st.dataframe(naryad_stats, use_container_width=True)
    else:
        st.warning("Hozircha hech qanday ma'lumot yo'q.")

# --- STATISTIKA SAHIFASI ---
if st.session_state.active_menu == "statistika":
    st.subheader("🏆 Navbatchilik Statistikasi")
    
    # Faqat sana ustunlarini ajratib olish (regex yordamida YYYY.MM.DD)
    date_cols = [c for c in df.columns if len(str(c)) == 10 and c[4] == '.' and c[7] == '.']
    
    if not date_cols:
        st.warning("Hozircha hech qanday ma'lumot yo'q.")
    else:
        # Har bir talaba uchun navbatchiliklarni sanash (faqat 1-4 IDlar)
        stats = df[['ism familiya', 'xona']].copy()
        
        def count_navbatchilik(row):
            count = 0
            for col in date_cols:
                val = str(row[col]).strip()
                if val.isdigit() and int(val) >= 1 and int(val) <= 4:
                    count += 1
            return count
        
        def count_naryad_stat(row):
            count = 0
            for col in date_cols:
                val = str(row[col]).strip()
                if val.isdigit():
                    num = int(val)
                    if (num >= 11 and num <= 17) or (num >= 21 and num <= 24):
                        count += 1
            return count
        
        stats['Navbatchilik'] = df.apply(count_navbatchilik, axis=1)
        stats['Naryad'] = df.apply(count_naryad_stat, axis=1)
        stats['Jami'] = stats['Navbatchilik'] + stats['Naryad']
        
        # Saralash (Eng ko'p navbatchi bo'lganlar tepada)
        stats = stats.sort_values(by="Jami", ascending=False).reset_index(drop=True)
        
        st.dataframe(stats, use_container_width=True)
        
        # ============================================================================
        # 📊 CHIROYLI GRAFIKLAR
        # ============================================================================
        st.markdown("---")
        st.subheader("📈 Grafiklar")
        
        # Top 10 talaba - Bar Chart
        top_10 = stats.head(10)
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("##### 🏆 Top 10 Faol Talabalar")
            fig_bar = go.Figure()
            
            fig_bar.add_trace(go.Bar(
                name='Navbatchilik',
                x=top_10['ism familiya'],
                y=top_10['Navbatchilik'],
                marker_color='#00D4AA',
                text=top_10['Navbatchilik'],
                textposition='auto'
            ))
            
            fig_bar.add_trace(go.Bar(
                name='Naryad',
                x=top_10['ism familiya'],
                y=top_10['Naryad'],
                marker_color='#FF6B6B',
                text=top_10['Naryad'],
                textposition='auto'
            ))
            
            fig_bar.update_layout(
                barmode='stack',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                xaxis=dict(
                    tickangle=-45,
                    gridcolor='rgba(255,255,255,0.1)'
                ),
                yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=20, r=20, t=40, b=100),
                height=400
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col_chart2:
            st.markdown("##### 🥧 Navbatchilik vs Naryad")
            
            total_navbat = stats['Navbatchilik'].sum()
            total_naryad = stats['Naryad'].sum()
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Navbatchilik', 'Naryad'],
                values=[total_navbat, total_naryad],
                hole=0.5,
                marker=dict(colors=['#00D4AA', '#FF6B6B']),
                textinfo='label+percent',
                textfont=dict(size=14, color='white'),
                hovertemplate='%{label}: %{value}<extra></extra>'
            )])
            
            fig_pie.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.1,
                    xanchor="center",
                    x=0.5
                ),
                margin=dict(l=20, r=20, t=40, b=60),
                height=400,
                annotations=[dict(
                    text=f'Jami<br>{total_navbat + total_naryad}',
                    x=0.5, y=0.5,
                    font_size=18,
                    font_color='#00D4AA',
                    showarrow=False
                )]
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Umumiy statistika kartalar
        st.markdown("---")
        st.markdown("##### 📊 Umumiy Ko'rsatkichlar")
        
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric(
                label="👥 Jami Talabalar",
                value=len(stats),
                delta=None
            )
        
        with metric_col2:
            st.metric(
                label="📝 Navbatchiliklar",
                value=total_navbat,
                delta=None
            )
        
        with metric_col3:
            st.metric(
                label="🛠️ Naryadlar",
                value=total_naryad,
                delta=None
            )
        
        with metric_col4:
            avg_per_student = round((total_navbat + total_naryad) / len(stats), 1) if len(stats) > 0 else 0
            st.metric(
                label="📈 O'rtacha (1 talaba)",
                value=avg_per_student,
                delta=None
            )
    
    # ============================================================================
    # XONALAR BO'YICHA STATISTIKA
    # ============================================================================
    st.markdown("---")
    st.subheader("🏠 Xonalar Bo'yicha Statistika")
    
    if date_cols:
        # Xonalarni guruhlash
        xona_stats = df.groupby('xona').apply(
            lambda x: pd.Series({
                'Talabalar soni': len(x),
                'Navbatchilik': x.apply(count_navbatchilik, axis=1).sum(),
                'Naryad': x.apply(count_naryad_stat, axis=1).sum()
            })
        ).reset_index()
        xona_stats['Jami'] = xona_stats['Navbatchilik'] + xona_stats['Naryad']
        xona_stats = xona_stats.sort_values(by='Jami', ascending=False).reset_index(drop=True)
        
        st.dataframe(xona_stats, use_container_width=True)
    
    # ============================================================================
    # TALABANI QIDIRISH
    # ============================================================================
    st.markdown("---")
    st.subheader("🔍 Talabani Qidirish")
    
    # Ismdan indexga mapping (Saralashda adashmaslik uchun)
    search_display_to_idx = {f"{row['ism familiya']} ({row['xona']})": idx for idx, row in df.iterrows()}
    search_student_options = sorted(search_display_to_idx.keys())
    
    # Session state
    if "show_student_details" not in st.session_state:
        st.session_state.show_student_details = False
        st.session_state.selected_student_name = None
    
    # Qidirish formasi - form ichida sahifa yangilanmaydi
    with st.form("search_form"):
        selected_search = st.selectbox(
            "Talabani tanlang yoki qidiring",
            options=search_student_options,
            index=None,
            placeholder="Ism yoki xona raqamini yozing...",
            key="search_student_stats"
        )
        
        search_submitted = st.form_submit_button("🔍 Qidirish", type="primary", use_container_width=True)
        
        if search_submitted and selected_search:
            st.session_state.show_student_details = True
            st.session_state.selected_student_name = selected_search
    
    # Agar qidirilgan bo'lsa, natijani ko'rsatish
    if st.session_state.show_student_details and st.session_state.selected_student_name and date_cols:
        selected_search = st.session_state.selected_student_name
        
        # Tanlangan talabani topish (TO'G'RI INDEX BILAN)
        search_idx = search_display_to_idx[selected_search]
        student_row = df.loc[search_idx]
        student_name = student_row['ism familiya']
        student_xona = student_row['xona']
        
        st.markdown("---")
        st.markdown(f"### 👤 {student_name}")
        st.info(f"🏠 Xona: {student_xona}")
        
        # Joy nomlari
        joy_nomlari = {
            1: "🍳 Katta Oshxona",
            2: "🥪 Kichik Oshxona", 
            3: "🚿 Katta Dush",
            4: "🛁 Kichik Dush",
            11: "🏠 Qo'shimcha Zal",
            12: "🪜 Zina",
            13: "🧹 Kirxona",
            14: "🥕 Sabzavotxona",
            15: "📚 Manaviyat",
            16: "📦 Kladovka",
            21: "🍳 K.Oshxona (Naryad)",
            22: "🥪 Ki.Oshxona (Naryad)",
            23: "🚿 K.Dush (Naryad)",
            24: "🛁 Ki.Dush (Naryad)"
        }
        
        # Statistikani hisoblash - sanalar bilan
        navbatchilik_count = 0
        naryad_count = 0
        joy_statistika = {}  # {joy_nomi: [sana1, sana2, ...]}
        
        for col in date_cols:
            val = str(student_row[col]).strip()
            if val.isdigit():
                num = int(val)
                joy_nomi = joy_nomlari.get(num, f"Noma'lum ({num})")
                
                if num >= 1 and num <= 4:
                    navbatchilik_count += 1
                elif (num >= 11 and num <= 17) or (num >= 21 and num <= 24):
                    naryad_count += 1
                
                # Sanani qo'shish
                if joy_nomi not in joy_statistika:
                    joy_statistika[joy_nomi] = []
                joy_statistika[joy_nomi].append(col)
        
        # Umumiy statistika
        col1, col2, col3 = st.columns(3)
        col1.metric("📝 Navbatchilik", navbatchilik_count)
        col2.metric("🛠️ Naryad", naryad_count)
        col3.metric("📊 Jami", navbatchilik_count + naryad_count)
        
        # Joy bo'yicha batafsil taqsimot
        if joy_statistika:
            st.markdown("#### 📍 Batafsil Ma'lumot:")
            
            # Saralash (eng ko'p birinchi)
            sorted_joy = sorted(joy_statistika.items(), key=lambda x: len(x[1]), reverse=True)
            
            for joy, sanalar in sorted_joy:
                soni = len(sanalar)
                sanalar_str = ", ".join(sanalar)
                
                # Expander ichida ko'rsatish
                with st.expander(f"{joy} - **{soni} marta**", expanded=False):
                    st.markdown(f"**📅 Sanalar:** {sanalar_str}")
                    
                    # Jadval ko'rinishida
                    if soni > 0:
                        for i, sana in enumerate(sanalar, 1):
                            st.write(f"  {i}. {sana}")
        else:
            st.info("Bu talaba hali hech qayerga tayinlanmagan")
        
        # Yopish tugmasi
        if st.button("❌ Yopish", key="close_student_details"):
            st.session_state.show_student_details = False
            st.session_state.selected_student_name = None
            st.rerun()


# ============================================================================
# XABARLAR BO'LIMI - SMS Yuborish
# ============================================================================
# --- XABARLAR SAHIFASI ---
if st.session_state.active_menu == "xabarlar":
    st.subheader("📨 Xabarlar - Tanlangan Talabalarga SMS Yuborish")
    st.info("📌 Xabar yozing va qaysi talabalarga yuborishni tanlang. SMS navbatga qo'shiladi.")
    
    # Talabalar ro'yxati (mapping bilan)
    xabar_display_to_idx = {}
    for idx, row in df.iterrows():
        display_str = f"{row['ism familiya']} ({row['xona']})"
        xabar_display_to_idx[display_str] = idx
    
    xabar_student_options = sorted(xabar_display_to_idx.keys())
    
    with st.form("xabar_form"):
        # Xabar matni
        st.markdown("##### ✍️ Xabar Matni")
        xabar_matni = st.text_area(
            "Xabarni kiriting",
            placeholder="Masalan: Hamma xonasiga qarasin! Bugun tekshiruv bo'ladi.",
            height=100,
            help="Bu xabar tanlangan barcha talabalarga SMS orqali yuboriladi"
        )
        
        st.markdown("---")
        
        # Tez tanlash
        st.markdown("##### 👥 Qabul qiluvchilar")
        
        tez_tanlash = st.radio(
            "Tanlash usuli",
            ["🎯 Alohida tanlash", "👥 Hammaga yuborish"],
            horizontal=True
        )
        
        if tez_tanlash == "🎯 Alohida tanlash":
            # Alohida talabalar tanlash
            tanlangan_talabalar = st.multiselect(
                "Talabalarni tanlang",
                options=xabar_student_options,
                placeholder="Ism yoki xona raqamini yozing...",
                help="Bir nechta talaba tanlashingiz mumkin"
            )
        else:
            tanlangan_talabalar = xabar_student_options  # Hammasi
            st.success(f"✅ Barcha {len(xabar_student_options)} ta talaba tanlandi")
        
        xabar_submitted = st.form_submit_button("📤 Xabarni Yuborish", type="primary")
    
    if xabar_submitted:
        if not xabar_matni.strip():
            st.warning("⚠️ Xabar matnini kiriting!")
        elif not tanlangan_talabalar:
            st.warning("⚠️ Kamida bitta talaba tanlang!")
        else:
            try:
                queue_sheet = get_queue_sheet()
                timestamp = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
                
                progress_bar = st.progress(0)
                yuborilgan = 0
                
                for i, student_str in enumerate(tanlangan_talabalar):
                    # To'g'ri indeksni olish (mapping orqali)
                    idx = xabar_display_to_idx[student_str]
                    phone = df.at[idx, 'telefon raqami']
                    student_name = df.at[idx, 'ism familiya']
                    
                    # SMS navbatga qo'shish (validatsiya bilan)
                    if add_to_sms_queue(queue_sheet, phone, xabar_matni.strip(), student_name):
                        yuborilgan += 1
                    
                    # Telegramga yuborish (agar telegram_id bo'lsa)
                    if 'telegram_id' in df.columns:
                        tg_id = df.at[idx, 'telegram_id']
                        tg_msg = f"📨 <b>Xabar</b>\n\n{xabar_matni.strip()}"
                        send_telegram_to_student(tg_id, tg_msg, student_name)
                    
                    progress_bar.progress((i + 1) / len(tanlangan_talabalar))
                
                # Admin xabari
                send_telegram_alert(f"📨 YANGI XABAR YUBORILDI!\n\n👥 {yuborilgan} ta talabaga\n📝 Xabar: {xabar_matni[:50]}...\n\n📲 SMS Widget tugmasini bosing!")
                
                # Guruhga xabar (talabalar ro'yxati bilan)
                group_msg = f"📨 <b>YANGI XABAR YUBORILDI</b>\n\n"
                group_msg += f"� <b>Xabar:</b> {xabar_matni.strip()}\n\n"
                group_msg += f"�👥 <b>Qabul qiluvchilar ({yuborilgan} ta):</b>\n"
                for student_str in tanlangan_talabalar[:15]:  # Max 15 ta ko'rsatish
                    group_msg += f"  • {student_str}\n"
                if len(tanlangan_talabalar) > 15:
                    group_msg += f"  ... va yana {len(tanlangan_talabalar) - 15} ta"
                send_to_ttj_group(group_msg)
                
                st.success(f"✅ Xabar {yuborilgan} ta talabaga navbatga qo'shildi!")
                st.info("📱 Telefoningiz internetga ulanganda SMSlar avtomatik yuboriladi.")
                
                log_activity("Xabar yuborildi", f"{yuborilgan} ta talabaga: {xabar_matni[:30]}...")
                
            except Exception as e:
                st.error(f"Xatolik: {e}")
    
    # Qo'shimcha: Tayyor shablonlar bilan tugmalar
    st.markdown("---")
    st.markdown("##### 📋 Tez Yuborish Shablonlari")
    st.info("👆 Tugmani bosing, talabalarni tanlang va xabar avtomatik yuboriladi!")
    
    # Shablonlar ro'yxati
    shablonlar = [
        ("🏠", "Xonangizga qarang, tekshiruv bo'ladi!"),
        ("🚿", "Dush soat 22:00 da yopiladi"),
        ("📚", "Ertaga dars bo'lmaydi"),
        ("⚠️", "Zudlik bilan yig'ilishga keling!"),
        ("🔔", "Komendant chaqirmoqda"),
        ("📞", "Telefon raqamingizni yangilang"),
    ]
    
    # Session state uchun
    if "shablon_xabar" not in st.session_state:
        st.session_state.shablon_xabar = None
    
    # Tugmalar qatori
    shablon_cols = st.columns(3)
    
    for i, (emoji, matn) in enumerate(shablonlar):
        col_idx = i % 3
        with shablon_cols[col_idx]:
            if st.button(f"{emoji} {matn[:20]}...", key=f"shablon_{i}", use_container_width=True):
                st.session_state.shablon_xabar = matn
    
    # Agar shablon tanlangan bo'lsa
    if st.session_state.shablon_xabar:
        st.markdown("---")
        st.success(f"📝 Tanlangan xabar: **{st.session_state.shablon_xabar}**")
        
        shablon_display_to_idx = {}
        for idx, row in df.iterrows():
            display_str = f"{row['ism familiya']} ({row['xona']})"
            shablon_display_to_idx[display_str] = idx
        
        shablon_talabalar_options = sorted(shablon_display_to_idx.keys())
        
        shablon_tanlash = st.radio(
            "Kimga yuborish?",
            ["🎯 Alohida tanlash", "👥 Hammaga"],
            horizontal=True,
            key="shablon_qabul"
        )
        
        if shablon_tanlash == "🎯 Alohida tanlash":
            shablon_talabalar = st.multiselect(
                "Talabalarni tanlang",
                options=shablon_talabalar_options,
                placeholder="Ism yoki xona raqamini yozing...",
                key="shablon_talabalar_select"
            )
        else:
            shablon_talabalar = shablon_talabalar_options
            st.info(f"✅ Barcha {len(shablon_talabalar_options)} ta talaba tanlandi")
        
        col_send, col_cancel = st.columns(2)
        
        with col_send:
            if st.button("📤 Yuborish", type="primary", use_container_width=True, key="shablon_send"):
                if shablon_talabalar:
                    try:
                        queue_sheet = get_queue_sheet()
                        timestamp = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
                        
                        sent_count = 0
                        for student_str in shablon_talabalar:
                            # To'g'ri indeksni olish (mapping orqali)
                            idx = shablon_display_to_idx[student_str]
                            phone = df.at[idx, 'telefon raqami']
                            student_name = df.at[idx, 'ism familiya']
                            if add_to_sms_queue(queue_sheet, phone, st.session_state.shablon_xabar, student_name):
                                sent_count += 1
                            
                            # Telegramga yuborish (agar telegram_id bo'lsa)
                            if 'telegram_id' in df.columns:
                                tg_id = df.at[idx, 'telegram_id']
                                tg_msg = f"📨 <b>Xabar</b>\n\n{st.session_state.shablon_xabar}"
                                send_telegram_to_student(tg_id, tg_msg, student_name)
                        
                        send_telegram_alert(f"📨 TEZ XABAR!\n\n👥 {len(shablon_talabalar)} ta talabaga\n📝 {st.session_state.shablon_xabar}\n\n📲 SMS Widget!")
                        
                        # Guruhga xabar
                        group_msg = f"📨 <b>TEZ XABAR YUBORILDI</b>\n\n"
                        group_msg += f"📝 <b>Xabar:</b> {st.session_state.shablon_xabar}\n\n"
                        group_msg += f"👥 <b>Qabul qiluvchilar ({sent_count} ta):</b>\n"
                        for student_str in shablon_talabalar[:15]:
                            group_msg += f"  • {student_str}\n"
                        if len(shablon_talabalar) > 15:
                            group_msg += f"  ... va yana {len(shablon_talabalar) - 15} ta"
                        send_to_ttj_group(group_msg)
                        
                        st.success(f"✅ {len(shablon_talabalar)} ta talabaga yuborildi!")
                        log_activity("Tez xabar", f"{len(shablon_talabalar)} talabaga: {st.session_state.shablon_xabar[:30]}...")
                        st.session_state.shablon_xabar = None
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Xatolik: {e}")
                else:
                    st.warning("⚠️ Kamida bitta talaba tanlang!")
        
        with col_cancel:
            if st.button("❌ Bekor qilish", use_container_width=True, key="shablon_cancel"):
                st.session_state.shablon_xabar = None
                st.rerun()

