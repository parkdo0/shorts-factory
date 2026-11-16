import os
from typing import List, Dict

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


def configure_gemini(api_key: str = None, model_name: str = "gemini-1.5-flash") -> None:
    """Gemini API 키 설정."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise EnvironmentError("Gemini API 키가 없습니다. UI나 GEMINI_API_KEY 환경변수로 설정하세요.")
    genai.configure(api_key=key)
    return model_name


def build_director_prompt(keyword: str) -> str:
    """감독 역할 프롬프트를 구성."""
    return (
        "당신은 Expert Visual Director입니다. 주어진 한국어 주제로 JSON 배열의 씬을 만드세요. "
        "각 씬은 voiceover(한국어 내레이션)와 image_prompt(고품질 영어 프롬프트)를 포함해야 합니다. "
        "영어 프롬프트는 SDXL에 최적화되고 cinematic, Unreal Engine 5, 8k, 3D render, satisfying, "
        "volumetric light, ultra-detailed textures를 포함하세요. 한국어 내레이션은 자연스럽고 간결하게. "
        f"입력 주제: {keyword}"
    )


def generate_scenes(keyword: str, api_key: str = None) -> List[Dict]:
    """키워드로 씬 리스트를 생성."""
    model_name = configure_gemini(api_key)
    model = genai.GenerativeModel(model_name)
    prompt = build_director_prompt(keyword)
    response = model.generate_content(prompt)
    text = response.text or ""
    try:
        data = genai.types.from_json(text)  # type: ignore
    except Exception:
        import json

        data = json.loads(text)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("Gemini 응답이 씬 리스트 형식이 아닙니다.")
    for scene in data:
        if "voiceover" not in scene or "image_prompt" not in scene:
            raise ValueError("voiceover 또는 image_prompt 키가 누락되었습니다.")
    return data

