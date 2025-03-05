import os
os.environ["FFMPEG_BINARY"] = r"D:\ffmpeg\bin\ffmpeg.exe"  # Đảm bảo đường dẫn này là chính xác
from pydub import AudioSegment
AudioSegment.converter = os.environ["FFMPEG_BINARY"]

# In ra đường dẫn để xác nhận
print("Đường dẫn ffmpeg: ", AudioSegment.converter)

try:
    # Giả sử bạn có file test.ogg trong cùng thư mục với script
    audio = AudioSegment.from_file("test.ogg", format="ogg")
    audio.export("test.wav", format="wav")
    print("Chuyển đổi thành công!")
except Exception as e:
    print("Lỗi khi chuyển đổi:", e)
