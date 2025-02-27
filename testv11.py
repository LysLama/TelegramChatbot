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
import re  # Thêm thư viện regex

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Telegram Bot Token
TELE_TOKEN = os.getenv("TELE_TOKEN")
SAVE_DIR = "./data"
os.makedirs(SAVE_DIR, exist_ok=True)    

# Conversation states
ASK_RESPONSE_TYPE = 1
MAX_TOKENS = 50000  # Giới hạn số token tối đa cho mỗi câu trả lời

def truncate_text(text, max_tokens=MAX_TOKENS):
    """Cắt bớt câu hỏi nếu vượt quá số token cho phép"""
    words = text.split()
    if len(words) > max_tokens:
        return " ".join(words[:max_tokens])
    return text

def remove_urls(text):
    """Thay thế tất cả các URL trong văn bản bằng '[liên kết]'"""
    url_pattern = r'http[s]?://(?:[a-zA-Z0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.sub(url_pattern, "[]", text)

def estimate_tokens(text):
    """Ước lượng số token dựa trên số từ"""
    return len(text.split())

async def start(update: Update, context):
    """Start command handler."""
    # Xoá các dữ liệu cũ (nếu có) khi bắt đầu hội thoại mới
    context.user_data.clear()
    await update.message.reply_text("Gửi cho tôi câu hỏi của bạn:")
    return ASK_RESPONSE_TYPE

async def ask_response_type(update: Update, context):
    """Lưu câu hỏi mới và yêu cầu người dùng chọn định dạng phản hồi."""
    question = update.message.text
    context.user_data["question"] = question

    # Xóa kết quả của câu hỏi trước (nếu có) để đảm bảo bot sẽ tạo phản hồi mới cho câu hỏi hiện tại
    context.user_data.pop("gemini_response", None)

    # Gửi thông báo "Đang xử lý..."
    loading_message = await update.message.reply_text("Đang xử lý câu hỏi...")

    # Nhận diện ngôn ngữ
    try:
        lang = detect(question)
        context.user_data["lang"] = lang
    except LangDetectException:
        lang = "en"
        context.user_data["lang"] = lang

    # Tạo inline keyboard cho định dạng phản hồi ban đầu
    keyboard = [
        [
            InlineKeyboardButton("Text", callback_data="text"),
            InlineKeyboardButton("Audio", callback_data="audio"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Cập nhật tin nhắn loading thành "Chọn định dạng trả lời:" kèm inline keyboard
    await loading_message.edit_text("Chọn định dạng trả lời:", reply_markup=reply_markup)
    
    return ASK_RESPONSE_TYPE


async def handle_response(update: Update, context):
    """Xử lý callback từ inline keyboard cho cả phản hồi ban đầu và chuyển đổi định dạng."""
    query = update.callback_query
    await query.answer()

    # Lấy callback_data: có thể là "text", "audio", "convert_text" hoặc "convert_audio"
    response_data = query.data

    # Xác định đây là phản hồi ban đầu hay yêu cầu chuyển đổi
    is_initial = response_data in ["text", "audio"]

    # Ẩn inline keyboard của tin nhắn gốc (sử dụng edit để xóa reply_markup)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    question = context.user_data.get("question", "")
    lang = context.user_data.get("lang", "en")

    # Kiểm tra số token của câu hỏi
    total_used_tokens = context.user_data.get("total_used_tokens", 0)
    truncated_question = truncate_text(question)
    input_tokens = estimate_tokens(truncated_question)
    if total_used_tokens + input_tokens > MAX_TOKENS:
        await query.edit_message_text("Bạn đã hết số token cho phép trong hội thoại này.")
        return ConversationHandler.END

    # Nếu chưa có kết quả từ Gemini, gọi API để tạo phản hồi và lưu vào context.user_data
    if "gemini_response" not in context.user_data:
        model = genai.GenerativeModel("gemini-pro")
        try:
            response = model.generate_content(truncated_question, generation_config={"max_output_tokens": MAX_TOKENS})
            response_text = response.text.strip() if hasattr(response, "text") else "Xin lỗi, tôi không thể tạo phản hồi."
            response_text = response_text.replace('*', '')
            output_tokens = estimate_tokens(response_text)
            total_used_tokens += input_tokens + output_tokens
            context.user_data["total_used_tokens"] = total_used_tokens
            # Thêm thông tin token vào phản hồi
            response_text += f"\n\n🔹 Token đã dùng: {total_used_tokens}/{MAX_TOKENS}"
            context.user_data["gemini_response"] = response_text
        except Exception as e:
            await query.edit_message_text(f"Lỗi: {str(e)}")
            return ConversationHandler.END
    else:
        response_text = context.user_data["gemini_response"]

    # Xử lý theo định dạng yêu cầu
    if response_data in ["text", "convert_text"]:
        # Hiển thị phản hồi dạng văn bản (text)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Nghe Audio", callback_data="convert_audio")]
        ])
        try:
            await query.edit_message_text(text=response_text, reply_markup=keyboard)
        except Exception as e:
            # Nếu không thể chỉnh sửa tin nhắn, gửi tin mới
            await context.bot.send_message(chat_id=query.message.chat_id, text=response_text, reply_markup=keyboard)
    elif response_data in ["audio", "convert_audio"]:
        # Thông báo đang gửi phản hồi bằng audio (có thể chỉnh sửa tin nhắn để xóa keyboard)
        try:
            await query.edit_message_text(text="Đang gửi phản hồi bằng audio...")
        except Exception:
            pass
        # Tạo file audio từ phản hồi (loại bỏ URL trước khi chuyển giọng)
        tts_text = remove_urls(response_text)
        tts_lang = "vi" if lang == "vi" else "en"
        audio_path = os.path.join(SAVE_DIR, f"response_{uuid.uuid4()}.mp3")
        try:
            tts = gTTS(tts_text, lang=tts_lang, slow=False)
            tts.save(audio_path)
        except Exception as e:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"Lỗi khi tạo audio: {str(e)}")
            return ConversationHandler.END
        # Gửi voice message
        with open(audio_path, "rb") as audio_file:
            await context.bot.send_voice(chat_id=query.message.chat_id, voice=audio_file)
        asyncio.create_task(delete_file_after_delay(audio_path))
        # Sau khi gửi audio, cung cấp inline keyboard cho phép xem văn bản (chuyển sang text)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Xem Text", callback_data="convert_text")]
        ])
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Phản hồi bằng audio đã gửi. Nếu muốn xem văn bản, bấm nút dưới đây:",
            reply_markup=keyboard
        )

    # Nếu đây là phản hồi ban đầu, và nếu số token chưa hết, yêu cầu đặt câu hỏi mới
    if is_initial:
        if total_used_tokens < MAX_TOKENS:
            await context.bot.send_message(chat_id=query.message.chat_id, text="Bạn có thể đặt câu hỏi tiếp theo:")
            return ASK_RESPONSE_TYPE
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text="Bạn đã hết token cho hội thoại này. Vui lòng bắt đầu lại với /start")
            return ConversationHandler.END
    else:
        # Nếu là yêu cầu chuyển đổi, tiếp tục duy trì trạng thái hội thoại hiện tại
        return ASK_RESPONSE_TYPE

async def delete_file_after_delay(file_path: str, delay: int = 300):
    """Xóa file sau một khoảng thời gian nhất định"""
    await asyncio.sleep(delay)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Đã xóa: {file_path}")

async def cancel(update: Update, context):
    """Hủy hội thoại"""
    await update.message.reply_text("Hủy bỏ!")
    return ConversationHandler.END

async def stop(update: Update, context):
    """Dừng hội thoại khi người dùng nhập /stop"""
    await update.message.reply_text("Hội thoại đã kết thúc. Gõ /start để bắt đầu lại.")
    return ConversationHandler.END

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
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("stop", stop)],
        allow_reentry=True  
    )
    
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
