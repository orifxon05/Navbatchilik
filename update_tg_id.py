import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

SETTINGS_SHEET_NAME = "Navbatchilik_Jadvali"
SETTINGS_WORKSHEET = "SETTINGS"
NEW_TG_ID = "-1002623014807"

try:
    sheet = client.open(SETTINGS_SHEET_NAME).worksheet(SETTINGS_WORKSHEET)
    data = sheet.get_all_records()
    
    for i, row in enumerate(data, start=2):
        if row.get("floor_id") == "3-etaj":
            # telegram_group is usually the 5th column
            sheet.update_cell(i, 5, NEW_TG_ID)
            print(f"Successfully updated 3-etaj Telegram Group ID to {NEW_TG_ID} in Google Sheets.")
            break
except Exception as e:
    print(f"Error updating Google Sheet: {e}")
