import os
from google import generativeai

# 初始化 Gemini
api_key = os.getenv("GEMINI_API_KEY")
generativeai.configure(api_key=api_key)
model = generativeai.GenerativeModel('gemini-1.5-pro')

def translate_and_generate_tags(title_en: str):
    prompt = f"""
请把以下视频标题翻译为中文，要使标题足够具备吸引力。，标题最多不要超过70个字。并为这个视频生成10个合适的中文标签，标签用英文逗号隔开，每个标题不能超过8个字。
标题：{title_en}

输出格式：
翻译：<翻译后的中文标题>
标签：<标签1>, <标签2>, <标签3>, <标签4>, <标签5>, <标签6>, <标签7>, <标签8>, <标签9>, <标签10>
"""
    response = model.generate_content(prompt)
    return response.text

def detect_sensitive_content(subtitle_text: str):
    prompt = f"""
请判断以下文案是否有涉及到侮辱讽刺中华人民共和国或中国共产党的情节，只回答“是”或“否”，不要解释原因：
{subtitle_text}
"""
    response = model.generate_content(prompt)
    return response.text.strip()

def translate_sentence(text: str):
    prompt = f"用解说的语气把下面这段视频字幕总结成地道的中文，需要做到足够吸引人但不要偏离原文意思。你只需要回复纯文本内容和正常的标点符号（逗号、句号等），不要带任何其他符号：{text}"
    response = model.generate_content(prompt)
    return response.text.strip()

def summarize_subtitle(subtitle_text: str):
    prompt = f"""
用解说的语气把下面这段视频字幕总结成地道的中文，需要做到足够吸引人但不要偏离原文意思。你只需要回复纯文本内容和正常的标点符号（逗号、句号等），不要带任何其他符号，不要逐句翻译，不要保留字幕格式：
{subtitle_text}
"""
    response = model.generate_content(prompt)
    return response.text.strip()
