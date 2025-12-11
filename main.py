import os
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from google import genai

# --- Load Keys from Environment Variables ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if TELEGRAM_TOKEN is None or GEMINI_API_KEY is None:
    raise ValueError("⚠ Missing TELEGRAM_TOKEN or GEMINI_API_KEY environment variable!")

# --- File for chat history ---
CHAT_HISTORY_FILE = "chat_history.json"
MAX_MESSAGES = 20  # store last 20 per user

# --- Gemini Client ---
client = genai.Client(api_key=GEMINI_API_KEY)

# --- Load chat history from file ---
if os.path.exists(CHAT_HISTORY_FILE):
    with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
        chat_history = json.load(f)
else:
    chat_history = {}

# Save history function
def save_chat_history():
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(chat_history, f, ensure_ascii=False, indent=2)

# -------------------------------
# Commands
# -------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    if chat_id not in chat_history:
        chat_history[chat_id] = []

    await update.message.reply_text("Hello!  I am your bot. How can I help you today?")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I can remember our conversation.\n"
        "Commands:\n"
        "/start - Start bot\n"
        "/help - Help menu\n"
        "/reset - Clear memory"
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    chat_history[chat_id] = []
    save_chat_history()
    await update.message.reply_text(" Chat history cleared!")

# -------------------------------
# AI Reply
# -------------------------------

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    text = update.message.text.lower()
    user_text = update.message.text

    if chat_id not in chat_history:
        chat_history[chat_id] = []

    # Quick replies
    if any(g in text for g in ["hi", "hello", "hey"]):
        await update.message.reply_text("Hey!  What’s up?")
        return

    if any(g in text for g in ["bye", "goodbye", "see you"]):
        await update.message.reply_text("Goodbye! ")
        return

    if "how are you" in text:
        await update.message.reply_text("I'm doing great! Thanks for asking ")
        return

    # Add user message to history
    chat_history[chat_id].append({"role": "user", "content": user_text})
    chat_history[chat_id] = chat_history[chat_id][-MAX_MESSAGES:]

    # Send to Gemini API
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"parts": [{"text": msg["content"]} for msg in chat_history[chat_id]]}]
        )
        ai_text = response.text
    except Exception as e:
        print("Gemini API Error:", e)
        ai_text = "⚠ Sorry, I couldn't process that right now."

    # Store AI reply
    chat_history[chat_id].append({"role": "assistant", "content": ai_text})
    save_chat_history()

    await update.message.reply_text(ai_text)

# -------------------------------
# Main Function
# -------------------------------

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))

    print(" Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
