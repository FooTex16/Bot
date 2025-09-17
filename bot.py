import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Load token dari file .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! 👋 Saya bot AI otomatis. Silakan tanya apa saja!")

# Fungsi untuk tanya ke OpenAI
def tanya_ai(teks: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": teks}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Terjadi error: {e}"

# Balas semua pesan user dengan jawaban AI
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = update.message.text
    print(f"Pesan dari {update.effective_user.first_name}: {pesan}")
    jawaban = tanya_ai(pesan)
    await update.message.reply_text(jawaban)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    print("🤖 Bot berjalan... Tekan CTRL+C untuk berhenti.")
    app.run_polling()

if __name__ == "__main__":
    main()
