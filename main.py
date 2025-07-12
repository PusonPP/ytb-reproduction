import os
import time
import random
import subprocess
from collections import deque
from gemini_api import translate_and_generate_tags
from gemini_api import summarize_subtitle
from gemini_api import detect_sensitive_content
from download_video import download_video
from googleapiclient.discovery import build
from process_subtitle_and_voice import process_subtitles
from compose_audio import merge_audio_segments, replace_video_audio
from whisper_utils import extract_audio_from_video, recognize_audio_to_text
import yt_dlp
from gemini_api import model
from compose_audio import get_audio_duration
from compose_audio import merge_music_tracks
from compose_audio import mix_voice_and_music
from voice_generator import tts_edge
from compose_audio import crop_video_by_ratio
from compose_audio import reencode_video

# YouTube API 配置
API_KEY = ''
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# 监控的地区和分类
regions = ["JP", "US", "GB", "DE", "FR", "CA", "AU"]
categories = ["17", "20", "22", "23", "24", "27", "28"]

# YouTube 分类 ID → bilibili 分区 tid 映射
category_tid_map = {
    "17": "21",   # 体育
    "20": "4",    # 游戏
    "22": "5",    # 人物与博客
    "23": "138",  # 搞笑
    "27": "201",  # 教育
    "28": "95"    # 科技
}

recent_video_ids = deque(maxlen=50)  # 记录最近 50 个视频 ID

# 视频队列
video_queue = deque()

# 视频下载目录
download_dir = "downloads"
if not os.path.exists(download_dir):
    os.makedirs(download_dir)

# 获取视频时长（秒）
def get_video_duration(video_url):
    ydl_opts = {
        'quiet': True,
        'cookiesfrombrowser': ('firefox', 'ua6vti8s.default')
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('duration', 0)
    except Exception as e:
        print(f"[错误] 获取视频时长失败: {e}")
        return 0

# 随机获取热门视频
def get_random_video_from_trending():
    region = random.choice(regions)
    category = random.choice(categories)
    print(f"[选择] 地区: {region}, 分类ID: {category}")

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)
    request = youtube.videos().list(
        part="snippet",
        chart="mostPopular",
        regionCode=region,
        videoCategoryId=category,
        maxResults=50 
    )
    try:
        response = request.execute()
    except Exception as e:
        print(f"[异常] API 请求失败：{e}")
        return None, None, None


    if not response.get("items"):
        print(f"[警告] {region}/{category} 没有找到热门视频")
        return None, None, None

    # 打乱顺序
    random.shuffle(response["items"])

    # 避免重复：使用 video_id 缓存
    for video in response["items"]:
        video_id = video["id"]
        if video_id in recent_video_ids:
            print(f"[跳过] 视频 {video_id} 最近已处理过")
            continue

        video_title = video["snippet"]["title"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"[检测] 检查视频：{video_title}")

        duration = get_video_duration(video_url)
        print(f"[时长] {video_title} 时长 {duration} 秒")

        if duration and 60 <= duration <= 10 * 60:
            recent_video_ids.append(video_id)  # 记录已处理
            return video_title, video_url, category  # 返回 3 个值
        else:
            print(f"[跳过] 超过10分钟，重新寻找...")

    return None, None, None  # 保证总返回3个值


# 上传到B站
def post_to_bilibili(video_file, translated_title, description, tags_line, cover_path, source_link, tid="51"):
    if not tags_line:
        tags_line = "YouTube搬运"

    command = [
        "biliup_rs", "upload", video_file,
        "--title", translated_title,
        "--desc", description,
        "--tag", tags_line,
        "--tid", tid,
        "--cover", cover_path,
        "--limit", "1",
        "--copyright", "1",
    ]
    print(f"[DEBUG] 最终投稿命令: {' '.join(command)}")
    subprocess.run(command, check=True)

# 处理队列
def process_queue():
    while video_queue:
        title, video_url, category = video_queue.popleft()
        print(f"[队列] 正在处理新视频：{title}")

        # 下载视频
        video_file_name, cover_file_name, description, source_link = download_video(video_url)
        video_file = os.path.join(download_dir, video_file_name)
        cover_path = os.path.join(download_dir, cover_file_name)

        # ① 下载完先整体转码为 H.264，避免后续 AV1 解码失败
        reencoded_video = os.path.join(download_dir, "reencoded.mp4")
        reencode_video(video_file, reencoded_video)
        video_file = reencoded_video

        # ② 提取字幕
        subtitle_text_vtt, subtitle_text = extract_subtitle_text(video_url, video_file)

        if len(subtitle_text) < 5:
            print(f"[跳过] 字幕过少，重新获取...")
            return

        # ③ Gemini 检测字幕是否正常
        legibility_result = detect_text_legibility(subtitle_text)
        print(f"[语义检测] Gemini 判断为：{legibility_result}")
        if "否" in legibility_result:
            print(f"[跳过] Gemini 判定为异常文字，重新获取...")
            return

        # ④ Gemini 检测是否敏感
        sensitive_result = detect_sensitive_content(subtitle_text)
        print(f"[敏感检测] Gemini 判断为：{sensitive_result}")
        if "是" in sensitive_result:
            print(f"[跳过] Gemini 判定为敏感内容，重新获取...")
            return

        # ⑤ Gemini 总结为完整中文文案
        chinese_text = summarize_subtitle(subtitle_text)

        # ⑥ 合成完整语音
        voice_path = os.path.join(download_dir, "voice.mp3")
        tts_edge(chinese_text, voice_path)

        # ⑦ 调整语音速度以匹配视频时长
        video_duration = get_audio_duration(video_file)
        voice_duration = get_audio_duration(voice_path)
        speed = video_duration / voice_duration
        speed = max(0.7, min(1.3, speed))

        adjusted_voice = os.path.join(download_dir, "voice_adjusted.mp3")
        subprocess.run([
            "ffmpeg", "-y", "-i", voice_path,
            "-filter:a", f"atempo={speed:.3f}",
            adjusted_voice
        ], check=True)

        # ⑧ 拼接背景音乐
        merged_music = merge_music_tracks(music_dir="music", total_duration=video_duration)

        # ⑨ 混音
        final_audio = os.path.join(download_dir, "final_audio.mp3")
        mix_voice_and_music(adjusted_voice, merged_music, final_audio)

        # ⑩ 计算裁剪比例 & 裁剪视频
        final_audio_duration = get_audio_duration(final_audio)
        crop_ratio = final_audio_duration / video_duration
        crop_ratio = min(1.0, max(0.2, crop_ratio))

        crop_target_duration = video_duration * crop_ratio

        cropped_video = os.path.join(download_dir, "video_cropped.mp4")
        crop_video_by_ratio(video_file, crop_target_duration, cropped_video)

        # ⑪ 替换音轨
        new_video = os.path.join(download_dir, "video_new.mp4")
        replace_video_audio(cropped_video, final_audio, new_video)
        video_file = new_video

        # ⑫ Gemini 生成标题 & 标签
        translated_data = translate_and_generate_tags(title)
        print(f"[DEBUG] Gemini 原始返回:\n{translated_data}")
        lines = [line.strip() for line in translated_data.strip().splitlines() if line.strip()]
        if len(lines) < 2:
            raise ValueError(f"Gemini API 返回格式不正确:\n{translated_data}")

        translated_title = lines[0].replace("翻译：", "").strip()
        tags_line = lines[1].replace("标签：", "").strip() or "YouTube搬运"

        # ⑬ 简介
        full_description = chinese_text + "\n" + source_link

        print(f"[DEBUG] 生成的标题: {translated_title}")
        print(f"[DEBUG] 最终标签: {tags_line}")
        print(f"[DEBUG] 视频简介: {full_description}")
        print(f"[DEBUG] 原视频链接: {source_link}")

        # ⑭ 上传到 B 站
        tid = category_tid_map.get(category, "51")
        post_to_bilibili(video_file, translated_title, full_description, tags_line, cover_path, source_link, tid)

        # ⑮ 清理
        os.remove(video_file)
        os.remove(cover_path)
        try:
            for file in os.listdir(download_dir):
                os.remove(os.path.join(download_dir, file))
            print(f"[清理] 已清空 downloads 目录")
        except Exception as e:
            print(f"[清理异常] 删除文件时出错: {e}")

        print(f"[完成] 已上传 {translated_title}，并删除本地文件。")




# 每次获取一个新视频
def check_for_new_videos():
    while True:  # 如果不符合要求，重新获取
        title, video_url, category = get_random_video_from_trending()
        if not video_url:
            print(f"[警告] 未找到符合要求的视频")
            return

        print(f"[检测] 选中的新视频：{title}, 链接：{video_url}")
        
        video_queue.append((title, video_url, category))
        print(f"[排队] 已加入搬运队列：{title}")
        break  # 找到符合要求的视频就退出循环


# 提取字幕文本
def extract_subtitle_text(video_url, video_file):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'writesubtitles': True,
        'subtitlesformat': 'vtt',
        'subtitleslangs': ['en', 'ja', 'zh-Hans', 'zh-Hant'],
        'outtmpl': os.path.join(download_dir, '%(id)s.%(ext)s'),
        'cookiesfrombrowser': ('firefox', 'ua6vti8s.default'),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)

    video_id = info.get('id')
    subtitle_path = os.path.join(download_dir, f"{video_id}.en.vtt")
    if not os.path.exists(subtitle_path):
        subtitle_path = os.path.join(download_dir, f"{video_id}.ja.vtt")
    if not os.path.exists(subtitle_path):
        subtitle_path = os.path.join(download_dir, f"{video_id}.zh-Hans.vtt")
    if not os.path.exists(subtitle_path):
        subtitle_path = os.path.join(download_dir, f"{video_id}.zh-Hant.vtt")

    # 如果有字幕，读取
    if os.path.exists(subtitle_path):
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        texts = [line.strip() for line in lines if '-->' not in line and not line.strip().isdigit() and line.strip()]
        subtitle_text = ' '.join(texts)
        print(f"[字幕] 提取到 {len(subtitle_text)} 个字符")
        return subtitle_text

    # 否则自动识别
    print("[无字幕] 尝试用 Whisper 识别...")
    audio_path = extract_audio_from_video(video_file)
    subtitle_text_vtt, full_text = recognize_audio_to_text(audio_path)
    print(f"[Whisper] 识别到 {len(full_text)} 个字符")

    # 保存生成的 vtt 文件
    whisper_sub_path = os.path.join(download_dir, f"{video_id}.whisper.vtt")
    with open(whisper_sub_path, 'w', encoding='utf-8') as f:
        f.write(subtitle_text_vtt)

    return subtitle_text_vtt, full_text

def detect_text_legibility(subtitle_text: str):
    prompt = f"""
请判断以下内容是否为完整、可理解的人类自然语言文字，不是乱码、重复无意义的片段或错误识别的内容。
只回答“是”或“否”，不需要解释原因：
{subtitle_text}
"""
    response = model.generate_content(prompt)
    return response.text.strip()

# 主循环
def main():
    while True:
        try:
            check_for_new_videos()
            process_queue()
        except Exception as e:
            print(f"[异常] 处理过程中出错: {e}")
        print("[等待] 30 分钟后继续...")
        time.sleep(30 * 60)

if __name__ == "__main__":
    main()
