import os
import asyncio
import edge_tts

# 异步语音合成
async def generate_audio(text, output_path, voice="zh-CN-YunxiNeural", rate="+0%", pitch="+0Hz"):
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)

# 对外封装为同步接口
def tts_edge(text, output_path):
    if not text.strip():
        return
    asyncio.run(generate_audio(text, output_path))
    print(f"[TTS] 生成语音：{output_path}")
