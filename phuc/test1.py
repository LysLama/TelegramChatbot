from edge_tts import Communicate
import asyncio
import re
from pydub import AudioSegment

VALID_VOICES = ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"]

async def text_to_speech(text, voice, output_file="output.mp3"):
    if voice not in VALID_VOICES:
        voice = "vi-VN-HoaiMyNeural"
    tts = Communicate(text, voice)
    await tts.save(output_file)

def split_text_into_chunks(text, words_per_chunk=20):
    words = re.findall(r'\S+|\n', text)
    chunks = []
    current_chunk = []
    word_count = 0

    for word in words:
        current_chunk.append(word)
        word_count += 1
        if word_count >= words_per_chunk and word.endswith('.'):
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            word_count = 0
        elif word_count >= words_per_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            word_count = 0

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

async def generate_audio_from_chunks(chunks, voice, output_file="output.mp3"):
    audio_segments = []
    for i, chunk in enumerate(chunks):
        chunk_file = f"chunk_{i}.mp3"
        await text_to_speech(chunk, voice, chunk_file)
        audio_segments.append(AudioSegment.from_mp3(chunk_file))

    combined_audio = AudioSegment.empty()
    for segment in audio_segments:
        combined_audio += segment

    combined_audio.export(output_file, format="test_file/mp3")

def run_tts(input_text, voice, is_save=False, save_path="output.wav"):
    chunks = split_text_into_chunks(input_text)
    if is_save:
        asyncio.run(generate_audio_from_chunks(chunks, voice, save_path))
    else:
        asyncio.run(generate_audio_from_chunks(chunks, voice))

# Test
text_link = r"D:\Procj\Thực Tập\chatbot\phuc\text.txt"
with open(text_link, "r", encoding="utf-8") as f:
    text = f.read()
voice = "vi-VN-HoaiMyNeural"
run_tts(text, voice, is_save=True, save_path="test_file/output.wav")