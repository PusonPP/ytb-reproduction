import subprocess
import os
import random

# 拼接语音片段
def merge_audio_segments(voice_segments, output_audio="downloads/voice_merged.mp3"):
    list_file = "downloads/voice_list.txt"
    with open(list_file, 'w', encoding='utf-8') as f:
        for _, _, path in voice_segments:
            f.write(f"file '{os.path.abspath(path)}'\n")

    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_audio], check=True)
    print(f"[合成] 语音合成完成：{output_audio}")
    return output_audio

# 拼接背景音乐
def merge_music_tracks(music_dir="music", total_duration=60, output_audio="downloads/music_merged.mp3"):
    music_files = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith(".mp3")]
    if not music_files:
        raise FileNotFoundError("music/ 目录下没有背景音乐")

    random.shuffle(music_files)
    select_files = music_files[:2]

    concat_file = "downloads/music_list.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        for file in select_files:
            f.write(f"file '{os.path.abspath(file)}'\n")

    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_audio], check=True)

    # 截断为与语音时长一致
    truncated_audio = output_audio.replace(".mp3", "_cut.mp3")
    subprocess.run(["ffmpeg", "-y", "-i", output_audio, "-t", str(total_duration), "-c", "copy", truncated_audio], check=True)

    print(f"[合成] 背景音乐完成：{truncated_audio}")
    return truncated_audio

# 混音
def mix_voice_and_music(voice_audio, music_audio, output_audio="downloads/final_audio.mp3"):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", voice_audio,
        "-i", music_audio,
        "-filter_complex", "[1:a]volume=0.4[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=3",
        "-c:a", "mp3",
        output_audio
    ], check=True)
    print(f"[合成] 混音完成：{output_audio}")
    return output_audio

# 替换视频音轨
def replace_video_audio(input_video, new_audio, output_video):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_video,
        "-i", new_audio,
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_video
    ], check=True)

    print(f"[完成] 替换音轨完成：{output_video}")


def get_audio_duration(audio_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        duration = float(result.stdout.strip())
        print(f"[音频时长] {audio_path}: {duration:.2f} 秒")
        return duration
    except Exception as e:
        print(f"[错误] 获取音频时长失败: {e}")
        return 0

def merge_music_tracks(music_dir="music", total_duration=60, output_audio="downloads/music_merged.mp3"):
    music_files = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith(".mp3")]
    if not music_files:
        raise FileNotFoundError("[错误] music 目录下未找到 mp3 文件")

    random.shuffle(music_files)

    # 随机选择 1~2 个音频拼接
    selected_files = music_files[:2] if len(music_files) >= 2 else music_files

    concat_list = "downloads/music_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for file in selected_files:
            f.write(f"file '{os.path.abspath(file)}'\n")

    merged_path = output_audio.replace(".mp3", "_full.mp3")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", merged_path], check=True)

    # 截取为语音时长
    truncated_path = output_audio
    subprocess.run(["ffmpeg", "-y", "-i", merged_path, "-t", str(total_duration), "-c", "copy", truncated_path], check=True)

    print(f"[合成] 背景音乐完成：{truncated_path}")
    return truncated_path

def mix_voice_and_music(voice_audio, music_audio, output_audio="downloads/final_audio.mp3"):
    # 音乐音量调为 0.4，语音保持原始音量
    subprocess.run([
        "ffmpeg", "-y",
        "-i", voice_audio,
        "-i", music_audio,
        "-filter_complex",
        "[0:a]volume=2.5[voice];[1:a]volume=0.2[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=3",
        "-c:a", "mp3",
        output_audio
    ], check=True)

    print(f"[合成] 混音完成：{output_audio}")
    return output_audio

def crop_video_by_ratio(input_video, target_duration, output_video):
    # 获取原视频总时长
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", input_video],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    total_duration = float(result.stdout.strip())
    print(f"[原视频时长] {total_duration:.2f} 秒")

    if target_duration >= total_duration:
        print("[提示] 目标时长 ≥ 原视频，无需裁剪")
        subprocess.run(["ffmpeg", "-y", "-i", input_video, "-c:v", "copy", "-an", output_video], check=True)
        return

    block_size = 5  # 每段 5 秒
    segments = []
    current = 0

    # 交替保留和跳过
    while current < total_duration:
        start = current
        end = min(current + block_size, total_duration)
        segments.append((start, end))
        current += block_size

    # 保留间隔：每隔一段保留一段
    keep_segments = []
    accumulated = 0
    toggle = True

    for start, end in segments:
        seg_len = end - start
        if toggle:
            keep_segments.append((start, end))
            accumulated += seg_len
            if accumulated >= target_duration:
                break
        toggle = not toggle  # 交替保留 / 跳过

    print(f"[保留片段] {keep_segments}")

    # 单独裁剪每一段
    temp_files = []
    for i, (start, end) in enumerate(keep_segments):
        temp_file = f"/tmp/clip_{i}.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", input_video,
            "-ss", str(start),
            "-to", str(end),
            "-c:v", "libx264",
            "-preset", "fast",
            "-an",  # 去掉原音轨
            temp_file
        ], check=True)
        temp_files.append(temp_file)

    # 合并
    concat_list = "/tmp/concat_list.txt"
    with open(concat_list, "w") as f:
        for temp_file in temp_files:
            f.write(f"file '{temp_file}'\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list,
        "-c:v", "libx264",
        "-preset", "fast",
        "-an",
        output_video
    ], check=True)

    print(f"[完成] 裁剪完成：{output_video}")

    # 清理
    for temp_file in temp_files:
        os.remove(temp_file)
    os.remove(concat_list)

def reencode_video(input_video, output_video):
    subprocess.run([
        "ffmpeg", "-y", "-i", input_video,
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_video
    ], check=True)

