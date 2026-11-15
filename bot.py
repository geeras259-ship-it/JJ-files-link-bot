import os
from threading import Thread
from flask import Flask
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- 1. Dummy Flask Server (Render port requirement kosam) ---
app_flask = Flask("")


@app_flask.route("/")
def home():
  return "Bot is alive and running!"


def run_flask():
  app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


# --- 2. Telegram Bot Configurations ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FILEMOON_API_KEY = os.getenv("FILEMOON_API_KEY", "166670chgr2qacpij1f2gx")


# 3. /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_name = update.effective_user.first_name
  welcome_message = (
      f"హాయ్ {user_name}! 👋\n\n"
      "Nenu FileMoon Uploader Bot ni. 🚀\n"
      "📥 ఏ file అయినా forward చేయండి, FileMoon ki upload చేసి Watch & Embed links ఇస్తాను.\n"
      "📋 Mee files list chudadaniki & delete cheyadaniki `/files` ani type cheyandi!"
  )
  await update.message.reply_text(welcome_message, parse_mode="Markdown")


# 4. FileMoon Upload Function
def upload_to_filemoon(file_path):
  try:
    server_res = requests.get(
        f"https://filemoon.sx/api/upload/server?key={FILEMOON_API_KEY}"
    ).json()
    upload_url = server_res.get("result")

    if not upload_url:
      return None

    with open(file_path, "rb") as f:
      files = {"file": f}
      res = requests.post(upload_url, files=files).json()

    if res.get("status") == 200:
      file_code = res.get("file_code")
      watch_link = f"https://filemoon.sx/{file_code}"
      embed_link = f"https://filemoon.sx/e/{file_code}"
      return {
          "code": file_code,
          "watch": watch_link,
          "embed": embed_link,
      }
  except Exception as e:
    print(f"Error: {e}")
  return None


# 5. Handle File Uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message = update.message
  file = (
      message.document
      or message.video
      or message.audio
      or message.photo[-1]
      if message.photo
      else None
  )

  if not file:
    await message.reply_text(
        "Dayachesi oka valid file/video forward cheyyandi."
    )
    return

  status_message = await message.reply_text(
      "📥 File download avtundi, konchem apandi..."
  )

  new_file = await context.bot.get_file(file.file_id)
  local_path = f"downloads/{file.file_id}"
  os.makedirs("downloads", exist_ok=True)
  await new_file.download_to_drive(local_path)

  await status_message.edit_text(
      "🚀 FileMoon ki upload avtundi, wait cheyyandi..."
  )

  result = upload_to_filemoon(local_path)

  if os.path.exists(local_path):
    os.remove(local_path)

  if result:
    response_text = (
        f"✅ **Upload Successful!**\n\n"
        f"🔗 **Watch Link:** {result['watch']}\n"
        f"💻 **Embed Link:** `<iframe src=\"{result['embed']}\" width=\"640\" height=\"360\" frameborder=\"0\" allowfullscreen></iframe>`"
    )
    keyboard = [[
        InlineKeyboardButton(
            "🗑 Delete File", callback_data=f"del_{result['code']}"
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await status_message.edit_text(
        response_text,
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=reply_markup,
    )
  else:
    await status_message.edit_text(
        "❌ FileMoon upload fail ayyindi. API Key limits check chesukondi."
    )


# 6. /files command - List files from FileMoon account
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
  try:
    res = requests.get(
        f"https://filemoon.sx/api/file/list?key={FILEMOON_API_KEY}"
    ).json()
    files = res.get("result", {}).get("files", [])

    if not files:
      await update.message.reply_text("📁 Mee account lo evvi files levu.")
      return

    await update.message.reply_text("📋 Mee FileMoon files list:")

    for f in files[:10]:
      title = f.get("title", "Unknown File")
      code = f.get("file_code")
      watch_link = f"https://filemoon.sx/{code}"

      keyboard = [[
          InlineKeyboardButton("🗑 Delete", callback_data=f"del_{code}")
      ]]
      reply_markup = InlineKeyboardMarkup(keyboard)

      msg = f"📄 **{title}**\n🔗 {watch_link}"
      await update.message.reply_text(
          msg, parse_mode="Markdown", reply_markup=reply_markup
      )
  except Exception as e:
    await update.message.reply_text(f"❌ Error fetching files: {e}")


# 7. Button Click Handler (For Deletion)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  data = query.data
  if data.startswith("del_"):
    file_code = data.split("_")[1]

    del_res = requests.get(
        f"https://filemoon.sx/api/file/delete?key={FILEMOON_API_KEY}&file_code={file_code}"
    ).json()

    if del_res.get("status") == 200:
      await query.edit_message_text(
          "🗑 **File successfully delete ayyindi!**", parse_mode="Markdown"
      )
    else:
      await query.edit_message_text("❌ Delete avvatam lo error vachindi.")


def main():
  # Start Flask server in background thread for Render port binding
  t = Thread(target=run_flask)
  t.start()

  # Start Telegram Bot
  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("files", list_files))
  app.add_handler(
      MessageHandler(
          filters.Document.ALL | filters.VIDEO | filters.AUDIO, handle_file
      )
  )
  app.add_handler(CallbackQueryHandler(button_handler))

  print("🤖 Telegram Bot with Flask & Delete feature is running...")
  app.run_polling()


if __name__ == "__main__":
  main()
