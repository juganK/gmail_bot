import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
import json

# Load Gmail credentials from environment variable
GMAIL_CREDENTIALS = json.loads(os.getenv('GMAIL_CREDENTIALS_JSON'))
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

flow = InstalledAppFlow.from_client_config(GMAIL_CREDENTIALS, SCOPES)
credentials = flow.run_console()

gmail_service = build('gmail', 'v1', credentials=credentials)

# Telegram Bot Setup
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Function to fetch emails
def fetch_emails():
    try:
        results = gmail_service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
        messages = results.get('messages', [])

        summary = ""
        for message in messages:
            msg = gmail_service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
            from_email = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
            snippet = msg.get('snippet', '')

            if 'SPAM' not in msg.get('labelIds', []):
                summary += f"From: {from_email}\nSubject: {subject}\nSnippet: {snippet}\n\n"

        if summary:
            bot.send_message(chat_id=CHAT_ID, text=summary)
        else:
            bot.send_message(chat_id=CHAT_ID, text="No new emails.")

    except Exception as e:
        bot.send_message(chat_id=CHAT_ID, text=f"Error fetching emails: {e}")

# Telegram Command Handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Welcome! I will send you email summaries every hour. Use /check to fetch emails manually.")

def check_emails(update: Update, context: CallbackContext):
    fetch_emails()
    update.message.reply_text("Email check triggered.")

# Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_emails, 'interval', hours=1)
scheduler.start()

# Telegram Bot Updater
updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("check", check_emails))

# Start the bot
updater.start_polling()
updater.idle()

# Shutdown scheduler on exit
scheduler.shutdown()
