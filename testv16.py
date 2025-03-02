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
    ContextTypes,
)
import google.generativeai as genai
from langdetect import detect, LangDetectException

# ============================
# CẤU HÌNH VÀ ĐỊNH NGHĨA TOÀN CỤC
# ============================

# Đường dẫn thư mục chứa file ngôn ngữ
SAVE_DIR = "./data"  # Thay đổi nếu cần
LANG_DIR = os.path.join(SAVE_DIR, "lang")
os.makedirs(LANG_DIR, exist_ok=True)

# Hàm tải ngôn ngữ
def load_language(language_code):
    """Đọc dữ liệu ngôn ngữ từ file JSON."""
    lang_file = os.path.join(LANG_DIR, f"lang_{language_code}.json")
    try:
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Không tìm thấy file ngôn ngữ cho {language_code}. Dùng tiếng Anh mặc định.")
        return load_language("en")  # Mặc định tiếng Anh nếu không tìm thấy
    except Exception as e:
        print(f"Lỗi đọc file ngôn ngữ: {e}")
        return {}

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
CHOOSE_LANGUAGE, AUTH_CHOICE, REGISTER_ID, REGISTER_PASSWORD, REGISTER_GEMINI, LOGIN_ID, LOGIN_PASSWORD = range(10, 17)

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

async def auto_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Chỉ được kích hoạt khi người dùng gửi lệnh /start.
    Nếu chưa đăng nhập, hiển thị chọn ngôn ngữ.
    Nếu đã đăng nhập, chuyển trực tiếp sang phần hỏi đáp Q&A.
    """
    if not context.user_data.get("authenticated"):
        # Hiển thị chọn ngôn ngữ
        supported_languages = {
            "en": "English",
            "vi": "Tiếng Việt",
            "ms": "Malaysia"
        }
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"lang_{code}")]
            for code, name in supported_languages.items()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Vui lòng chọn ngôn ngữ / Please select your language:",
            reply_markup=reply_markup
        )
        return CHOOSE_LANGUAGE
    else:
        return await ask_response_type(update, context)

async def choose_language(update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        language_code = query.data.split("_")[1]
        context.user_data["language"] = language_code
        
        translation = load_language(language_code)
        
        keyboard = [
            [InlineKeyboardButton(translation["login"], callback_data="login"),
             InlineKeyboardButton(translation["register"], callback_data="register")]
        ]
        
        await  query.edit_message_text(
            f"{translation['welcome']}\n{translation['choose_option']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AUTH_CHOICE
    except Exception as e:
        print(f"Lỗi trong choose_language: {str(e)}")
        await update.callback_query.message.reply_text("Đã xảy ra lỗi. Vui lòng thử lại.")
        return ConversationHandler.END

async def start_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lựa chọn ngôn ngữ."""
    query = update.callback_query
    await query.answer()
    language_code = query.data.split("_")[1]  # Lấy "en" hoặc "vi" từ "lang_en", "lang_vi"
    context.user_data["language"] = language_code
    
    # Tải ngôn ngữ
    translation = load_language(language_code)

    """Lệnh /start hoặc callback từ nút 'Đăng nhập / Đăng ký': Hiển thị lựa chọn đăng nhập hay đăng ký."""
    keyboard = [
        [
            InlineKeyboardButton(translation["login"], callback_data="login"),
            InlineKeyboardButton(translation["register"], callback_data="register"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Kiểm tra xem update đến từ message hay callback query
    if update.message:
        await update.message.reply_text(f"{translation['welcome']}\n{translation['choose_option']}", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.answer()  # Trả lời callback query
        await update.callback_query.edit_message_text(f"{translation['welcome']}\n{translation['choose_option']}", reply_markup=reply_markup)
    return AUTH_CHOICE

async def auth_choice(update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lựa chọn đăng nhập/đăng ký."""
    query = update.callback_query
    await query.answer()
    choice = query.data
    translation = load_language(context.user_data.get("language", "en"))
    
    if choice == "login":
        await query.edit_message_text(f"{translation['login']}:\n{translation['enter_id']}")
        return LOGIN_ID
    elif choice == "register":
        await query.edit_message_text(f"{translation['register']}:\n{translation['enter_id']}")
        return REGISTER_ID

async def register_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    translation = load_language(context.user_data.get("language", "en"))

    """Nhận ID người dùng trong quá trình đăng ký."""
    user_id = update.message.text.strip()
    users = load_users_data()
    if user_id in users:
        await update.message.reply_text(translation["id_exists"])
        return ConversationHandler.END
    context.user_data["reg_id"] = user_id
    await update.message.reply_text(translation["enter_password"])
    return REGISTER_PASSWORD

async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    translation = load_language(context.user_data.get("language", "en"))
    """Nhận mật khẩu của người dùng trong quá trình đăng ký."""
    password = update.message.text.strip()
    context.user_data["reg_password"] = password
    await update.message.reply_text(translation["enter_api"])
    return REGISTER_GEMINI

async def register_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    translation = load_language(context.user_data.get("language", "en"))
    gemini_api = update.message.text.strip()
    user_id = context.user_data.get("reg_id")
    password = context.user_data.get("reg_password")
    
    hashed_pass = hash_password(password)
    
    users = load_users_data()
    users[user_id] = {
        "hashed_password": hashed_pass.decode("utf-8"),
        "gemini_api": gemini_api
    }
    save_users_data(users)
    
    context.user_data["authenticated"] = True
    context.user_data["user_credentials"] = {
        "id": user_id,
        "gemini_api": gemini_api
    }
    context.user_data["session_token"] = generate_session_token()
    context.user_data["total_used_tokens"] = 0
    await update.message.reply_text(translation["register_success"])
    # Prompt the user to ask a question
    await update.message.reply_text(translation.get("ask_question", "Please type your question:"))
    return ASK_RESPONSE_TYPE

async def login_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    translation = load_language(context.user_data.get("language", "en"))
    """Nhận ID người dùng trong quá trình đăng nhập."""
    user_id = update.message.text.strip()
    context.user_data["login_id"] = user_id
    await update.message.reply_text(translation["enter_password"])
    return LOGIN_PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    translation = load_language(context.user_data.get("language", "en"))
    password = update.message.text.strip()
    user_id = context.user_data.get("login_id")
    users = load_users_data()
    
    if user_id not in users:
        await update.message.reply_text(translation["id_not_exists"])
        return ConversationHandler.END
    
    stored_hash = users[user_id]["hashed_password"].encode("utf-8")
    if check_password(password, stored_hash):
        gemini_api = users[user_id]["gemini_api"]
        context.user_data["authenticated"] = True
        context.user_data["user_credentials"] = {
            "id": user_id,
            "gemini_api": gemini_api
        }
        context.user_data["session_token"] = generate_session_token()
        context.user_data["total_used_tokens"] = 0
        await update.message.reply_text(translation["login_success"])
        # Prompt the user to ask a question
        await update.message.reply_text(translation.get("ask_question", "Please type your question:"))
        return ASK_RESPONSE_TYPE
    else:
        await update.message.reply_text(translation["wrong_password"])
        return ConversationHandler.END

# ============================
# PHẦN GIAO TIẾP VỚI API GEMINI (Q&A)
# ============================

async def ask_response_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    translation = load_language(context.user_data.get("language", "en"))

    """Xử lý câu hỏi sau khi đã đăng nhập"""
    # Kiểm tra lại trạng thái đăng nhập
    if not context.user_data.get("authenticated"):
        return await auto_start(update, context)

    question = update.message.text
    context.user_data["question"] = question
    context.user_data.pop("gemini_response", None)

    # Gia hạn hoặc khởi tạo token phiên
    if "session_token" not in context.user_data:
        context.user_data["session_token"] = generate_session_token()
    else:
        context.user_data["session_token"]["expires_at"] = time.time() + TOKEN_LIFETIME

    loading_message = await update.message.reply_text(translation["processing_question"])
    try:
        detect_lang = detect(question)
        context.user_data["detected_lang"] = detect_lang
    except LangDetectException:
        detect_lang = "en"
        context.user_data["detected_lang"] = detect_lang

    keyboard = [
        [
            InlineKeyboardButton("Text", callback_data="text"),
            InlineKeyboardButton("Audio", callback_data="audio"),
            InlineKeyboardButton("Refresh Token", callback_data="refresh_token"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await loading_message.edit_text(translation["choose_format"], reply_markup=reply_markup)
    
    return ASK_RESPONSE_TYPE

# Xử lý định dạng trả lời (text hay audio) và gọi API Gemini.
async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    translation = load_language(context.user_data.get("language", "en"))

    query = update.callback_query
    await query.answer()
    response_data = query.data

    # Kiểm tra token phiên đã hết hạn hay chưa
    session_token = context.user_data.get("session_token", {})
    if session_token.get("expires_at", 0) < time.time():
        await query.edit_message_text(translation["session_format"])
        return ASK_RESPONSE_TYPE

    if response_data == "refresh_token":
        context.user_data["session_token"] = generate_session_token()
        context.user_data["total_used_tokens"] = 0
        await query.edit_message_text(
            text=translation["token_refreshed"],
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
    detected_lang = context.user_data.get("detected_lang", "en")

    total_used_tokens = context.user_data.get("total_used_tokens", 0)
    truncated_question = truncate_text(question)
    input_tokens = estimate_tokens(truncated_question)
    if total_used_tokens + input_tokens > MAX_TOKENS:
        await query.edit_message_text(translation["token_over"])
        return ConversationHandler.END

    # Sử dụng API Gemini của người dùng
    user_credentials = context.user_data.get("user_credentials", {})
    user_api_key = user_credentials.get("gemini_api", GEMINI_API_KEY)
    genai.configure(api_key=str(user_api_key))

    if "gemini_response" not in context.user_data:
        loading_temp = await context.bot.send_message(chat_id=query.message.chat_id, text=translation["fetching_api"])
        model = genai.GenerativeModel("gemini-exp-1206")
        try:
            response = model.generate_content(truncated_question, generation_config={"max_output_tokens": MAX_TOKENS})
            response_text = response.text.strip() if hasattr(response, "text") else translation["cannot_generate"]
            response_text = response_text.replace('*', '')
            output_tokens = estimate_tokens(response_text)
            total_used_tokens += input_tokens + output_tokens
            context.user_data["total_used_tokens"] = total_used_tokens
            # Thêm thông tin token vào phản hồi
            response_text += f"\n\n🔹 {translation['used_token']} {total_used_tokens}/{MAX_TOKENS}"
            context.user_data["gemini_response"] = response_text
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=loading_temp.message_id)
            except Exception as e:
                print(f"{translation['cannot_delete']}, {e}")
        except Exception as e:
            await query.edit_message_text(f"Lỗi: {str(e)}")
            return ConversationHandler.END
    else:
        response_text = context.user_data["gemini_response"]

    # Xử lý định dạng trả lời theo yêu cầu:
    # --- Nhóm xử lý text (và convert_text)
    if response_data in ["text", "convert_text"]:
        # Nếu người dùng chọn xem text thì loại bỏ thông tin token khỏi nội dung
        if response_data == "convert_text" and "🔹" in response_text:
            response_text = response_text.split("🔹")[0].strip()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(translation["hear_audio"], callback_data="convert_audio"),
             InlineKeyboardButton("Refresh Token", callback_data="refresh_token")]
        ])
        try:
            await query.edit_message_text(text=response_text, reply_markup=keyboard)
        except Exception:
            await context.bot.send_message(chat_id=query.message.chat_id, text=response_text, reply_markup=keyboard)
    
    # --- Nhóm xử lý audio (và convert_audio)
    elif response_data in ["audio", "convert_audio"]:
        try:
            await query.edit_message_text(text=translation["sending_audio"])
        except Exception:
            pass
        tts_text = remove_urls(response_text)
        # Loại bỏ thông tin token nếu có trong nội dung chuyển giọng nói
        if "🔹" in tts_text:
            tts_text = tts_text.split("🔹")[0].strip()
        tts_lang = "vi" if detected_lang == "vi" else "en"
        audio_path = os.path.join(SAVE_DIR, f"response_{uuid.uuid4()}.mp3")
        try:
            tts = gTTS(tts_text, lang=tts_lang, slow=False)
            tts.save(audio_path)
        except Exception as e:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"{translation['audio_error']}, {str(e)}")
            return ConversationHandler.END
        with open(audio_path, "rb") as audio_file:
            await context.bot.send_voice(chat_id=query.message.chat_id, voice=audio_file)
        asyncio.create_task(delete_file_after_delay(audio_path))
        # Xây dựng tin nhắn kết hợp: token hiển thị ở trên cùng, sau đó là thông báo audio đã gửi
        token_info = f"🔹 {translation['used_token']} {total_used_tokens}/{MAX_TOKENS}"
        combined_message = f"{token_info}\n{translation['audio_sent']}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(translation["show_text"], callback_data="convert_text"),
             InlineKeyboardButton("Refresh Token", callback_data="refresh_token")]
        ])
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=combined_message,
            reply_markup=keyboard
        )

    # Nếu là lần đầu tiên trả lời (is_initial), hỏi tiếp nếu token chưa hết
    if is_initial:
        if total_used_tokens < MAX_TOKENS:
            await context.bot.send_message(chat_id=query.message.chat_id, text=translation["ask_next"])
            return ASK_RESPONSE_TYPE
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text=translation["chat_over"])
            return ConversationHandler.END
    else:
        return ASK_RESPONSE_TYPE

# ============================
# MAIN: KHỞI TẠO BOT VÀ THÊM HANDLER
# ============================

def main():

    app = Application.builder().token(TELE_TOKEN).build()
    # ConversationHandler chính xử lý xác thực và Q&A.
    conv_handler = ConversationHandler(
        entry_points=[
            # Chỉ khởi tạo bằng lệnh /start, không bắt mọi tin nhắn văn bản.
            CommandHandler("start", auto_start)
        ],
        states={
            CHOOSE_LANGUAGE: [CallbackQueryHandler(choose_language, pattern=r"^lang_")],
            AUTH_CHOICE: [CallbackQueryHandler(auth_choice, pattern=r"^(login|register)$")],
            REGISTER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_id)],
            REGISTER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_password)],
            REGISTER_GEMINI: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_gemini)],
            LOGIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_id)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
            ASK_RESPONSE_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_response_type),
                CallbackQueryHandler(handle_response)
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
