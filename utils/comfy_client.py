import json
import os
import random
import shutil
import time
from pathlib import Path
from typing import Dict, List, Tuple, Union

import requests
import websocket

# 사용자가 직접 수정할 수 있는 ComfyUI 출력 경로
COMFY_OUTPUT_DIR = Path(os.getenv("COMFY_OUTPUT_DIR", r"C:/Users/User/ComfyUI/output"))
COMFY_HTTP_URL = "http://127.0.0.1:8188"
COMFY_WS_URL = "ws://127.0.0.1:8188/ws"


def queue_prompt(workflow: Dict) -> str:
    """워크플로를 ComfyUI에 전송하고 prompt_id를 반환."""
    resp = requests.post(f"{COMFY_HTTP_URL}/prompt", json=workflow, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    prompt_id = data.get("prompt_id")
    if not prompt_id:
        raise RuntimeError("ComfyUI에서 prompt_id를 반환하지 않았습니다.")
    return prompt_id


def track_progress(prompt_id: str, timeout: int = 120) -> None:
    """웹소켓으로 상태를 수신하며 완료 또는 타임아웃까지 대기."""
    ws = websocket.WebSocket()
    ws.settimeout(5)
    ws.connect(COMFY_WS_URL)
    start = time.time()
    try:
        while True:
            if time.time() - start > timeout:
                raise TimeoutError(f"ComfyUI 실행 타임아웃: {prompt_id}")
            try:
                msg = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            if not msg:
                continue
            try:
                payload = json.loads(msg)
            except json.JSONDecodeError:
                continue
            if payload.get("type") == "progress" and payload.get("data", {}).get("prompt_id") == prompt_id:
                continue
            if payload.get("type") == "executed" and payload.get("data", {}).get("prompt_id") == prompt_id:
                break
    finally:
        ws.close()


def find_nodes_by_class(workflow: Dict, class_type: str) -> List[Tuple[str, Dict]]:
    """특정 class_type을 가진 노드 목록 반환."""
    nodes = workflow.get("nodes") or workflow.get("workflow") or {}
    results: List[Tuple[str, Dict]] = []
    for node_id, node in nodes.items():
        if node.get("class_type") == class_type:
            results.append((node_id, node))
    return results


def find_node_by_class(workflow: Dict, class_type: str) -> Tuple[str, Dict]:
    """특정 class_type을 가진 첫 노드 반환."""
    matches = find_nodes_by_class(workflow, class_type)
    if not matches:
        raise ValueError(f"class_type '{class_type}' 노드를 찾을 수 없습니다.")
    return matches[0]


def _apply_replacements(workflow: Dict, replacements: Dict[str, Union[Dict, List[Dict]]]) -> None:
    """매칭되는 노드에 입력값을 덮어쓰기."""
    for class_type, payload in replacements.items():
        nodes = find_nodes_by_class(workflow, class_type)
        if not nodes:
            continue
        if isinstance(payload, list):
            for node_pair, values in zip(nodes, payload):
                node_id, node = node_pair
                node.setdefault("inputs", {}).update(values)
        else:
            node_id, node = nodes[0]
            node.setdefault("inputs", {}).update(payload)


def get_latest_output_file(output_dir: Path, extension: str) -> Path:
    """출력 폴더에서 가장 최근 생성된 파일을 반환."""
    if not output_dir.exists():
        raise FileNotFoundError(f"출력 폴더를 찾을 수 없습니다: {output_dir}")
    candidates = list(output_dir.glob(f"**/*{extension}"))
    if not candidates:
        raise FileNotFoundError(f"{output_dir} 내에 {extension} 확장자 파일이 없습니다.")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def generate_media_via_comfy(
    workflow_path: Union[str, Path],
    replacements_dict: Dict[str, Union[Dict, List[Dict]]],
    target_filename: Union[str, Path],
    extension: str = ".png",
    timeout: int = 180,
) -> Path:
    """워크플로를 로드하고 값 치환 후 ComfyUI 실행, 최신 결과를 프로젝트 폴더로 이동."""
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)

    _apply_replacements(workflow, replacements_dict)

    # KSampler가 있으면 시드를 랜덤으로 부여
    for node_id, node in find_nodes_by_class(workflow, "KSampler"):
        node.setdefault("inputs", {})["seed"] = random.randint(1, 2**31 - 1)

    prompt_id = queue_prompt({"prompt": workflow})
    track_progress(prompt_id, timeout=timeout)

    latest = get_latest_output_file(COMFY_OUTPUT_DIR, extension)
    target_path = Path(target_filename)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(latest), target_path)
    return target_path

