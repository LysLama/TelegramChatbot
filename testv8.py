import os
import asyncio
import uuid
from dotenv import load_dotenv
load_dotenv()
from gtts import gTTS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
import google.generativeai as genai
from langdetect import detect, LangDetectException

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Telegram Bot Token
TOKEN = os.getenv("TOKEN")
SAVE_DIR = "./data"
os.makedirs(SAVE_DIR, exist_ok=True)    

# Conversation states
ASK_RESPONSE_TYPE = 1

async def start(update: Update, context):
    """Start command handler."""
    await update.message.reply_text("Gửi cho tôi câu hỏi của bạn:")
    return ASK_RESPONSE_TYPE

async def ask_response_type(update: Update, context):
    """Store question and ask for response type with inline keyboard"""
    question = update.message.text
    context.user_data["question"] = question

    # Gửi thông báo "Đang xử lý..."
    loading_message = await update.message.reply_text("Đang xử lý câu hỏi...")

    # Detect language
    try:
        lang = detect(question)
        context.user_data["lang"] = lang
    except LangDetectException:
        lang = "en"
        context.user_data["lang"] = lang

    # Tạo bàn phím lựa chọn kiểu phản hồi
    keyboard = [
        [
            InlineKeyboardButton("Text", callback_data="text"),
            InlineKeyboardButton("Audio", callback_data="audio"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Cập nhật tin nhắn loading thành "Chọn định dạng trả lời:"
    await loading_message.edit_text("Chọn định dạng trả lời:", reply_markup=reply_markup)
    
    return ASK_RESPONSE_TYPE

async def handle_response(update: Update, context):
    """Handle inline keyboard response"""
    query = update.callback_query
    await query.answer()

    response_type = query.data
    question = context.user_data.get("question", "")
    lang = context.user_data.get("lang", "en")

    # Gửi thông báo "Đang xử lý phản hồi..."
    loading_message = await query.edit_message_text("Đang xử lý phản hồi...")

    # Gọi API Gemini để tạo phản hồi
    model = genai.GenerativeModel("gemini-pro")
    try:
        response = model.generate_content(question)
        response_text = response.text.strip() if hasattr(response, "text") else "Xin lỗi, tôi không thể tạo phản hồi."
        response_text = response_text.replace('*', '')  # Xóa dấu *
    except Exception as e:
        response_text = f"Lỗi: {str(e)}"

    # Xử lý loại phản hồi
    if response_type == "audio":
        tts_lang = "vi" if lang == "vi" else "en"
        audio_path = os.path.join(SAVE_DIR, f"response_{uuid.uuid4()}.mp3")
        tts = gTTS(response_text, lang=tts_lang)
        tts.save(audio_path)

        await loading_message.edit_text("Đang gửi phản hồi bằng audio...")
        await context.bot.send_voice(
            chat_id=query.message.chat_id,
            voice=open(audio_path, "rb")
        )
        asyncio.create_task(delete_file_after_delay(audio_path))
    else:
        await loading_message.edit_text(response_text)

    # Tiếp tục hội thoại
    await query.message.reply_text("Bạn có thể đặt câu hỏi tiếp theo:")
    return ASK_RESPONSE_TYPE

async def delete_file_after_delay(file_path: str, delay: int = 3600):
    """Delete file after delay"""
    await asyncio.sleep(delay)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Đã xóa: {file_path}")

async def cancel(update: Update, context):
    """Cancel conversation"""
    await update.message.reply_text("Hủy bỏ!")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_RESPONSE_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_response_type),
                CallbackQueryHandler(handle_response)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True  # Cho phép quay lại hội thoại mà không cần /start

    )
    
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()