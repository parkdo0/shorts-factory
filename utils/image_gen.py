from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any
import time

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

def _get_hf_client() -> InferenceClient:
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_TOKEN")
    if not token:
        raise ValueError("HF_TOKEN이 없습니다.")
    return InferenceClient(token=token)

def _ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def generate_images(
    scenes: List[Dict[str, Any]],
    output_dir: Path,
    # [변경] 가장 안전하고 무료인 '표준' 모델로 복귀
    hf_model: str = "stabilityai/stable-diffusion-xl-base-1.0", 
) -> List[Path]:
    if not scenes:
        print("❌ [Image Gen] 생성할 장면이 없습니다.")
        return []

    try:
        client = _get_hf_client()
    except Exception as e:
        print(f"❌ [Image Gen] 클라이언트 설정 오류: {e}")
        return []

    _ensure_output_dir(output_dir)
    saved_paths: List[Path] = []

    print(f"🎨 [안전 모드] 이미지 생성을 시작합니다 (모델: {hf_model})...")

    # SDXL 모델을 위한 강력한 부정 프롬프트 (뭉개짐 방지)
    negative_prompt = "text, watermark, blurry, low quality, distorted, ugly, bad anatomy, pixelated, cartoon, illustration, drawing, anime"

    for idx, scene in enumerate(scenes, start=1):
        raw_prompt = str(scene.get("image_prompt", "")).strip()
        if not raw_prompt:
            continue
            
        # [화질 보정] 모델이 무료인 대신, 프롬프트로 퀄리티를 강제 주입합니다.
        # "Award winning", "Unreal Engine 5" 같은 단어가 효과가 좋습니다.
        enhanced_prompt = f"photoshoot of {raw_prompt}, hyper-realistic, 8k, highly detailed, dramatic lighting, cinematic atmosphere, sharp focus, f/1.8, 85mm lens"
        
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                print(f"   Generating Scene {idx} (시도 {retry_count+1}/{max_retries})...")
                
                # 이미지 생성 요청
                image = client.text_to_image(
                    prompt=enhanced_prompt,
                    negative_prompt=negative_prompt,
                    model=hf_model,
                    num_inference_steps=30, # 무료 서버 부하를 고려해 30으로 조정 (충분함)
                    guidance_scale=7.5,
                )
                
                file_path = output_dir / f"scene_{idx:02d}.png"
                image.save(file_path)
                print(f"✅ Scene {idx} 저장 완료")
                saved_paths.append(file_path)
                break 

            except Exception as e:
                # 402(유료), 400(입력오류) 등 치명적 에러는 바로 출력
                if "402" in str(e):
                    print(f"❌ 유료 모델 에러. 무료 모델로 자동 전환이 필요합니다.")
                    break
                    
                # 503(서버 바쁨)이나 500(시간 초과)은 재시도
                print(f"❌ 생성 실패 ({e})...")
                if "503" in str(e) or "timed out" in str(e).lower() or "500" in str(e):
                    retry_count += 1
                    print(f"   ⚠️ 무료 서버가 혼잡합니다. 5초 쉬고 다시 시도합니다...")
                    time.sleep(5)
                else:
                    break
    
    if not saved_paths:
        print("❌ 생성된 이미지가 없습니다.")

    return saved_paths