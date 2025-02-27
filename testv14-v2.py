import os
import asyncio
import uuid
import time
import re  # Thư viện regex
import aiohttp  # Thư viện để gọi API bất đồng bộ
from dotenv import load_dotenv
from urllib.parse import quote_plus

from gtts import gTTS
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
import google.generativeai as genai
from langdetect import detect, LangDetectException

# Load biến môi trường (nếu cần)
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Telegram Bot Token
TELE_TOKEN = os.getenv("TELE_TOKEN")
SAVE_DIR = "./data"
os.makedirs(SAVE_DIR, exist_ok=True)    

# Conversation states
ASK_RESPONSE_TYPE = 1
WAITING_FOR_LOCATION = 2  # Trạng thái chờ nhận vị trí từ người dùng
MAX_TOKENS = 50000  # Giới hạn số token tối đa cho mỗi câu trả lời

# Thời gian sống của token (giả lập, đơn vị: giây)
TOKEN_LIFETIME = 3600  # 1 giờ

# Hàm tạo token mới
def generate_session_token():
    return {
        "token": str(uuid.uuid4()),
        "expires_at": time.time() + TOKEN_LIFETIME
    }

def truncate_text(text, max_tokens=MAX_TOKENS):
    """Cắt bớt văn bản nếu vượt quá số token cho phép"""
    words = text.split()
    if len(words) > max_tokens:
        return " ".join(words[:max_tokens])
    return text

def remove_urls(text):
    """Thay thế các URL trong văn bản bằng '[liên kết]'"""
    url_pattern = r'http[s]?://(?:[a-zA-Z0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.sub(url_pattern, "[]", text)

def estimate_tokens(text):
    """Ước lượng số token dựa trên số từ"""
    return len(text.split())

async def search_product(query: str):
    """
    Tìm kiếm sản phẩm sử dụng Google Custom Search API theo kiểu tìm kiếm hình ảnh.
    Hàm sẽ trả về tuple (image_url, purchase_link) nếu có kết quả, hoặc (None, None) nếu không tìm thấy.
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")
    google_cx = os.getenv("GOOGLE_CX")
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": google_api_key,
        "cx": google_cx,
        "q": query,
        "searchType": "image",  # Sử dụng tìm kiếm hình ảnh
        "num": 1  # Lấy kết quả đầu tiên
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            result = await resp.json()
    if "items" in result and len(result["items"]) > 0:
        item = result["items"][0]
        image_url = item.get("link")
        # 'contextLink' chứa đường dẫn đến trang chứa hình ảnh (có thể là link mua hàng)
        purchase_link = item.get("image", {}).get("contextLink")
        return image_url, purchase_link
    return None, None

async def ask_response_type(update: Update, context):
    question = update.message.text
    context.user_data["question"] = question
    context.user_data.pop("gemini_response", None)
    
    # Xác định loại tìm kiếm dựa trên nội dung câu hỏi
    lower_question = question.lower()
    if "thời tiết" in lower_question:
        context.user_data["search_type"] = "weather"
    elif "mua" in lower_question or "sản phẩm" in lower_question:
        context.user_data["search_type"] = "product"
    else:
        context.user_data["search_type"] = None

    # Khởi tạo hoặc gia hạn token phiên
    if "session_token" not in context.user_data:
        context.user_data["session_token"] = generate_session_token()
    else:
        context.user_data["session_token"]["expires_at"] = time.time() + TOKEN_LIFETIME

    loading_message = await update.message.reply_text("Đang xử lý câu hỏi...")
    try:
        lang = detect(question)
        context.user_data["lang"] = lang
    except LangDetectException:
        lang = "en"
        context.user_data["lang"] = lang

    # Xây dựng inline keyboard: nếu có tìm kiếm Google thì thêm nút "Google Search"
    keyboard_buttons = [
        InlineKeyboardButton("Text", callback_data="text"),
        InlineKeyboardButton("Audio", callback_data="audio")
    ]
    if context.user_data["search_type"]:
        keyboard_buttons.append(InlineKeyboardButton("Google Search", callback_data="google_search"))
    keyboard_buttons.append(InlineKeyboardButton("Refresh Token", callback_data="refresh_token"))
    keyboard = [keyboard_buttons]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await loading_message.edit_text("Chọn định dạng trả lời:", reply_markup=reply_markup)
    
    return ASK_RESPONSE_TYPE

async def handle_response(update: Update, context):
    query = update.callback_query
    await query.answer()
    response_data = query.data

    # Kiểm tra token hợp lệ
    session_token = context.user_data.get("session_token", {})
    if session_token.get("expires_at", 0) < time.time():
        await query.edit_message_text("Phiên làm việc đã hết hạn. Vui lòng làm mới token!")
        return ASK_RESPONSE_TYPE

    if response_data == "refresh_token":
        context.user_data["session_token"] = generate_session_token()
        context.user_data["total_used_tokens"] = 0
        await query.edit_message_text(
            text="Token đã được làm mới thành công!\nBạn có thể tiếp tục đặt câu hỏi:",
            reply_markup=None
        )
        return ASK_RESPONSE_TYPE

    # Xử lý tìm kiếm Google nếu người dùng chọn "Google Search"
    if response_data == "google_search":
        search_type = context.user_data.get("search_type")
        if search_type == "weather":
            # Nếu chưa có vị trí, yêu cầu người dùng chia sẻ vị trí
            if "location" not in context.user_data:
                location_button = KeyboardButton("Chia sẻ vị trí", request_location=True)
                location_markup = ReplyKeyboardMarkup([[location_button]], one_time_keyboard=True)
                await query.edit_message_text("Vui lòng chia sẻ vị trí của bạn để tìm kiếm thời tiết:", reply_markup=location_markup)
                return WAITING_FOR_LOCATION
            else:
                # Nếu đã có vị trí, tạo link tìm kiếm theo GPS
                user_location = context.user_data["location"]
                lat = user_location.latitude
                lon = user_location.longitude
                search_url = f"https://www.google.com/search?q=thời+tiết+{lat}+{lon}"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Mở kết quả trên Google", url=search_url)]
                ])
                await query.edit_message_text("Đây là kết quả tìm kiếm thời tiết dựa trên vị trí của bạn:", reply_markup=keyboard)
                return ASK_RESPONSE_TYPE
        elif search_type == "product":
            # Tìm kiếm sản phẩm: gọi API Google Custom Search để lấy hình ảnh và link sản phẩm
            question = context.user_data.get("question", "")
            image_url, purchase_link = await search_product(question)
            if image_url and purchase_link:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Mở trang sản phẩm", url=purchase_link)]
                ])
                # Gửi ảnh sản phẩm kèm theo inline button để mở trang mua hàng
                await query.edit_message_text("Đây là kết quả tìm kiếm sản phẩm:")
                await context.bot.send_photo(
                    chat_id=query.message.chat_id, 
                    photo=image_url, 
                    caption="Sản phẩm có thể phù hợp với yêu cầu của bạn.",
                    reply_markup=keyboard
                )
            else:
                await query.edit_message_text("Không tìm thấy kết quả sản phẩm phù hợp.")
            return ASK_RESPONSE_TYPE
        else:
            # Nếu không thuộc trường hợp tìm kiếm, chuyển sang xử lý Gemini như thông thường
            response_data = "text"

    # Ẩn inline keyboard của tin nhắn gốc (xóa reply_markup)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    # Xử lý phản hồi dạng text/audio từ Gemini
    question = context.user_data.get("question", "")
    lang = context.user_data.get("lang", "en")

    total_used_tokens = context.user_data.get("total_used_tokens", 0)
    truncated_question = truncate_text(question)
    input_tokens = estimate_tokens(truncated_question)
    if total_used_tokens + input_tokens > MAX_TOKENS:
        await query.edit_message_text("Bạn đã hết số token cho phép trong hội thoại này.")
        return ConversationHandler.END

    # Nếu chưa có phản hồi từ Gemini cho câu hỏi hiện tại, gọi API
    if "gemini_response" not in context.user_data:
        model = genai.GenerativeModel("gemini-exp-1206")
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
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Nghe Audio", callback_data="convert_audio"),
             InlineKeyboardButton("Refresh Token", callback_data="refresh_token")]
        ])
        try:
            await query.edit_message_text(text=response_text, reply_markup=keyboard)
        except Exception:
            await context.bot.send_message(chat_id=query.message.chat_id, text=response_text, reply_markup=keyboard)
    elif response_data in ["audio", "convert_audio"]:
        try:
            await query.edit_message_text(text="Đang gửi phản hồi bằng audio...")
        except Exception:
            pass
        tts_text = remove_urls(response_text)
        tts_lang = "vi" if lang == "vi" else "en"
        audio_path = os.path.join(SAVE_DIR, f"response_{uuid.uuid4()}.mp3")
        try:
            tts = gTTS(tts_text, lang=tts_lang, slow=False)
            tts.save(audio_path)
        except Exception as e:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"Lỗi khi tạo audio: {str(e)}")
            return ConversationHandler.END
        with open(audio_path, "rb") as audio_file:
            await context.bot.send_voice(chat_id=query.message.chat_id, voice=audio_file)
        asyncio.create_task(delete_file_after_delay(audio_path))
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Xem Text", callback_data="convert_text"),
             InlineKeyboardButton("Refresh Token", callback_data="refresh_token")]
        ])
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Phản hồi bằng audio đã gửi. Nếu muốn xem văn bản, bấm nút dưới đây:",
            reply_markup=keyboard
        )

    if response_data in ["text", "audio"]:
        if total_used_tokens < MAX_TOKENS:
            await context.bot.send_message(chat_id=query.message.chat_id, text="Bạn có thể đặt câu hỏi tiếp theo:")
            return ASK_RESPONSE_TYPE
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text="Bạn đã hết token cho hội thoại này. Vui lòng khởi động lại bot.")
            return ConversationHandler.END
    else:
        return ASK_RESPONSE_TYPE

async def handle_location(update: Update, context):
    """Xử lý nhận vị trí từ người dùng (cho tìm kiếm thời tiết)"""
    user_location = update.message.location
    if not user_location:
        await update.message.reply_text("Không nhận được vị trí. Vui lòng thử lại.")
        return WAITING_FOR_LOCATION
    context.user_data["location"] = user_location
    lat = user_location.latitude
    lon = user_location.longitude
    search_url = f"https://www.google.com/search?q=thời+tiết+{lat}+{lon}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Mở kết quả trên Google", url=search_url)]
    ])
    await update.message.reply_text("Đây là kết quả tìm kiếm thời tiết dựa trên vị trí của bạn:", reply_markup=keyboard)
    return ASK_RESPONSE_TYPE

async def delete_file_after_delay(file_path: str, delay: int = 300):
    """Xóa file sau một khoảng thời gian nhất định (mặc định 5 phút)"""
    await asyncio.sleep(delay)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Đã xóa: {file_path}")

def main():
    app = Application.builder().token(TELE_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_response_type)],
        states={
            ASK_RESPONSE_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_response_type),
                CallbackQueryHandler(handle_response)
            ],
            WAITING_FOR_LOCATION: [
                MessageHandler(filters.LOCATION, handle_location)
            ]
        },
        fallbacks=[],
        allow_reentry=True  
    )
    
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
