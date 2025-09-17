import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from groq import Groq

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

openai_client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

# Fungsi tanya AI dengan fallback
def tanya_ai(teks: str) -> str:
    # 1. Coba pakai OpenAI
    if openai_client:
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": teks}]
            )
            return response.choices[0].message.content
        except Exception as e:
            err = str(e)
            if "insufficient_quota" in err or "429" in err:
                print("⚠️ Kuota OpenAI habis, fallback ke Groq...")
            else:
                return f"⚠️ Error OpenAI: {e}"

    # 2. Fallback ke Groq
    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[{"role": "user", "content": teks}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"⚠️ Error Groq: {e}"

    # 3. Jika dua-duanya gagal
    return "⚠️ Tidak ada AI service yang tersedia. Pastikan API key benar."

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! 👋 Saya bot AI otomatis.\nKirim pertanyaanmu, saya akan jawab pakai AI (OpenAI/Groq).")

# Balas semua pesan user
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = update.message.text
    print(f"Pesan dari {update.effective_user.first_name}: {pesan}")
    jawaban = tanya_ai(pesan)
    await update.message.reply_text(jawaban)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    print("🤖 Bot berjalan... Tekan CTRL+C untuk berhenti.")
    app.run_polling()

if __name__ == "__main__":
    main()
