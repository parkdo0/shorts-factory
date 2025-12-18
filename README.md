# AI Shorts Generator (Prototype v1.0)

## 📖 Project Overview
이 프로젝트는 "유튜브 쇼츠 제작 과정을 어디까지 자동화할 수 있을까?"라는 호기심에서 시작된 테스트 프로젝트입니다. 주제만 던져주면 기획(Script)부터 이미지 생성, 영상 편집까지 파이썬 코드 하나로 처리하는 것을 목표로 했습니다.

초기에는 접근성을 위해 Hugging Face와 Google Gemini API를 활용하여 파이프라인을 구축했습니다.

## Limitations & Future Roadmap (Why ComfyUI?)
프로젝트를 진행하며 Cloud API 기반 방식의 명확한 한계를 느꼈습니다. 현재 버전(v1.0)을 끝으로, 로컬 GPU 기반의 **ComfyUI** 방식으로 전환할 예정입니다.

**1. 이미지 품질의 한계**
무료 API 모델(SDXL Base 등)로는 내가 원하는 구체적인 질감이나 'Satisfying 3D' 느낌을 일관되게 뽑아내기 어려웠습니다. 프롬프트를 아무리 깎아도 API 서버의 상황에 따라 퀄리티가 들쭉날쭉했습니다.

**2. 동영상 변환(Image-to-Video)의 어려움**
가장 큰 장벽은 '움직임'이었습니다. 정적인 이미지에 단순히 줌인/줌아웃(Ken Burns) 효과를 넣는 것만으로는 요즘 쇼츠 트렌드인 "역동적인 영상미"를 따라갈 수 없었습니다. API를 통한 비디오 생성은 대기 시간이 길고 비용 문제가 있어, 프로덕션 레벨로 쓰기엔 무리라고 판단했습니다.

**결론:**
따라서 다음 버전부터는 **RTX 3080 Ti 로컬 환경**을 활용해 **ComfyUI**와 연동할 계획입니다. 이를 통해 비용 제약 없이 고품질의 SVD(Stable Video Diffusion) 영상을 생성하고, 더 정교한 컨트롤을 구현할 것입니다.

---

## 🛠 Tech Stack
* **Language**: Python 3.9+
* **Web Framework**: Streamlit
* **AI/LLM**: Google Gemini API (Scripting), Hugging Face Inference API (Image Gen)
* **Video Processing**: MoviePy (Custom pipeline without ImageMagick)
* **Image Processing**: Pillow, NumPy

---

## ⚙️ Installation & Setup

### 1. Environment Setup
```bash
# Repository Clone
git clone https://github.com/your-username/ai-shorts-generator.git
cd ai-shorts-generator

# Install Dependencies
pip install -r requirements.txt
2. API Key Configuration
프로젝트 루트 디렉토리에 .env 파일을 생성하고 아래 키를 입력해야 합니다. (Gemini와 Hugging Face 계정이 필요합니다.)

Ini, TOML

GOOGLE_API_KEY=your_gemini_api_key_here
HF_TOKEN=your_huggingface_token_here
3. Run Application
Bash

streamlit run main.py
실행 후 브라우저가 열리면 사이드바에 주제를 입력하고 생성 버튼을 누르면 됩니다.

📝 Technical Issues & Solutions
개발 과정에서 겪은 주요 라이브러리 충돌 문제와 해결 방법입니다.

1. MoviePy와 ImageMagick 의존성 제거
MoviePy의 TextClip 기능은 자막 생성을 위해 ImageMagick 설치를 요구합니다. 하지만 윈도우 환경에서 경로 설정 에러(WinError 2)가 빈번하게 발생하여 배포에 불리했습니다.

해결: PIL (Pillow) 라이브러리를 사용해 이미지 위에 직접 텍스트를 렌더링(Drawing)하는 커스텀 함수를 구현했습니다. 이를 통해 외부 프로그램 설치 없이 순수 파이썬 코드만으로 자막 기능이 작동하도록 개선했습니다.

2. Pillow 버전 호환성 문제 (Monkey Patch)
최신 Pillow 10.x 버전에서 ANTIALIAS 속성이 삭제되었으나, MoviePy 구버전이 이를 참조하여 AttributeError가 발생했습니다.

해결: 코드 최상단에 몽키 패치(Monkey Patch)를 적용하여 하위 호환성을 확보했습니다.

Python

import PIL.Image
# Pillow 10.0 이상 호환성 패치
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
📂 Project Structure
ai-shorts-generator/
├── main.py              # Streamlit 메인 실행 파일
├── requirements.txt     # 의존성 패키지 목록
├── .env                 # API 키 설정 (gitignore 처리됨)
└── utils/
    ├── script_gen.py    # Gemini 기반 스크립트/프롬프트 생성
    ├── image_gen.py     # Hugging Face 이미지 생성 로직
    └── video_gen.py     # MoviePy 영상 편집 및 자막 합성
