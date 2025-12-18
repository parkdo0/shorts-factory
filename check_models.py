from __future__ import annotations

import os

import google.generativeai as genai
from dotenv import load_dotenv

# .env 로드 후 GOOGLE_API_KEY로 인증
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY가 .env에 설정되어 있지 않습니다.")

genai.configure(api_key=api_key)


def main() -> None:
    """
    사용 가능한 모델 중 generateContent 지원 모델을 출력.
    """
    models = genai.list_models()
    print("=== generateContent 지원 모델 ===")
    for m in models:
        # 일부 모델은 supported_generation_methods 속성을 갖고 있음
        methods = getattr(m, "supported_generation_methods", [])
        name = getattr(m, "name", "unknown")
        if "generateContent" in methods:
            print(f"- {name}")


if __name__ == "__main__":
    main()

