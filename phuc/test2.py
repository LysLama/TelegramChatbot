import os
import asyncio
import re
from edge_tts import Communicate

VALID_VOICES = ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"]

async def text_to_speech(text, voice, output_file):
    if voice not in VALID_VOICES:
        voice = "vi-VN-HoaiMyNeural"
    tts = Communicate(text, voice)
    await tts.save(output_file)

def split_text_into_chunks(text, words_per_chunk=20):
    words = re.findall(r'\S+|\n', text)
    chunks, current_chunk = [], []
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
    temp_files = []
    
    for i, chunk in enumerate(chunks):
        chunk_file = f"chunk_{i}.mp3"
        await text_to_speech(chunk, voice, chunk_file)
        temp_files.append(chunk_file)

    # Ghép file bằng ffmpeg
    with open("file_list.txt", "w", encoding="utf-8") as f:
        for file in temp_files:
            f.write(f"file '{file}'\n")
    
    os.system(f"ffmpeg -f concat -safe 0 -i file_list.txt -c copy {output_file}")

    # Xóa các file tạm
    for file in temp_files:
        os.remove(file)
    os.remove("file_list.txt")

def run_tts(input_text, voice, is_save=False, save_path="output.mp3"):
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
run_tts(text, voice, is_save=True, save_path="test_file/output.mp3")
