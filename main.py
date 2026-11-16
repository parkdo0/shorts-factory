import json
import os
from pathlib import Path
from typing import List, Dict

import streamlit as st

from utils import script_gen, media_gen, video_editor

WORKFLOW_T2I = Path("workflow_t2i.json")
WORKFLOW_I2V = Path("workflow_i2v.json")
FINAL_OUTPUT = Path("outputs/final_movie.mp4")


def log(message: str):
    """로그 리스트에 추가하고 UI 갱신."""
    st.session_state.logs.append(message)
    st.session_state.log_area.text("\n".join(st.session_state.logs))


def ensure_state():
    """세션 상태 기본값을 준비."""
    defaults = {
        "keyword": "",
        "scenes": [],
        "image_paths": [],
        "video_paths": [],
        "logs": [],
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def main():
    st.set_page_config(page_title="로컬 AI 쇼츠 제너레이터", layout="wide")
    ensure_state()

    st.title("로컬 AI 쇼츠 제너레이터 (ComfyUI + Gemini)")

    with st.sidebar:
        st.markdown("### 설정")
        api_key = st.text_input("Gemini API Key", type="password")
        st.session_state.keyword = st.text_input("프로젝트 주제 (한글 키워드)", value=st.session_state.keyword)
        generate_script_btn = st.button("스크립트 생성")
        generate_images_btn = st.button("이미지 생성 (로컬)")
        generate_videos_btn = st.button("영상 생성 (로컬)")
        render_btn = st.button("최종 영상 렌더")

    st.session_state.log_area = st.empty()
    log("대기 중입니다.")

    if generate_script_btn:
        try:
            log("Gemini에 스크립트를 요청 중...")
            scenes = script_gen.generate_scenes(st.session_state.keyword, api_key=api_key)
            st.session_state.scenes = scenes
            log(f"{len(scenes)}개의 씬을 수신했습니다.")
        except Exception as e:
            log(f"스크립트 생성 실패: {e}")

    if generate_images_btn:
        if not st.session_state.scenes:
            log("씬 정보가 없습니다. 먼저 스크립트를 생성하세요.")
        else:
            try:
                log("ComfyUI를 통해 이미지를 생성 중...")
                images = media_gen.generate_images_local(st.session_state.scenes, WORKFLOW_T2I)
                st.session_state.image_paths = images
                log(f"{len(images)}개의 이미지를 생성했습니다.")
            except Exception as e:
                log(f"이미지 생성 실패: {e}")

    if generate_videos_btn:
        if not st.session_state.image_paths:
            log("이미지 경로가 없습니다. 먼저 이미지를 생성하세요.")
        else:
            try:
                log("ComfyUI(SVD)로 영상을 생성 중...")
                videos = media_gen.generate_videos_local(st.session_state.image_paths, WORKFLOW_I2V)
                st.session_state.video_paths = videos
                log(f"{len(videos)}개의 영상을 생성했습니다.")
            except Exception as e:
                log(f"영상 생성 실패: {e}")

    if render_btn:
        if not st.session_state.video_paths:
            log("영상 클립이 없습니다. 먼저 영상을 생성하세요.")
        else:
            try:
                log("자막을 입혀 최종 영상을 렌더링 중...")
                video_editor.assemble_video_with_subtitles(
                    st.session_state.video_paths, st.session_state.scenes, FINAL_OUTPUT
                )
                log(f"렌더 완료: {FINAL_OUTPUT}")
            except Exception as e:
                log(f"렌더 실패: {e}")

    if st.session_state.scenes:
        st.markdown("### 씬 목록")
        for idx, scene in enumerate(st.session_state.scenes, start=1):
            st.markdown(f"**씬 {idx}**")
            st.markdown(f"- 내레이션: {scene.get('voiceover', '')}")
            st.markdown(f"- 프롬프트: {scene.get('image_prompt', '')}")


if __name__ == "__main__":
    main()

