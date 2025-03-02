import os
import asyncio
import uuid
import json
import time
import re
import bcrypt  # Thư viện mã hóa mật khẩu
from dotenv import load_dotenv
load_dotenv()
from gtts import gTTS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
)
import google.generativeai as genai
from langdetect import detect, LangDetectException

# ============================
# CẤU HÌNH VÀ ĐỊNH NGHĨA TOÀN CỤC
# ============================

# Thông tin mặc định từ biến môi trường (cho các yêu cầu khác)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Nếu người dùng chưa đăng ký API riêng, mặc định dùng GEMINI_API_KEY từ env
genai.configure(api_key=GEMINI_API_KEY)

TELE_TOKEN = os.getenv("TELE_TOKEN")
SAVE_DIR = "./data"
os.makedirs(SAVE_DIR, exist_ok=True)

# File JSON lưu thông tin người dùng
USER_DATA_FILENAME = "users.json"
USER_DATA_FILEPATH = os.path.join(SAVE_DIR, USER_DATA_FILENAME)

# Nếu file chưa tồn tại, khởi tạo file rỗng
if not os.path.exists(USER_DATA_FILEPATH):
    with open(USER_DATA_FILEPATH, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

# Các hằng số cho conversation của Gemini Q&A
ASK_RESPONSE_TYPE = 100  # trạng thái cho Q&A
MAX_TOKENS = 50000       # Giới hạn số token cho mỗi hội thoại
TOKEN_LIFETIME = 3600    # Thời gian sống của token (1 giờ)

# Các trạng thái cho quá trình xác thực (đăng nhập/đăng ký)
AUTH_CHOICE, REGISTER_ID, REGISTER_PASSWORD, REGISTER_GEMINI, LOGIN_ID, LOGIN_PASSWORD = range(10, 16)

# ============================
# HÀM HỖ TRỢ CHO VIỆC QUẢN LÝ NGƯỜI DÙNG
# ============================

def load_users_data():
    """Đọc dữ liệu người dùng từ file JSON."""
    try:
        with open(USER_DATA_FILEPATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi đọc file người dùng: {e}")
        return {}

def save_users_data(data):
    """Lưu dữ liệu người dùng vào file JSON."""
    try:
        with open(USER_DATA_FILEPATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Lỗi ghi file người dùng: {e}")

def hash_password(password: str) -> bytes:
    """Mã hóa mật khẩu sử dụng bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password: str, hashed: bytes) -> bool:
    """So sánh mật khẩu nhập vào với mật khẩu đã được mã hóa."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def generate_session_token():
    """Tạo token phiên mới (giả lập) với thời gian sống TOKEN_LIFETIME."""
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

async def delete_file_after_delay(file_path: str, delay: int = 300):
    """Xóa file sau một khoảng thời gian nhất định (mặc định 5 phút)"""
    await asyncio.sleep(delay)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Đã xóa: {file_path}")

# ============================
# PHẦN XÁC THỰC: ĐĂNG NHẬP / ĐĂNG KÝ
# ============================

async def start_auth(update: Update, context):
    """Lệnh /start: Hiển thị lựa chọn đăng nhập hay đăng ký."""
    keyboard = [
        [
            InlineKeyboardButton("Đăng nhập", callback_data="login"),
            InlineKeyboardButton("Đăng ký", callback_data="register"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Chào mừng! Vui lòng chọn:", reply_markup=reply_markup)
    return AUTH_CHOICE

async def auth_choice(update: Update, context):
    """Xử lý lựa chọn đăng nhập hoặc đăng ký."""
    query = update.callback_query
    await query.answer()
    choice = query.data
    if choice == "register":
        await query.edit_message_text("Đăng ký:\nVui lòng nhập ID của bạn:")
        return REGISTER_ID
    elif choice == "login":
        await query.edit_message_text("Đăng nhập:\nVui lòng nhập ID của bạn:")
        return LOGIN_ID

async def register_id(update: Update, context):
    """Nhận ID người dùng trong quá trình đăng ký."""
    user_id = update.message.text.strip()
    users = load_users_data()
    if user_id in users:
        await update.message.reply_text("ID này đã tồn tại. Vui lòng chọn đăng nhập hoặc thử ID khác.")
        return ConversationHandler.END
    context.user_data["reg_id"] = user_id
    await update.message.reply_text("Vui lòng nhập mật khẩu của bạn:")
    return REGISTER_PASSWORD

async def register_password(update: Update, context):
    """Nhận mật khẩu của người dùng trong quá trình đăng ký."""
    password = update.message.text.strip()
    context.user_data["reg_password"] = password
    await update.message.reply_text("Vui lòng nhập API Gemini của bạn:")
    return REGISTER_GEMINI

async def register_gemini(update: Update, context):
    """Hoàn thiện đăng ký: lưu thông tin người dùng vào file JSON sau khi mã hóa mật khẩu."""
    gemini_api = update.message.text.strip()
    user_id = context.user_data.get("reg_id")
    password = context.user_data.get("reg_password")
    
    # Mã hóa mật khẩu
    hashed_pass = hash_password(password)
    
    # Lưu vào file JSON
    users = load_users_data()
    users[user_id] = {
        "hashed_password": hashed_pass.decode("utf-8"),  # Lưu dưới dạng chuỗi
        "gemini_api": gemini_api
    }
    save_users_data(users)
    
    # Đánh dấu người dùng đã đăng nhập thành công
    context.user_data["authenticated"] = True
    context.user_data["user_credentials"] = {
        "id": user_id,
        "gemini_api": gemini_api
    }
    # Khởi tạo token phiên cho việc sử dụng API Gemini
    context.user_data["session_token"] = generate_session_token()
    context.user_data["total_used_tokens"] = 0
    
    await update.message.reply_text("Đăng ký thành công! Bạn đã đăng nhập và có thể sử dụng bot để đặt câu hỏi.")
    return ConversationHandler.END

async def login_id(update: Update, context):
    """Nhận ID người dùng trong quá trình đăng nhập."""
    user_id = update.message.text.strip()
    context.user_data["login_id"] = user_id
    await update.message.reply_text("Vui lòng nhập mật khẩu của bạn:")
    return LOGIN_PASSWORD

async def login_password(update: Update, context):
    """Kiểm tra mật khẩu khi đăng nhập."""
    password = update.message.text.strip()
    user_id = context.user_data.get("login_id")
    users = load_users_data()
    
    if user_id not in users:
        await update.message.reply_text("ID không tồn tại. Vui lòng đăng ký hoặc kiểm tra lại.")
        return ConversationHandler.END
    
    # Lấy mật khẩu đã mã hóa từ file
    stored_hash = users[user_id]["hashed_password"].encode("utf-8")
    if check_password(password, stored_hash):
        gemini_api = users[user_id]["gemini_api"]
        context.user_data["authenticated"] = True
        context.user_data["user_credentials"] = {
            "id": user_id,
            "gemini_api": gemini_api
        }
        # Khởi tạo token phiên cho việc sử dụng API Gemini
        context.user_data["session_token"] = generate_session_token()
        context.user_data["total_used_tokens"] = 0
        await update.message.reply_text("Đăng nhập thành công! Bây giờ, bạn có thể đặt câu hỏi để sử dụng API Gemini.")
    else:
        await update.message.reply_text("Mật khẩu không đúng. Vui lòng thử lại.")
    return ConversationHandler.END

# ============================
# PHẦN GIAO TIẾP VỚI API GEMINI (Q&A)
# ============================

async def ask_response_type(update: Update, context):
    """Xử lý tin nhắn của người dùng cho câu hỏi gửi tới API Gemini."""
    # Kiểm tra xem người dùng đã đăng nhập chưa
    if not context.user_data.get("authenticated"):
        await update.message.reply_text("Vui lòng đăng nhập hoặc đăng ký bằng lệnh /start trước khi sử dụng bot.")
        return ConversationHandler.END

    question = update.message.text
    context.user_data["question"] = question
    context.user_data.pop("gemini_response", None)

    # Gia hạn hoặc khởi tạo token phiên
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

    keyboard = [
        [
            InlineKeyboardButton("Text", callback_data="text"),
            InlineKeyboardButton("Audio", callback_data="audio"),
            InlineKeyboardButton("Refresh Token", callback_data="refresh_token"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await loading_message.edit_text("Chọn định dạng trả lời:", reply_markup=reply_markup)
    
    return ASK_RESPONSE_TYPE

async def handle_response(update: Update, context):
    """Xử lý định dạng trả lời (text hay audio) và gọi API Gemini."""
    query = update.callback_query
    await query.answer()
    response_data = query.data

    # Kiểm tra token phiên đã hết hạn hay chưa
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

    is_initial = response_data in ["text", "audio"]

    # Ẩn inline keyboard của tin nhắn gốc
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    question = context.user_data.get("question", "")
    lang = context.user_data.get("lang", "en")

    total_used_tokens = context.user_data.get("total_used_tokens", 0)
    truncated_question = truncate_text(question)
    input_tokens = estimate_tokens(truncated_question)
    if total_used_tokens + input_tokens > MAX_TOKENS:
        await query.edit_message_text("Bạn đã hết số token cho phép trong hội thoại này.")
        return ConversationHandler.END

    # Sử dụng API Gemini của người dùng (nếu đã đăng nhập và có API riêng)
    user_credentials = context.user_data.get("user_credentials", {})
    user_api_key = user_credentials.get("gemini_api", GEMINI_API_KEY)
    genai.configure(api_key=str(user_api_key))

    # Nếu chưa có phản hồi từ Gemini, gọi API
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

    # Xử lý định dạng trả lời theo yêu cầu
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
             InlineKeyboardButton("Refresh Token", callback_data="refresh_token")]])
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Phản hồi bằng audio đã gửi. Nếu muốn xem văn bản, bấm nút dưới đây:",
            reply_markup=keyboard
        )

    if is_initial:
        if total_used_tokens < MAX_TOKENS:
            await context.bot.send_message(chat_id=query.message.chat_id, text="Bạn có thể đặt câu hỏi tiếp theo:")
            return ASK_RESPONSE_TYPE
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text="Bạn đã hết token cho hội thoại này. Vui lòng khởi động lại bot.")
            return ConversationHandler.END
    else:
        return ASK_RESPONSE_TYPE

# ============================
# MAIN: KHỞI TẠO BOT VÀ THÊM HANDLER
# ============================

def main():
    app = Application.builder().token(TELE_TOKEN).build()

    # ConversationHandler cho xác thực (đăng nhập/đăng ký)
    auth_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_auth)],
        states={
            AUTH_CHOICE: [CallbackQueryHandler(auth_choice)],
            REGISTER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_id)],
            REGISTER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_password)],
            REGISTER_GEMINI: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_gemini)],
            LOGIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_id)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[],
        allow_reentry=True  
    )
    app.add_handler(auth_handler)

    # ConversationHandler cho phần hỏi đáp với API Gemini (yêu cầu người dùng đã đăng nhập)
    qa_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_response_type)],
        states={
            ASK_RESPONSE_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_response_type),
                CallbackQueryHandler(handle_response)
            ]
        },
        fallbacks=[],
        allow_reentry=True  
    )
    app.add_handler(qa_handler)

    app.run_polling()

if __name__ == "__main__":
    main()
