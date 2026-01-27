import os
import urllib.request

URL = "https://raw.githubusercontent.com/HamzterDev/Calender/main/bot.py"
FILE = "bot.py"

def update():
    try:
        print("🔄 กำลังอัปเดต...")

        if os.path.exists(FILE):
            os.remove(FILE)

        urllib.request.urlretrieve(URL, FILE)
        print("✅ อัปเดตเสร็จสิ้น")

    except Exception as e:
        print("❌ Error:", e)

update()
