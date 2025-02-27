from edge_tts import Communicate
import asyncio

VALID_VOICES = ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"]

# Hàm TTS 
async def text_to_speech(text, voice, output_file="output.mp3"):
    if voice not in VALID_VOICES:
        voice = "vi-VN-HoaiMyNeural"  # mặc định
    tts = Communicate(text, voice)
    await tts.save(output_file)

def run_tts(input_text, voice, is_save=False, save_path="output.wav"):
    if is_save:
        asyncio.run(text_to_speech(input_text, voice, save_path))
    else:
        asyncio.run(text_to_speech(input_text, voice))

#test
text = "Xin chào, tôi là chatbot"
voice = "vi-VN-HoaiMyNeural"
run_tts(text, voice, is_save=True, save_path="output.wav")