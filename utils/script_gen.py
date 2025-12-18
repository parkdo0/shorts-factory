from __future__ import annotations

import json
import os
import re
from typing import List, Dict, Any, Tuple

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold # 안전 설정용
from dotenv import load_dotenv

load_dotenv()

def _configure_gemini() -> None:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API Key가 설정되지 않았습니다.")
    genai.configure(api_key=api_key)

def _build_prompt(topic: str) -> str:
    return (
        "You are a creative short-form script writer.\n"
        "Generate a concise list of 5-7 scenes for a YouTube Shorts video.\n"
        "Return JSON with key 'scenes', each item containing:\n"
        " - voiceover: short narration (<= 25 words)\n"
        " - image_prompt: English prompt optimized for SDXL with camera/lighting details\n"
        f"Topic: {topic}\n"
        "Respond in JSON format only."
    )

def generate_scenes(topic: str, model: str = "models/gemini-flash-latest") -> Tuple[List[Dict[str, Any]], str | None]:
    if not topic.strip():
        return [], "주제가 비어 있습니다."

    try:
        _configure_gemini()
    except Exception as exc:
        return [], f"Gemini 설정 오류: {exc}"

    # 1. 안전 설정: 모든 필터 해제 (BLOCK_NONE)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    # 사용자 키가 1.5/Standard 권한이 없으므로 flash-latest 사용
    target_model = "models/gemini-flash-latest"

    try:
        prompt = _build_prompt(topic)
        gen_model = genai.GenerativeModel(target_model)
        
        # API 호출
        response = gen_model.generate_content(prompt, safety_settings=safety_settings)
        text = response.text if response.parts else ""

        # 디버깅 출력 (터미널 확인용)
        print(f"\n--- [Gemini Raw Response] ---\n{text}\n-----------------------------\n")

        if not text:
            # 2. 비상용 대본 (Gemini가 입을 다물었을 때 프로그램이 죽지 않게 함)
            print("Gemini가 빈 응답을 보냈습니다. 비상용 기본 대본을 사용합니다.")
            return [
                {"voiceover": f"Here is a story about {topic}.", "image_prompt": f"Cinematic shot of {topic}, mysterious atmosphere, 8k"},
                {"voiceover": "It remains a mystery to this day.", "image_prompt": f"Dramatic angle of {topic}, dark background, high contrast"},
                {"voiceover": "What do you think happened?", "image_prompt": f"Abstract representation of {topic}, questions marks, surreal art"}
            ], None

        # JSON 파싱 (마크다운 제거)
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        data = json.loads(text)
        scenes = data.get("scenes", [])
        
        cleaned = []
        for item in scenes:
            v = str(item.get("voiceover", "")).strip()
            i = str(item.get("image_prompt", "")).strip()
            if v and i:
                cleaned.append({"voiceover": v, "image_prompt": i})
        
        if not cleaned:
             return [], "생성된 장면에 내용이 없습니다."
             
        return cleaned, None

    except Exception as exc:
        return [], f"Gemini API 에러 ({target_model}): {exc}"