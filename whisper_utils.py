import os
import subprocess
from faster_whisper import WhisperModel

# 从视频提取音频为 wav 格式
def extract_audio_from_video(video_path, output_wav="downloads/audio.wav"):
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",  # 单声道
        output_wav
    ], check=True)
    return output_wav

# 使用 Whisper 识别音频为字幕文本
def recognize_audio_to_text(audio_path):
    model = WhisperModel("base", device="cpu")
    segments, _ = model.transcribe(audio_path)

    subtitle_lines = []
    pure_text = []
    for segment in segments:
        # 生成 vtt 格式
        start = format_timestamp(segment.start)
        end = format_timestamp(segment.end)
        subtitle_lines.append(f"{start} --> {end}")
        subtitle_lines.append(segment.text)
        subtitle_lines.append("")
        pure_text.append(segment.text)

    # 输出字幕和纯文本
    subtitle_text = "\n".join(subtitle_lines)
    full_text = " ".join(pure_text)
    return subtitle_text, full_text

# 格式化时间为 vtt 标准
def format_timestamp(seconds):
    ms = int((seconds - int(seconds)) * 1000)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
