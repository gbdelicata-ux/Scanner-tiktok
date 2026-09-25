"""
Module de génération d'accroches visuelles ("Hook 0-2s") pour TikTok.
Incruste un titre percutant pendant les premières secondes de la vidéo,
garanti 100% positionné dans la Safe Zone TikTok pour maximiser la rétention
et briser le plafond des 800 vues.
"""

import os
import subprocess
import tempfile
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

# Styles visuels d'accroches haute performance
HOOK_STYLES = {
    "yellow_impact": {
        "name": "⚡ Impact Jaune / Noir (Style Viral TikTok)",
        "bg_color": (15, 15, 20, 235),
        "text_color": (255, 225, 0, 255),
        "accent_color": (255, 255, 255, 255),
        "border_color": (255, 225, 0, 255),
    },
    "cyber_cyan": {
        "name": "🪐 Cyber Cyan / Espace (Idéal CGI & Astronomie)",
        "bg_color": (10, 15, 30, 235),
        "text_color": (0, 240, 255, 255),
        "accent_color": (255, 255, 255, 255),
        "border_color": (0, 240, 255, 255),
    },
    "alert_red": {
        "name": "🚨 Alerte Rouge (Urgence / Révélation)",
        "bg_color": (40, 10, 15, 240),
        "text_color": (255, 255, 255, 255),
        "accent_color": (255, 75, 75, 255),
        "border_color": (255, 60, 60, 255),
    },
    "clean_dark": {
        "name": "🖤 Minimaliste Dark (Élégant / Facecam)",
        "bg_color": (20, 20, 24, 230),
        "text_color": (255, 255, 255, 255),
        "accent_color": (200, 200, 200, 255),
        "border_color": (80, 80, 90, 200),
    },
}

# Modèles d'accroches pré-rédigées prêtes à l'emploi
HOOK_PRESETS = {
    "espace_cgi": [
        "🚀 Que se passerait-il si cet astéroïde touchait la Terre ?",
        "🪐 Regardez bien à la 4e seconde... C'est stupéfiant !",
        "💥 Simulation réelle : L'impact d'une collision spatiale",
        "🌌 Ce que la NASA ne vous montre jamais sur l'espace",
        "🛰️ La vitesse réelle de cette fusée dépasse l'entendement...",
    ],
    "facecam_conseil": [
        "🛑 Arrêtez de faire cette erreur immédiatement !",
        "💡 Le secret que 99% des gens ignorent encore :",
        "❓ Pourquoi personne ne parle de cette vérité ?",
        "👀 Regardez jusqu'à la fin pour comprendre...",
        "🧠 3 faits incroyables qui vont changer votre vision :",
    ],
    "curiosite_generale": [
        "😱 Ne regardez pas si vous avez le vertige !",
        "⏳ Attendez la fin pour voir ce qui arrive...",
        "🤯 Ce détail va complètement vous choquer !",
        "🔥 Vous n'étiez clairement pas prêts pour ça :",
    ],
}


def _get_font(size: int = 42):
    """Charge une police TTF système ou la police par défaut de PIL."""
    font_paths = [
        "/System/Library/Fonts/SFCompact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def create_hook_banner_image(
    text: str,
    style_key: str = "yellow_impact",
    target_width: int = 1080,
    target_height: int = 1920,
) -> Image.Image:
    """
    Génère un calque RGBA transparent 1080x1920 contenant la boîte d'accroche
    parfaitement centrée dans la Safe Zone TikTok.
    """
    style = HOOK_STYLES.get(style_key, HOOK_STYLES["yellow_impact"])
    overlay = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_title = _get_font(int(46 * (target_width / 1080.0)))
    font_badge = _get_font(int(24 * (target_width / 1080.0)))

    # Découpage du texte en lignes (max ~28-32 caractères par ligne)
    lines = textwrap.wrap(text, width=28)
    if not lines:
        lines = [text]

    # Dimensions de la bannière
    # Safe zone X: de 60 à 870 (largeur max ~760px)
    banner_w = int(760 * (target_width / 1080.0))
    line_height = int(60 * (target_height / 1920.0))
    badge_height = int(45 * (target_height / 1920.0))
    padding_v = int(35 * (target_height / 1920.0))
    banner_h = (len(lines) * line_height) + badge_height + (padding_v * 2)

    # Position Y dans la Safe Zone (yeux du spectateur, entre Y=260 et Y=300)
    top_y = int(280 * (target_height / 1920.0))
    # Centré dans la zone sécurisée (60 à 870)
    left_x = int(60 + (810 - banner_w) / 2)
    right_x = left_x + banner_w
    bottom_y = top_y + banner_h

    # 1. Ombre portée douce
    shadow_offset = int(8 * (target_width / 1080.0))
    draw.rounded_rectangle(
        [left_x + shadow_offset, top_y + shadow_offset, right_x + shadow_offset, bottom_y + shadow_offset],
        radius=24,
        fill=(0, 0, 0, 140),
    )

    # 2. Boîte principale
    draw.rounded_rectangle(
        [left_x, top_y, right_x, bottom_y],
        radius=24,
        fill=style["bg_color"],
        outline=style["border_color"],
        width=max(2, int(3 * (target_width / 1080.0))),
    )

    # 3. Petit badge en haut de la bannière ("⚡ ATTENTION" ou "👁️ REGARDEZ")
    badge_bg = style["border_color"]
    badge_x1 = left_x + int(30 * (target_width / 1080.0))
    badge_y1 = top_y + int(18 * (target_height / 1920.0))
    badge_x2 = badge_x1 + int(170 * (target_width / 1080.0))
    badge_y2 = badge_y1 + badge_height - int(10 * (target_height / 1920.0))
    draw.rounded_rectangle([badge_x1, badge_y1, badge_x2, badge_y2], radius=10, fill=badge_bg)
    draw.text(
        (badge_x1 + int(14 * (target_width / 1080.0)), badge_y1 + int(4 * (target_height / 1920.0))),
        "👁️ À VOIR",
        font=font_badge,
        fill=(10, 10, 15, 255),
    )

    # 4. Dessin des lignes de texte
    text_y = badge_y2 + int(18 * (target_height / 1920.0))
    for line in lines:
        draw.text(
            (left_x + int(32 * (target_width / 1080.0)), text_y),
            line,
            font=font_title,
            fill=style["text_color"],
        )
        text_y += line_height

    return overlay


def preview_hook_on_frame(
    frame_rgb: np.ndarray,
    text: str,
    style_key: str = "yellow_impact",
) -> np.ndarray:
    """
    Superpose l'accroche sur une image RGB NumPy pour la prévisualiser dans Streamlit.
    """
    h, w, _ = frame_rgb.shape
    base_img = Image.fromarray(frame_rgb).convert("RGBA")
    banner_layer = create_hook_banner_image(text, style_key=style_key, target_width=w, target_height=h)
    combined = Image.alpha_composite(base_img, banner_layer)
    return np.array(combined.convert("RGB"))


def add_hook_to_video(
    input_video_path: str,
    output_video_path: str,
    hook_text: str,
    style_key: str = "yellow_impact",
    duration_sec: float = 2.5,
) -> dict:
    """
    Incruste la bannière d'accroche pendant les `duration_sec` premières secondes
    d'un fichier vidéo MP4/MOV.
    """
    if not os.path.exists(input_video_path):
        return {"success": False, "error": f"Fichier vidéo introuvable : {input_video_path}"}

    # 1. Générer le fichier PNG temporaire du bandeau
    temp_png = tempfile.mktemp(suffix="_hook_banner.png")
    banner_img = create_hook_banner_image(hook_text, style_key=style_key)
    banner_img.save(temp_png, format="PNG")

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Filtre overlay FFmpeg avec condition de temps enable='between(t,0,{duration_sec})'
    filter_complex = f"[0:v][1:v]overlay=0:0:enable='between(t,0,{duration_sec})'[outv]"

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", input_video_path,
        "-i", temp_png,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_video_path,
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            return {"success": False, "error": f"Erreur FFmpeg: {proc.stderr[-300:]}"}

        file_size_mb = round(os.path.getsize(output_video_path) / (1024 * 1024), 2)
        return {
            "success": True,
            "output_path": output_video_path,
            "file_size_mb": file_size_mb,
            "duration_sec": duration_sec,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if os.path.exists(temp_png):
            try:
                os.remove(temp_png)
            except Exception:
                pass
