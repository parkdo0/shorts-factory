import json
import os
import random
from pathlib import Path
from typing import Dict, List

from . import comfy_client

ASSETS_DIR = Path("assets")
IMAGES_DIR = ASSETS_DIR / "images"
VIDEOS_DIR = ASSETS_DIR / "videos"

NEGATIVE_PROMPT = (
    "low quality, worst quality, blurry, noisy, distorted, extra limbs, artifacts, watermark, text, nsfw"
)


def _load_workflow(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _choose_positive_clip_node(workflow: Dict) -> str:
    nodes = comfy_client.find_nodes_by_class(workflow, "CLIPTextEncode")
    if not nodes:
        raise ValueError("No CLIPTextEncode nodes found")
    # Positive prompt often has longer text
    nodes_sorted = sorted(nodes, key=lambda pair: len(str(pair[1].get("inputs", {}).get("text", ""))), reverse=True)
    return nodes_sorted[0][0]


def _choose_negative_clip_node(workflow: Dict, positive_node_id: str) -> str:
    nodes = comfy_client.find_nodes_by_class(workflow, "CLIPTextEncode")
    for node_id, _ in nodes:
        if node_id != positive_node_id:
            return node_id
    return positive_node_id


def generate_images_local(scenes: List[Dict], workflow_path: Path) -> List[Path]:
    image_paths: List[Path] = []
    for idx, scene in enumerate(scenes):
        workflow = _load_workflow(workflow_path)
        pos_id = _choose_positive_clip_node(workflow)
        neg_id = _choose_negative_clip_node(workflow, pos_id)

        replacements = {
            "CLIPTextEncode": [
                {"text": scene["image_prompt"]},
                {"text": NEGATIVE_PROMPT},
            ],
        }

        # Ensure order corresponds to sorted nodes
        clip_nodes = comfy_client.find_nodes_by_class(workflow, "CLIPTextEncode")
        clip_nodes_sorted = sorted(
            clip_nodes,
            key=lambda pair: len(str(pair[1].get("inputs", {}).get("text", ""))),
            reverse=True,
        )
        replacements["CLIPTextEncode"] = []
        for node_id, node in clip_nodes_sorted:
            if node_id == pos_id:
                replacements["CLIPTextEncode"].append({"text": scene["image_prompt"]})
            else:
                replacements["CLIPTextEncode"].append({"text": NEGATIVE_PROMPT})

        target = IMAGES_DIR / f"scene_{idx+1:02d}.png"
        path = comfy_client.generate_media_via_comfy(
            workflow_path,
            replacements_dict=replacements,
            target_filename=target,
            extension=".png",
            timeout=180,
        )
        image_paths.append(path)
    return image_paths


def generate_videos_local(image_paths: List[Path], workflow_path: Path) -> List[Path]:
    video_paths: List[Path] = []
    for idx, image_path in enumerate(image_paths):
        workflow = _load_workflow(workflow_path)
        replacements = {
            "LoadImage": {"image": str(image_path)},
            "SVD_img2vid_Conditioning": {"motion_bucket_id": 127, "augmentation_level": 0.02},
        }
        target = VIDEOS_DIR / f"scene_{idx+1:02d}.mp4"
        path = comfy_client.generate_media_via_comfy(
            workflow_path,
            replacements_dict=replacements,
            target_filename=target,
            extension=".mp4",
            timeout=300,
        )
        video_paths.append(path)
    return video_paths

