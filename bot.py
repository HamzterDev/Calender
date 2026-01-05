import os
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pytz

# ======================
# CONFIG
# ======================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = "Asia/Bangkok"
BKK = pytz.timezone(TIMEZONE)

# ======================
# GOOGLE CALENDAR SERVICE
# ======================
def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

# ======================
# ADD EVENT FUNCTION
# ======================
def add_event(title: str, start: datetime, end: datetime = None, all_day: bool = False):
    service = get_calendar_service()
    if all_day:
        event = {
            "summary": title,
            "start": {"date": start.date().isoformat()},
            "end": {"date": (start.date() + timedelta(days=1)).isoformat()},
        }
    else:
        if end is None:
            end = start + timedelta(hours=1)
        event = {
            "summary": title,
            "start": {"dateTime": start.isoformat(), "timeZone": TIMEZONE},
            "end": {"dateTime": end.isoformat(), "timeZone": TIMEZONE},
        }
    created_event = service.events().insert(calendarId="primary", body=event).execute()
    return created_event.get("id")

# ======================
# DELETE EVENT FUNCTION
# ======================
def delete_event(event_id):
    service = get_calendar_service()
    service.events().delete(calendarId="primary", eventId=event_id).execute()

# ======================
# LIST EVENTS FUNCTION
# ======================
def get_events(month: int, year: int):
    service = get_calendar_service()
    start_month = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    if month == 12:
        end_month = datetime(year+1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    else:
        end_month = datetime(year, month+1, 1, 0, 0, 0, tzinfo=timezone.utc)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_month.isoformat(),
        timeMax=end_month.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    # sort by start time
    events.sort(key=lambda x: x['start'].get('dateTime') or x['start'].get('date'))
    return events

async def get_events_async(month: int, year: int):
    return await asyncio.to_thread(get_events, month, year)

# ======================
# TELEGRAM COMMANDS
# ======================
HELP_TEXT = (
    "🤖 วิธีใช้ Todo Bot\n\n"
    "คำสั่ง:\n"
    " → เพิ่มงานวันนี้\n"
    "🟢/add งานที่ต้องทำ\n\n"
    " → เพิ่มงานแบบตามวัน\n"
    "🟢/add งานที่ต้องทำ | dd/mm/yyyy\n\n"
    "→ เพิ่มงานพร้อมเวลา\n"
    "🟢/add งานที่ต้องทำ | dd/mm/yyyy HH:MM\n\n"
    "→ ลบงานตามหมายเลข /show\n"
    "🟢/delete <หมายเลข>\n\n"
    "→ แสดงงานทั้งหมด\n"
    "🟢/show MM/YYYY\n\n"
    " → แสดงวิธีใช้\n"
    "🟢/help\n"
    "📌ตัวอย่าง📌\n"
    "🔰/add ทำรายงานวิชา MIS\n"
    "🔰/add ทำรายงานวิชา MIS | 05/01/2026\n"
    "🔰/add ทำรายงานวิชา MIS | 05/01/2026 14:00\n"
    "🔰/show 01/2026\n"
    "🔰/delete 2"
)

# เก็บ list ของ event ของเดือนล่าสุดสำหรับลบตามหมายเลข
LAST_EVENT_LIST = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ ใช้รูปแบบ:\n/add งานที่ต้องทำ | dd/mm/yyyy [HH:MM]")
        return

    text = " ".join(context.args)
    if "|" in text:
        task, datetime_str = map(str.strip, text.split("|", 1))
        try:
            if len(datetime_str.strip()) <= 10:
                start_time = datetime.strptime(datetime_str.strip(), "%d/%m/%Y")
                all_day = True
                end_time = None
            else:
                start_time = datetime.strptime(datetime_str.strip(), "%d/%m/%Y %H:%M")
                end_time = start_time + timedelta(hours=1)
                all_day = False
        except ValueError:
            await update.message.reply_text("❌ รูปแบบวันที่ไม่ถูกต้อง\nใช้ dd/mm/yyyy หรือ dd/mm/yyyy HH:MM")
            return
    else:
        task = text
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        all_day = False

    try:
        add_event(task, start_time, end_time, all_day)
        await update.message.reply_text(
            f"✅ เพิ่มลง Google Calendar แล้ว\n\n"
            f"📝 {task}\n"
            f"⏰ {start_time.strftime('%d/%m/%Y %H:%M') if not all_day else start_time.strftime('%d/%m/%Y')} "
            f"{'(All-day)' if all_day else ''}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ เกิดข้อผิดพลาด\n{e}")
        await update.message.reply_text("อาจเกิดปัญหาจากการเชื่อมต่อ Broser !")
async def show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global LAST_EVENT_LIST
    if not context.args:
        await update.message.reply_text("❌ ใช้ /show MM/YYYY เช่น /show 01/2026")
        return
    try:
        month, year = map(int, context.args[0].split("/"))
        events = await get_events_async(month, year)
        if not events:
            await update.message.reply_text("📭 ไม่พบงานในเดือนนี้")
            LAST_EVENT_LIST = []
            return

        msg = f"📅 งานเดือน {month}/{year}:\n"
        LAST_EVENT_LIST = events
        for idx, e in enumerate(events, 1):
            start_str = e['start'].get('dateTime') or e['start'].get('date')
            if 'T' in start_str:
                dt = datetime.fromisoformat(start_str.replace('Z', '+00:00')).astimezone(BKK)
                start_display = dt.strftime('%d/%m/%Y %H:%M')
            else:
                dt = datetime.fromisoformat(start_str)
                start_display = dt.strftime('%d/%m/%Y')
            msg += f"{idx}. {start_display} - {e['summary']}\n"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ เกิดข้อผิดพลาด\n{e}")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global LAST_EVENT_LIST
    if not context.args:
        await update.message.reply_text("❌ ใช้ /delete <หมายเลข>")
        return
    try:
        num = int(context.args[0])
        if num < 1 or num > len(LAST_EVENT_LIST):
            await update.message.reply_text(f"❌ ไม่พบหมายเลข {num} ในรายการล่าสุด")
            return
        event = LAST_EVENT_LIST[num-1]
        delete_event(event['id'])
        await update.message.reply_text(f"✅ ลบงานเรียบร้อย: {event['summary']}")
        LAST_EVENT_LIST.pop(num-1)
    except ValueError:
        await update.message.reply_text("❌ หมายเลขต้องเป็นตัวเลข")
    except Exception as e:
        await update.message.reply_text(f"❌ เกิดข้อผิดพลาด\n{e}")

# ======================
# MAIN
# ======================
def main():
    if not TOKEN:
        raise RuntimeError("❌ ไม่พบ BOT_TOKEN ในไฟล์ .env")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("show", show))
    app.add_handler(CommandHandler("delete", delete))

    print("🤖 Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()

