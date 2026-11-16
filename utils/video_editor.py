import os
import tempfile
from pathlib import Path
from typing import List, Dict

import PIL
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import CompositeVideoClip, ImageClip, VideoFileClip, concatenate_videoclips

# 오래된 Pillow 버전 호환 패치
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS  # type: ignore


def _draw_text_with_pil(text: str, size=(1280, 200), fontsize: int = 36) -> Path:
    """가독성을 위해 외곽선을 넣어 텍스트 이미지를 생성."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", fontsize)
    except OSError:
        font = ImageFont.load_default()
    text_w, text_h = draw.textsize(text, font=font)
    x = (size[0] - text_w) // 2
    y = (size[1] - text_h) // 2
    outline_color = "black"
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill="white")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    return Path(tmp.name)


def assemble_video_with_subtitles(video_paths: List[Path], scenes: List[Dict], output_path: Path) -> Path:
    """영상 클립에 자막을 합성하고 크로스페이드로 이어붙임."""
    clips = []
    for idx, video_path in enumerate(video_paths):
        base_clip = VideoFileClip(str(video_path))
        subtitle = scenes[idx].get("voiceover", "")
        text_img_path = _draw_text_with_pil(subtitle, size=(base_clip.w, 200))
        subtitle_clip = (
            ImageClip(str(text_img_path))
            .set_duration(base_clip.duration)
            .set_position(("center", base_clip.h - 220))
            .set_start(0)
        )
        composite = CompositeVideoClip([base_clip, subtitle_clip])
        clips.append(composite)

    # 인접 클립 사이에 크로스페이드 적용
    for i in range(1, len(clips)):
        clips[i] = clips[i].crossfadein(1.0)

    final = concatenate_videoclips(clips, method="compose", padding=-1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(str(output_path), codec="libx264", fps=24, audio_codec="aac")
    return output_path

