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
TELE_TOKEN = os.getenv("TELE_TOKEN")
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

    # Nhận diện ngôn ngữngữ
    try:
        lang = detect(question)
        context.user_data["lang"] = lang
    except LangDetectException:
        lang = "en"
        context.user_data["lang"] = lang

    # Tạo bàn inline keyboard kiểu phản hồi
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

import re  # Thêm thư viện regex

MAX_TOKENS = 500  # Giới hạn số token tối đa cho mỗi câu trả lời

def truncate_text(text, max_tokens=MAX_TOKENS):
    """Cắt bớt câu hỏi nếu vượt quá số token cho phép"""
    words = text.split()
    if len(words) > max_tokens:
        return " ".join(words[:max_tokens])
    return text

def remove_urls(text):
    """Thay thế tất cả các URL trong văn bản bằng '[liên kết]'"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.sub(url_pattern, "[]", text)

def estimate_tokens(text):
    """Ước lượng số token dựa trên số từ"""
    return len(text.split())

async def handle_response(update: Update, context):
    """Handle inline keyboard response"""
    query = update.callback_query
    await query.answer()

    response_type = query.data
    question = context.user_data.get("question", "")
    lang = context.user_data.get("lang", "en")

    # Gửi thông báo "Đang xử lý phản hồi..."
    loading_message = await query.edit_message_text("Đang xử lý phản hồi...")

    # Lấy tổng số token đã dùng trước đó, mặc định là 0
    total_used_tokens = context.user_data.get("total_used_tokens", 0)

    # Giới hạn số token của câu hỏi
    truncated_question = truncate_text(question)
    input_tokens = estimate_tokens(truncated_question)

    # Kiểm tra nếu vượt quá giới hạn token
    if total_used_tokens + input_tokens > MAX_TOKENS:
        await query.edit_message_text("Bạn đã hết số token cho phép trong hội thoại này.")
        return ConversationHandler.END

    # Gọi API Gemini để tạo phản hồi
    model = genai.GenerativeModel("gemini-pro")
    try:
        response = model.generate_content(truncated_question, generation_config={"max_output_tokens": MAX_TOKENS})

        response_text = response.text.strip() if hasattr(response, "text") else "Xin lỗi, tôi không thể tạo phản hồi."
        response_text = response_text.replace('*', '')

        output_tokens = estimate_tokens(response_text)
        total_used_tokens += input_tokens + output_tokens
        context.user_data["total_used_tokens"] = total_used_tokens  # Cập nhật tổng số token

        # Thêm số token đã dùng vào phản hồi
        response_text += f"\n\n🔹 Token đã dùng: {total_used_tokens}/{MAX_TOKENS}"

        # Nếu phản hồi là audio, xóa URL trước khi đọc và thêm thông tin token
        if response_type == "audio":
            tts_text = remove_urls(response_text)
            tts_lang = "vi" if lang == "vi" else "en"
            audio_path = os.path.join(SAVE_DIR, f"response_{uuid.uuid4()}.mp3")
            tts = gTTS(tts_text, lang=tts_lang)
            tts.save(audio_path)

            await loading_message.edit_text("Đang gửi phản hồi bằng audio...")
            await context.bot.send_voice(chat_id=query.message.chat_id, voice=open(audio_path, "rb"))
            asyncio.create_task(delete_file_after_delay(audio_path))
        else:
            await loading_message.edit_text(response_text)

    except Exception as e:
        await query.edit_message_text(f"Lỗi: {str(e)}")

    # Tiếp tục hội thoại nếu chưa hết token
    if total_used_tokens < MAX_TOKENS:
        await query.message.reply_text("Bạn có thể đặt câu hỏi tiếp theo:")
        return ASK_RESPONSE_TYPE
    else:
        await query.message.reply_text("Bạn đã hết token cho hội thoại này. Vui lòng bắt đầu lại với /start")
        return ConversationHandler.END

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

# Thêm trạng thái END
END = ConversationHandler.END

async def stop(update: Update, context):
    """Dừng hội thoại khi người dùng nhập /stop"""
    await update.message.reply_text("Hội thoại đã kết thúc. Gõ /start để bắt đầu lại.")
    return END

def main():
    app = Application.builder().token(TELE_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_RESPONSE_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_response_type),
                CallbackQueryHandler(handle_response)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("stop", stop)],  # Thêm /stop vào fallbacks
        allow_reentry=True  
    )
    
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
