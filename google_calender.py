import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "client_secret.json", SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

def add_event(title, start_time, end_time):
    service = get_calendar_service()

    event = {
        "summary": title,
        "start": {
            "dateTime": start_time,
            "timeZone": "Asia/Bangkok",
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "Asia/Bangkok",
        },
    }

    service.events().insert(
        calendarId="primary",
        body=event
    ).execute()
