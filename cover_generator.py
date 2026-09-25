"""
Module de sélection et de génération de vignettes (Cover Frame) pour TikTok.
Analyse les images clés d'une vidéo pour identifier le moment visuel le plus
spectaculaire (contraste, netteté, intensité des couleurs) et génère une
miniature 9:16 percutante avec titre de couverture.
"""

import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Optional

from hook_generator import _get_font


def extract_best_cover_frames(
    video_path: str,
    max_candidates: int = 15,
    top_k: int = 4,
) -> List[Dict[str, Any]]:
    """
    Extrait les meilleures frames d'une vidéo selon la netteté et le contraste.
    Retourne une liste de dicts :
    [{'timestamp_sec': float, 'frame_rgb': np.ndarray, 'score': float, 'label': str}, ...]
    """
    if not os.path.exists(video_path):
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0

    if duration_sec <= 0:
        cap.release()
        return []

    # Échantillonnage uniforme
    timestamps = np.linspace(0.5, max(0.5, duration_sec - 0.5), num=max_candidates)
    candidates = []

    for t in timestamps:
        frame_idx = int(t * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame_bgr = cap.read()
        if not ret or frame_bgr is None:
            continue

        # Calcul netteté (Variance du Laplacien)
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Calcul dynamique du contraste (Écart-type des niveaux de gris)
        contrast_std = np.std(gray)

        # Calcul de saturation colorimétrique (HSV)
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        saturation_mean = np.mean(hsv[:, :, 1])

        # Score composite : netteté (50%) + contraste (30%) + éclat des couleurs (20%)
        composite_score = (laplacian_var * 0.5) + (contrast_std * 2.0) + (saturation_mean * 1.5)

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        candidates.append({
            "timestamp_sec": round(t, 2),
            "frame_rgb": frame_rgb,
            "score": round(composite_score, 1),
            "sharpness": round(laplacian_var, 1),
            "contrast": round(contrast_std, 1),
        })

    cap.release()

    # Trier par score décroissant et garder les top_k
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top_frames = candidates[:top_k]

    for i, item in enumerate(top_frames):
        item["rank"] = i + 1
        item["label"] = f"Frame #{i+1} (à {item['timestamp_sec']}s - Score: {item['score']})"

    return top_frames


def create_cover_with_sticker(
    frame_rgb: np.ndarray,
    title_text: str = "",
    badge_text: str = "NOUVEAU",
    style: str = "neon",
) -> np.ndarray:
    """
    Ajoute un sticker / bandeau de couverture percutant sur la frame sélectionnée.
    Garantit que le titre de couverture est lisible dans la grille de profil TikTok (ratio 3:4 centré).
    """
    h, w, _ = frame_rgb.shape
    base_img = Image.fromarray(frame_rgb).convert("RGBA")
    draw = ImageDraw.Draw(base_img)

    scale_x = w / 1080.0
    scale_y = h / 1920.0

    if not title_text.strip() and not badge_text.strip():
        return np.array(base_img.convert("RGB"))

    # Zone de la grille TikTok (au milieu de l'écran 9:16)
    center_y = int(960 * scale_y)

    # 1. Badge supérieur
    if badge_text.strip():
        font_badge = _get_font(int(26 * scale_x))
        b_w = int(220 * scale_x)
        b_h = int(50 * scale_y)
        b_x1 = int((w - b_w) / 2)
        b_y1 = center_y - int(120 * scale_y)
        b_x2 = b_x1 + b_w
        b_y2 = b_y1 + b_h

        badge_bg = (255, 0, 80, 245) if style == "neon" else (255, 200, 0, 245)
        badge_txt_color = (255, 255, 255, 255) if style == "neon" else (15, 15, 20, 255)

        draw.rounded_rectangle([b_x1, b_y1, b_x2, b_y2], radius=12, fill=badge_bg)
        draw.text((b_x1 + int(24 * scale_x), b_y1 + int(8 * scale_y)), badge_text.upper(), font=font_badge, fill=badge_txt_color)

    # 2. Grand titre de couverture centré
    if title_text.strip():
        import textwrap
        font_title = _get_font(int(52 * scale_x))
        lines = textwrap.wrap(title_text, width=22)

        line_h = int(70 * scale_y)
        total_h = len(lines) * line_h
        t_y = center_y - int(40 * scale_y)

        box_w = int(820 * scale_x)
        box_x1 = int((w - box_w) / 2)
        box_y1 = t_y - int(20 * scale_y)
        box_x2 = box_x1 + box_w
        box_y2 = box_y1 + total_h + int(40 * scale_y)

        # Fond sombre pour contraste absolu
        draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=20, fill=(12, 12, 18, 235), outline=(255, 255, 255, 220), width=3)

        curr_y = box_y1 + int(20 * scale_y)
        for line in lines:
            draw.text((box_x1 + int(30 * scale_x), curr_y), line, font=font_title, fill=(255, 235, 20, 255))
            curr_y += line_h

    return np.array(base_img.convert("RGB"))
