import os
import asyncio
import uuid
from dotenv import load_dotenv
load_dotenv()
from gtts import gTTS
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
import google.generativeai as genai

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Telegram Bot Token
TOKEN = os.getenv("TOKEN")
SAVE_DIR = "./data"
os.makedirs(SAVE_DIR, exist_ok=True)

# Conversation states
ASK_RESPONSE_TYPE, HANDLE_RESPONSE = range(2)

async def delete_file_after_delay(file_path: str, delay: int = 3600):
    """Deletes the file after a specified delay."""
    await asyncio.sleep(delay)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted: {file_path}")

async def start(update: Update, context):
    """Start command handler."""
    await update.message.reply_text("Send me your question:")
    return ASK_RESPONSE_TYPE  # Move to asking response type

async def ask_response_type(update: Update, context):
    """Store the user's question and ask for response type."""
    context.user_data["question"] = update.message.text  # Store the question
    await update.message.reply_text("Do you want the response in Text or Audio?")
    return HANDLE_RESPONSE  # Move to handling response

async def handle_response(update: Update, context):
    """Generate response based on user choice of text or audio."""
    response_type = update.message.text.lower()
    
    if response_type not in ["text", "audio"]:
        await update.message.reply_text("Please choose 'Text' or 'Audio'!")
        return HANDLE_RESPONSE  # Stay in the same state until valid input

    question = context.user_data.get("question", "No question found.")  # Retrieve stored question
    
    # Generate response using Gemini API
    model = genai.GenerativeModel("gemini-pro")
    try:
        response = model.generate_content(question)
        response_text = response.text.strip() if hasattr(response, "text") else "Sorry, I couldn't generate a response."
    except Exception as e:
        response_text = f"Error generating response: {str(e)}"

    if response_type == "audio":
        audio_path = os.path.join(SAVE_DIR, f"response_{uuid.uuid4()}.mp3")
        tts = gTTS(response_text, lang="en")
        tts.save(audio_path)
        await update.message.reply_voice(voice=open(audio_path, "rb"))
        asyncio.create_task(delete_file_after_delay(audio_path))
    else:
        await update.message.reply_text(response_text)

    return ConversationHandler.END  # End the conversation

def main():
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_RESPONSE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_response_type)],
            HANDLE_RESPONSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_response)]
        },
        fallbacks=[]
    )
    
    app.add_handler(conv_handler)
    
    app.run_polling()

if __name__ == "__main__":
    main()
