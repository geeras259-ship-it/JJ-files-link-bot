import os
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Configurations (Render environment variables nundi read chesthundi)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FILEMOON_API_KEY = os.getenv("FILEMOON_API_KEY", "166670chgr2qacpij1f2gx")


# 1. /start command ichinappudu respond avvadaniki
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_name = update.effective_user.first_name
  welcome_message = (
      f"హాయ్ {user_name}! 👋\n\n"
      "Nenu FileMoon Uploader Bot ni. 🚀\n"
      "Meeru ఏ file లేదా video పంపినా/forward చేసినా, nenu dani automatic ga **FileMoon** ki upload చేసి Watch & Embed links ఇస్తాను.\n\n"
      "📥 *Oka file ni ఇక్కడ forward చేయండి!*"
  )
  await update.message.reply_text(welcome_message, parse_mode="Markdown")


def upload_to_filemoon(file_path):
  try:
    # 1. Get FileMoon upload server URL
    server_res = requests.get(
        f"https://filemoon.sx/api/upload/server?key={FILEMOON_API_KEY}"
    ).json()
    upload_url = server_res.get("result")

    if not upload_url:
      return None

    # 2. Upload file to FileMoon server
    with open(file_path, "rb") as f:
      files = {"file": f}
      res = requests.post(upload_url, files=files).json()

    # Response check
    if res.get("status") == 200:
      file_code = res.get("file_code")
      watch_link = f"https://filemoon.sx/{file_code}"
      embed_link = f"https://filemoon.sx/e/{file_code}"
      return {"watch": watch_link, "embed": embed_link}
  except Exception as e:
    print(f"Error: {e}")
  return None


# 2. Files handle chese function
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
    await message.reply_text("Dayachesi oka valid file/video forward cheyyandi.")
    return

  status_message = await message.reply_text(
      "📥 File download avtundi, konchem apandi..."
  )

  # Download file from Telegram
  new_file = await context.bot.get_file(file.file_id)
  local_path = f"downloads/{file.file_id}"
  os.makedirs("downloads", exist_ok=True)
  await new_file.download_to_drive(local_path)

  await status_message.edit_text(
      "🚀 FileMoon ki upload avtundi, wait cheyyandi..."
  )

  # Upload to FileMoon
  links = upload_to_filemoon(local_path)

  # Local file delete cheyadam (Storage save kosam)
  if os.path.exists(local_path):
    os.remove(local_path)

  if links:
    response_text = (
        f"✅ **Upload Successful!**\n\n"
        f"🔗 **Watch Link:** {links['watch']}\n"
        f"💻 **Embed Link:** `<iframe src=\"{links['embed']}\" width=\"640\" height=\"360\" frameborder=\"0\" allowfullscreen></iframe>`"
    )
    await status_message.edit_text(
        response_text, parse_mode="Markdown", disable_web_page_preview=True
    )
  else:
    await status_message.edit_text(
        "❌ FileMoon upload fail ayyindi. API Key or limits check chesukondi."
    )


def main():
  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

  # Handlers register cheyyadam
  app.add_handler(CommandHandler("start", start))
  app.add_handler(
      MessageHandler(
          filters.Document.ALL | filters.VIDEO | filters.AUDIO, handle_file
      )
  )

  print("🤖 Telegram Bot is running...")
  app.run_polling()


if __name__ == "__main__":
  main()
