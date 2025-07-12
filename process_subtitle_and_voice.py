import os
import re
from gemini_api import translate_sentence
from voice_generator import tts_edge

# 翻译并逐句生成语音
def process_subtitles(subtitle_text, voice_dir="voice"):
    if not os.path.exists(voice_dir):
        os.makedirs(voice_dir)

    subtitles = parse_vtt(subtitle_text)
    voice_segments = []

    all_translated_texts = []
    for i, (start, end, text) in enumerate(subtitles):
        translated = translate_sentence(text)
        all_translated_texts.append(translated)
        print(f"[翻译] {text} -> {translated}")
        output_path = os.path.join(voice_dir, f"{i:04d}.mp3")

        # 语音合成
        tts_edge(translated, output_path)
        voice_segments.append((start, end, output_path))

    return voice_segments, "\n".join(all_translated_texts)

# 解析 vtt 格式
def parse_vtt(subtitle_text):
    pattern = re.compile(r"(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})")
    lines = subtitle_text.splitlines()

    subtitles = []
    cur_start, cur_end = None, None
    cur_text = []

    for line in lines:
        match = pattern.match(line)
        if match:
            if cur_text:
                subtitles.append((cur_start, cur_end, ' '.join(cur_text)))
                cur_text = []
            cur_start, cur_end = match.group(1), match.group(2)
        elif line.strip() and not line.strip().isdigit():
            cur_text.append(line.strip())

    if cur_text:
        subtitles.append((cur_start, cur_end, ' '.join(cur_text)))

    return subtitles
