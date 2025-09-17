import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load token dari .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! 👋 Saya bot Telegram AI. Silakan tanya apa saja!")

# Fungsi sederhana untuk menjawab pertanyaan seperti otak AI
def jawab_pertanyaan(teks):
    teks = teks.lower()
    if "siapa kamu" in teks:
        return "Saya adalah bot AI yang dibuat dengan Python."
    elif "berapa 2+2" in teks or "berapa dua tambah dua" in teks:
        return "2 + 2 = 4"
    elif "apa itu ai" in teks or "apa itu artificial intelligence" in teks:
        return "AI (Artificial Intelligence) adalah kecerdasan buatan yang dibuat oleh manusia untuk menyelesaikan tugas tertentu."
    elif "siapa presiden indonesia" in teks:
        return "Presiden Indonesia saat ini adalah Joko Widodo (per 2024)."
    elif "halo" in teks:
        return "Halo juga! Ada yang bisa saya bantu?"
    else:
        return None

# Balas semua pesan teks, print ke terminal, dan jawab jika pertanyaan sesuai
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = update.message.text
    print(f"Pesan dari {update.effective_user.first_name}: {pesan}")
    jawaban = jawab_pertanyaan(pesan)
    if jawaban:
        await update.message.reply_text(jawaban)
    else:
        await update.message.reply_text(f"Kamu mengirim: {pesan}")

def main():
    import pytz
    import asyncio

    os.environ['TZ'] = 'UTC'

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    app.run_polling()

if __name__ == "__main__":
    main()
