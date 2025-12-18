from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List

import streamlit as st
from dotenv import load_dotenv

from utils import generate_scenes, generate_images, create_slideshow

load_dotenv()


def _get_assets_root() -> Path:
    """환경 변수 또는 기본값으로 자산 루트 디렉터리 결정."""
    root = os.getenv("ASSETS_DIR", "assets")
    return Path(root)


def _new_run_directory() -> Path:
    """실행 시점별 폴더 생성."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = _get_assets_root() / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _has_env_keys() -> bool:
    """필수 키 존재 여부 검사."""
    return bool(os.getenv("GOOGLE_API_KEY") and os.getenv("HF_TOKEN"))


def main() -> None:
    st.set_page_config(page_title="YouTube Shorts Factory", layout="wide")
    st.title("🎬 YouTube Shorts Factory")
    st.caption("주제만 넣으면 스크립트 → 이미지 → 영상까지 자동화")

    topic = st.text_input("주제(Topic)를 입력하세요", placeholder="예: 7 Deadly Sins as Cats")
    run_button = st.button("생성 시작", type="primary")

    if run_button:
        if not _has_env_keys():
            st.error("GOOGLE_API_KEY 와 HF_TOKEN 을 .env에 설정해주세요.")
            return

        if not topic.strip():
            st.warning("주제를 입력해주세요.")
            return

        st.info("1) Gemini로 스크립트 생성 중...")
        scenes, err = generate_scenes(topic)
        if err:
            st.error(f"스크립트를 생성하지 못했습니다: {err}")
            return

        st.success(f"장면 {len(scenes)}개 생성 완료")
        run_dir = _new_run_directory()
        image_dir = run_dir / "images"
        video_path = run_dir / "video.mp4"

        st.info("2) SDXL로 이미지 생성 중...")
        image_paths = generate_images(scenes, image_dir)
        if not image_paths:
            st.error("이미지 생성에 실패했습니다. Hugging Face 토큰을 확인하거나 재시도하세요.")
            return

        st.success(f"이미지 {len(image_paths)}개 생성 완료 → {image_dir}")

        st.info("3) MoviePy로 영상 합성 중...")
        subtitles: List[str] = [scene.get("voiceover", "") for scene in scenes][: len(image_paths)]
        try:
            output = create_slideshow(image_paths, subtitles, video_path)
            st.video(str(output))
            st.success(f"영상 생성 완료: {output}")
        except Exception as exc:
            st.error(f"영상 합성 중 오류가 발생했습니다: {exc}")


if __name__ == "__main__":
    main()



