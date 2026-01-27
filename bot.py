import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ======================
# CONFIG
# ======================

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_TELEGRAM_BOT")

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = "Asia/Bangkok"
BKK = pytz.timezone(TIMEZONE)

# ======================
# TOKEN FINDER
# ======================

TOKEN_PATHS = [
    "token.json",
    "./config/token.json",
    os.path.expanduser("~/.config/calendar_bot/token.json"),
]

def find_token_file():
    for path in TOKEN_PATHS:
        if os.path.isfile(path):
            return path
    return None

# ======================
# GOOGLE CALENDAR
# ======================

def get_calendar_service():
    token_file = find_token_file()

    if not token_file:
        raise RuntimeError(
            "❌ ไม่พบ token.json\n"
            "โปรดวางไฟล์ไว้ที่:\n" +
            "\n".join(TOKEN_PATHS)
        )

    creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    return build("calendar", "v3", credentials=creds)


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

        start = BKK.localize(start)
        end = BKK.localize(end)

        event = {
            "summary": title,
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": TIMEZONE,
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": TIMEZONE,
            },
        }

    service.events().insert(calendarId="primary", body=event).execute()


def delete_event(event_id: str):
    service = get_calendar_service()
    service.events().delete(calendarId="primary", eventId=event_id).execute()


def get_events(month: int, year: int):
    service = get_calendar_service()

    start_month = datetime(year, month, 1, tzinfo=timezone.utc)
    end_month = (
        datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    )

    events = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_month.isoformat(),
            timeMax=end_month.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
        .get("items", [])
    )

    events.sort(key=lambda e: e["start"].get("dateTime") or e["start"].get("date"))
    return events


async def get_events_async(month: int, year: int):
    return await asyncio.to_thread(get_events, month, year)

# ======================
# TELEGRAM COMMANDS
# ======================

HELP_TEXT = (
    "📅 Calendar Auto-Bot\n\n"
    "🟢 /add งาน\n"
    "🟢 /add งาน | dd/mm/yyyy\n"
    "🟢 /add งาน | dd/mm/yyyy HH:MM\n\n"
    "🟢 /show MM/YYYY\n"
    "🟢 /delete <หมายเลข>\n"
    "🟢 /help"
)

LAST_EVENT_LIST = []


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ ใช้ /add งาน | วันที่ [เวลา]")
        return

    text = " ".join(context.args)

    try:
        if "|" in text:
            task, dt_str = map(str.strip, text.split("|", 1))
            if len(dt_str) <= 10:
                start = datetime.strptime(dt_str, "%d/%m/%Y")
                add_event(task, start, all_day=True)
            else:
                start = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
                add_event(task, start)
        else:
            task = text
            add_event(task, datetime.now())

        await update.message.reply_text(f"✅ เพิ่มงานแล้ว: {task}")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global LAST_EVENT_LIST

    if not context.args:
        await update.message.reply_text("❌ ใช้ /show MM/YYYY")
        return

    month, year = map(int, context.args[0].split("/"))
    events = await get_events_async(month, year)

    if not events:
        await update.message.reply_text("📭 ไม่พบงาน")
        LAST_EVENT_LIST = []
        return

    LAST_EVENT_LIST = events
    msg = f"📅 งานเดือน {month}/{year}\n"

    for i, e in enumerate(events, 1):
        start_str = e["start"].get("dateTime") or e["start"].get("date")
        if "T" in start_str:
            dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")).astimezone(BKK)
            display = dt.strftime("%d/%m/%Y %H:%M")
        else:
            display = datetime.fromisoformat(start_str).strftime("%d/%m/%Y")

        msg += f"{i}. 📌 {display} - {e['summary']}\n"

    await update.message.reply_text(msg)


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global LAST_EVENT_LIST

    if not context.args:
        await update.message.reply_text("❌ ใช้ /delete <หมายเลข>")
        return

    idx = int(context.args[0]) - 1
    if idx < 0 or idx >= len(LAST_EVENT_LIST):
        await update.message.reply_text("❌ ไม่พบหมายเลข")
        return

    event = LAST_EVENT_LIST[idx]
    delete_event(event["id"])
    await update.message.reply_text(f"✅ ลบแล้ว: {event['summary']}")

# ======================
# MAIN
# ======================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("show", show))
    app.add_handler(CommandHandler("delete", delete))

    print("🤖 CalendarAutoBot started")
    app.run_polling()


if __name__ == "__main__":
    main()
