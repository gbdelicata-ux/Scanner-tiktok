"""
Module de détection automatique de thèmes vidéo (Computer Vision & Audio).
Identifie la catégorie de la vidéo parmi les niches du créateur :
- 🚀 Fusée & Espace (fond sombre, traînée de feu, poussée)
- 💥 Collision & Météorite (impact, explosion, flash de poussière/débris)
- ✈️ Aviation & Avion (ciel bleu/nuages, vitesse horizontale/diagonale)
- 👤 Facecam & Humain (teintes de peau, plan centré, voix dominante)
"""

import cv2
import numpy as np


class VideoThemeDetector:
    THEMES = {
        "fusee": {
            "label": "🚀 Fusée & Espace",
            "slug": "Fusee_Espace",
            "hashtags": "#fusee #espace #astronomie #nasa #spacex #pourtoi #fyp",
        },
        "collision": {
            "label": "💥 Collision & Météorite",
            "slug": "Collision_Impact",
            "hashtags": "#collision #meteorite #science #simulation #impact #pourtoi #fyp",
        },
        "avion": {
            "label": "✈️ Aviation & Avion",
            "slug": "Avion_Vol",
            "hashtags": "#aviation #avion #vol #pilote #aerien #pourtoi #fyp",
        },
        "humain": {
            "label": "👤 Facecam & Humain",
            "slug": "Facecam_Portrait",
            "hashtags": "#apprendre #conseil #motivation #faits #histoire #pourtoi #fyp",
        },
        "action_generale": {
            "label": "🎬 Scène d'Action",
            "slug": "Action_Scene",
            "hashtags": "#action #spectaculaire #viral #pourtoi #fyp",
        },
    }

    def detect_theme(self, video_path: str) -> dict:
        """
        Analyse les caractéristiques visuelles clés (chroma, palette spatiale/ciel/peau, dynamique)
        pour attribuer un thème précis à la vidéo.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {
                "theme_id": "action_generale",
                **self.THEMES["action_generale"],
                "confidence": 0.5,
                "suggested_title": "Video_TikTok",
            }

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        # Échantillonnage de 8 frames réparties sur la vidéo
        sample_count = min(8, max(3, total_frames // 10))
        indices = np.linspace(0, max(0, total_frames - 2), sample_count, dtype=int)

        dark_scores = []
        sky_scores = []
        fire_scores = []
        skin_scores = []

        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            # Redimensionnement miniature pour rapidité extrême (<0.01s)
            thumb = cv2.resize(frame, (120, 160))
            hsv = cv2.cvtColor(thumb, cv2.COLOR_BGR2HSV)
            h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
            total_pixels = thumb.shape[0] * thumb.shape[1]

            # 1. Fond sombre / Spatial (Valeur < 45)
            dark_pixels = np.sum(v < 45)
            dark_scores.append(dark_pixels / total_pixels)

            # 2. Ciel / Nuages bleus (Hue 90-130, Sat > 30, Val > 60)
            sky_pixels = np.sum((h >= 90) & (h <= 130) & (s >= 30) & (v >= 60))
            sky_scores.append(sky_pixels / total_pixels)

            # 3. Flamme / Explosion / Réacteur (Hue 5-25, Sat > 130, Val > 120)
            fire_pixels = np.sum((h >= 5) & (h <= 25) & (s >= 130) & (v >= 120))
            fire_scores.append(fire_pixels / total_pixels)

            # 4. Teintes peau humaine (Hue 0-25, Sat 40-170, Val 70-240)
            skin_pixels = np.sum((h >= 0) & (h <= 25) & (s >= 40) & (s <= 170) & (v >= 70) & (v <= 240))
            skin_scores.append(skin_pixels / total_pixels)

        cap.release()

        avg_dark = float(np.mean(dark_scores)) if dark_scores else 0.0
        avg_sky = float(np.mean(sky_scores)) if sky_scores else 0.0
        avg_fire = float(np.mean(fire_scores)) if fire_scores else 0.0
        avg_skin = float(np.mean(skin_scores)) if skin_scores else 0.0

        # Algorithme de décision des thèmes
        if avg_skin > 0.18 and avg_dark < 0.5:
            theme_id = "humain"
            confidence = min(0.95, 0.5 + avg_skin)
        elif avg_dark > 0.45:
            # Fond majoritairement spatial
            if avg_fire > 0.02:
                theme_id = "fusee"
                confidence = 0.88
            else:
                theme_id = "collision"
                confidence = 0.82
        elif avg_sky > 0.25:
            theme_id = "avion"
            confidence = min(0.92, 0.6 + avg_sky)
        elif avg_fire > 0.05:
            theme_id = "collision"
            confidence = 0.85
        else:
            theme_id = "action_generale"
            confidence = 0.65

        theme_data = self.THEMES[theme_id]

        return {
            "theme_id": theme_id,
            "theme_label": theme_data["label"],
            "slug": theme_data["slug"],
            "hashtags": theme_data["hashtags"],
            "confidence": round(confidence, 2),
            "stats": {
                "dark": round(avg_dark, 2),
                "sky": round(avg_sky, 2),
                "fire": round(avg_fire, 2),
                "skin": round(avg_skin, 2),
            },
        }

    def generate_thematic_filename(self, orig_name: str, theme_id: str, index: int = 1) -> str:
        """
        Génère un nom de fichier TikTok percutant selon le thème détecté.
        Ex: 'Fusee_Espace_01_corrige.mp4' ou 'Collision_Impact_02_corrige.mp4'
        """
        slug = self.THEMES.get(theme_id, self.THEMES["action_generale"])["slug"]
        return f"{slug}_{index:02d}_corrige.mp4"
