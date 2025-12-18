from __future__ import annotations

import json
import urllib.request
import urllib.parse
import uuid
import random
import os
import time
import shutil
import websocket # pip install websocket-client
from pathlib import Path
from typing import List

# ==========================================
# [설정] 집에 가서 여기만 바꾸면 됩니다
# ==========================================
COMFY_URL = "127.0.0.1:8188"  # ComfyUI 주소
WORKFLOW_FILE = "svd_workflow_api.json" # 저장한 워크플로우 파일명

# [세부 조절] 여기서 숫자를 바꾸면 영상 느낌이 확 달라집니다!
MOTION_BUCKET_ID = 127  # 움직임 강도 (기본: 127, 추천범위: 100~180)
# - 100 이하: 아주 잔잔함 (카메라만 살짝 이동)
# - 127: 표준 (물 흐름, 머릿결 흔들림)
# - 180 이상: 격렬함 (때로는 이미지가 깨질 수도 있음)

AUGMENTATION_LEVEL = 0.02 # 원본 변형도 (기본: 0.02)
# - 0.0: 원본 그대로
# - 0.1 이상: AI가 배경이나 사물을 조금씩 자기 멋대로 바꿈
# ==========================================

def queue_prompt(workflow_data):
    p = {"prompt": workflow_data, "client_id": str(uuid.uuid4())}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{COMFY_URL}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

def find_node_by_class(workflow, class_type_name):
    """초보자를 위한 기능: ID를 몰라도 '기능 이름'으로 노드를 찾아줍니다."""
    for node_id, node_info in workflow.items():
        if node_info["class_type"] == class_type_name:
            return node_id, node_info
    return None, None

def create_video_via_comfyui(image_path: Path, output_path: Path) -> Path | None:
    print(f"🎬 [ComfyUI] 영상 생성 요청: {image_path.name}")
    print(f"   ⚙️ 세팅값: 움직임강도({MOTION_BUCKET_ID}), 변형도({AUGMENTATION_LEVEL})")

    # 1. 워크플로우 파일 로드
    if not os.path.exists(WORKFLOW_FILE):
        print(f"❌ 오류: '{WORKFLOW_FILE}' 파일을 찾을 수 없습니다. (프로젝트 폴더에 넣어주세요)")
        return None

    with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
        workflow = json.load(f)

    # 2. [자동화 핵심] 노드 찾아서 값 바꿔치기
    # (사용자가 ID를 몰라도 코드가 알아서 찾습니다)
    
    # (1) 이미지 넣는 곳 찾기 (LoadImage)
    load_image_id, load_image_node = find_node_by_class(workflow, "LoadImage")
    if load_image_node:
        # ComfyUI는 절대경로가 필요함
        load_image_node["inputs"]["image"] = str(image_path.absolute())
    else:
        print("❌ 'LoadImage' 노드를 찾을 수 없습니다. (워크플로우 확인 필요)")
        return None

    # (2) 영상 설정하는 곳 찾기 (SVD_img2vid_Conditioning)
    # 여기서 '세부 조절'을 자동으로 적용합니다.
    svd_node_id, svd_node = find_node_by_class(workflow, "SVD_img2vid_Conditioning")
    if svd_node:
        svd_node["inputs"]["motion_bucket_id"] = MOTION_BUCKET_ID
        svd_node["inputs"]["augmentation_level"] = AUGMENTATION_LEVEL
    
    # (3) 랜덤 시드 설정 (KSampler) - 매번 다른 느낌을 주기 위해
    ksampler_id, ksampler_node = find_node_by_class(workflow, "KSampler")
    if ksampler_node:
        ksampler_node["inputs"]["seed"] = random.randint(1, 9999999999)

    # (4) 저장 경로 설정 (VideoSave 또는 VHS_VideoCombine)
    # ComfyUI 결과물은 기본 output 폴더에 저장되므로, 일단 실행하고 파일명을 추적해야 함.

    # 3. 실행!
    try:
        ws = websocket.WebSocket()
        ws.connect(f"ws://{COMFY_URL}/ws?clientId={str(uuid.uuid4())}")
        
        prompt_response = queue_prompt(workflow)
        prompt_id = prompt_response['prompt_id']
        
        print("   ⏳ 렌더링 중... (3080 Ti 기준 약 30~60초 소요)")
        
        # 대기 루프
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break # 완료!
        
        ws.close()
        
        # 4. 결과물 가져오기
        # ComfyUI의 output 폴더에서 가장 최근에 생성된 mp4/webp 파일을 찾아서 가져옴
        # (초보자를 위한 가장 쉬운 방법: 가장 최신 파일 납치하기)
        comfy_output_dir = Path("C:/ComfyUI_windows_portable/ComfyUI/output") # [수정필요] 실제 설치 경로
        
        # 경로가 틀리면 현재 폴더 근처에서 찾기 시도
        if not comfy_output_dir.exists():
             # 보통 상위 폴더 어딘가에 있겠지... 가정
             print("⚠️ ComfyUI output 폴더 경로를 코드에서 수정해주세요. (임시로 현재폴더 사용)")
             return None

        # 가장 최근 파일 찾기
        files = list(comfy_output_dir.glob("*.mp4")) + list(comfy_output_dir.glob("*.gif")) + list(comfy_output_dir.glob("*.webp"))
        if not files:
            print("❌ 생성된 영상 파일을 찾을 수 없습니다.")
            return None
            
        latest_file = max(files, key=os.path.getctime)
        
        # 결과물을 우리 프로젝트 폴더로 복사
        shutil.copy(latest_file, output_path)
        print(f"✅ 영상 확보 완료: {output_path.name}")
        return output_path

    except Exception as e:
        print(f"❌ ComfyUI 통신 에러: {e}")
        return None

# 기존 create_slideshow 함수는 이 함수를 호출하여 리스트로 영상을 만듭니다.
# (이전 답변의 create_slideshow 로직과 결합하면 됩니다)