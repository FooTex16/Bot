import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# Load environment variable
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_KEY)

# Fungsi tanya Groq pakai streaming (mirip contohmu)
def tanya_groq(teks: str) -> str:
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",   # bisa ganti model lain, misalnya llama-3.1-70b-versatile
            messages=[
                {"role": "system", "content": "Kamu adalah AI asisten bernama RUDI."},
                {"role": "user", "content": teks},
            ],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            reasoning_effort="medium",
            stream=True,
            stop=None,
            tools=[{"type": "browser_search"}]
        )

        jawaban = ""
        for chunk in completion:
            delta = chunk.choices[0].delta.content or ""
            jawaban += delta
        return jawaban.strip() if jawaban else "⚠️ Tidak ada jawaban."
    except Exception as e:
        return f"⚠️ Error Groq: {e}"

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! 👋 Saya bot AI (Groq). Ketik pertanyaanmu!")

# Balas pesan user
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = update.message.text
    print(f"Pesan dari {update.effective_user.first_name}: {pesan}")
    jawaban = tanya_groq(pesan)
    await update.message.reply_text(jawaban)

def main():
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        print("🤖 Bot Groq berjalan... Tekan CTRL+C untuk berhenti.")
        app.run_polling()
    except Exception as e:
        print("⚠️ Terjadi error pada bot Telegram:")
        print(e)
        print("Pastikan hanya satu instance bot yang berjalan. Jika error 'Conflict: terminated by other getUpdates request', matikan proses bot lain yang sedang berjalan.")

if __name__ == "__main__":
    main()
