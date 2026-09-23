"""
Module de calcul et de rendu de la Safe Zone TikTok officielle (format 9:16).
Fournit un calque réaliste superposé à la vidéo pour vérifier que les textes,
sous-titres et éléments d'action ne sont pas masqués par les boutons de l'interface.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def get_tiktok_safe_zone_rects(width: int, height: int):
    """
    Retourne les coordonnées relatives et absolues des zones mortes de l'interface TikTok :
    - Top bar (Recherche, Onglets Pour Toi / Suivis)
    - Right bar (Profil, Like, Commentaire, Enregistrement, Partage, Son)
    - Bottom bar (Nom du créateur, Légende, Hashtags, Titre audio)
    - Safe Zone (Zone centrale optimale)
    """
    scale_x = width / 1080.0
    scale_y = height / 1920.0

    # Coordonnées basées sur un gabarit 1080x1920 standard
    top_bar = {
        "name": "Barre supérieure (Recherche, Onglets)",
        "x1": 0,
        "y1": 0,
        "x2": width,
        "y2": int(180 * scale_y),
    }

    right_sidebar = {
        "name": "Boutons d'interaction droite (Like, Com, Partage, Son)",
        "x1": int(880 * scale_x),
        "y1": int(720 * scale_y),
        "x2": width,
        "y2": int(1720 * scale_y),
    }

    bottom_bar = {
        "name": "Zone de légende & Musique (Bas de l'écran)",
        "x1": 0,
        "y1": int(1520 * scale_y),
        "x2": width,
        "y2": height,
    }

    safe_box = {
        "name": "Safe Zone Optimale (Textes & Visages)",
        "x1": int(60 * scale_x),
        "y1": int(220 * scale_y),
        "x2": int(870 * scale_x),
        "y2": int(1500 * scale_y),
    }

    return {
        "top_bar": top_bar,
        "right_sidebar": right_sidebar,
        "bottom_bar": bottom_bar,
        "safe_box": safe_box,
    }


def render_tiktok_overlay(frame_rgb: np.ndarray, opacity: float = 0.85) -> np.ndarray:
    """
    Superpose l'interface graphique de TikTok (icônes, texte factice, zones d'alerte)
    sur une image RGB NumPy.
    """
    height, width, _ = frame_rgb.shape
    base_img = Image.fromarray(frame_rgb).convert("RGBA")
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    scale_x = width / 1080.0
    scale_y = height / 1920.0
    zones = get_tiktok_safe_zone_rects(width, height)

    # 1. Dessiner des zones d'avertissement translucides légères
    # Zone morte droite (rouge translucide)
    r = zones["right_sidebar"]
    draw.rectangle([r["x1"], r["y1"], r["x2"], r["y2"]], fill=(255, 50, 50, int(45 * opacity)))

    # Zone morte basse (rouge translucide)
    b = zones["bottom_bar"]
    draw.rectangle([b["x1"], b["y1"], b["x2"], b["y2"]], fill=(255, 50, 50, int(45 * opacity)))

    # Zone morte haute
    t = zones["top_bar"]
    draw.rectangle([t["x1"], t["y1"], t["x2"], t["y2"]], fill=(255, 50, 50, int(45 * opacity)))

    # 2. Contour de la Safe Zone (Vert / Cyan pointillé)
    s = zones["safe_box"]
    draw.rectangle(
        [s["x1"], s["y1"], s["x2"], s["y2"]],
        outline=(0, 240, 180, int(220 * opacity)),
        width=max(2, int(3 * scale_x)),
    )

    # 3. Éléments d'interface réalistes TikTok
    # Top Bar: Live, Pour toi, Recherche
    font_size_sm = max(12, int(28 * scale_x))
    font_size_xs = max(10, int(22 * scale_x))

    # Texte haut
    draw.text((int(60 * scale_x), int(70 * scale_y)), "LIVE", fill=(255, 255, 255, int(200 * opacity)))
    draw.text((int(width * 0.42), int(70 * scale_y)), "Pour toi", fill=(255, 255, 255, int(250 * opacity)))
    draw.text((int(width - 120 * scale_x), int(70 * scale_y)), "🔍", fill=(255, 255, 255, int(220 * opacity)))

    # Boutons d'interaction à droite
    icons = [
        ("👤", "+", int(780 * scale_y)),
        ("❤️", "84.2K", int(940 * scale_y)),
        ("💬", "1.4K", int(1100 * scale_y)),
        ("🔖", "12.8K", int(1260 * scale_y)),
        ("↗️", "5.6K", int(1420 * scale_y)),
        ("🎵", "", int(1580 * scale_y)),
    ]

    center_x = int(980 * scale_x)
    for icon, label, y_pos in icons:
        # Cercle ou icône
        circle_radius = int(36 * scale_x)
        draw.ellipse(
            [center_x - circle_radius, y_pos - circle_radius, center_x + circle_radius, y_pos + circle_radius],
            fill=(20, 20, 25, int(150 * opacity)),
            outline=(255, 255, 255, int(180 * opacity)),
            width=max(1, int(2 * scale_x)),
        )
        draw.text(
            (center_x - int(14 * scale_x), y_pos - int(16 * scale_y)),
            icon,
            fill=(255, 255, 255, int(240 * opacity)),
        )
        if label:
            draw.text(
                (center_x - int(24 * scale_x), y_pos + circle_radius + int(6 * scale_y)),
                label,
                fill=(255, 255, 255, int(230 * opacity)),
            )

    # Bas de page : Nom d'utilisateur & Légende factice
    draw.text(
        (int(40 * scale_x), int(1600 * scale_y)),
        "@votre_compte_tiktok",
        fill=(255, 255, 255, int(240 * opacity)),
    )
    draw.text(
        (int(40 * scale_x), int(1660 * scale_y)),
        "Votre description ici... #fyp #viral #pourtoi",
        fill=(230, 230, 230, int(200 * opacity)),
    )
    draw.text(
        (int(40 * scale_x), int(1720 * scale_y)),
        "🎵 Son original - Votre Compte",
        fill=(200, 200, 200, int(180 * opacity)),
    )

    # Étiquette Safe Zone
    draw.text(
        (s["x1"] + int(15 * scale_x), s["y1"] + int(15 * scale_y)),
        "✅ SAFE ZONE TIKTOK (Placez textes, visages et sous-titres ici)",
        fill=(0, 240, 180, int(240 * opacity)),
    )

    # Fusion avec l'image d'origine
    combined = Image.alpha_composite(base_img, overlay)
    return np.array(combined.convert("RGB"))
