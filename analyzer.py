"""
Moteur d'analyse algorithmique et technique pour vidéos TikTok.
Évalue le format, le dynamisme visuel des 3 premières secondes (Hook),
l'audio (silences au départ), le potentiel de boucle (Loop) et la Safe Zone.
"""

import os
import subprocess
import tempfile
import cv2
import numpy as np
import imageio_ffmpeg
from safe_zone import get_tiktok_safe_zone_rects, render_tiktok_overlay


class TikTokVideoAnalyzer:
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def analyze_all(self, content_style: str = "statique") -> dict:
        """
        Exécute la batterie complète de tests et calcule le Score TikTok (/100).
        content_style: 'statique' (visages/personnes) ou 'action' (fusées/catastrophes/CGI).
        """
        tech_data = self._analyze_technical()
        if "error" in tech_data:
            return tech_data

        hook_data = self._analyze_hook_dynamism(tech_data["fps"], tech_data["duration"])
        audio_data = self._analyze_audio()
        loop_data = self._analyze_loop_potential(tech_data["total_frames"])

        # Calcul des scores par pilier
        score_tech, tech_checks = self._score_technical(tech_data)
        score_hook, hook_checks = self._score_hook(hook_data, content_style)
        score_audio, audio_checks = self._score_audio(audio_data)
        score_retention, retention_checks = self._score_retention(tech_data, loop_data, content_style)

        overall_score = int(score_tech + score_hook + score_audio + score_retention)
        overall_score = max(5, min(100, overall_score))

        # Recommandations personnalisées
        recommendations = self._generate_recommendations(
            tech_checks, hook_checks, audio_checks, retention_checks, content_style, tech_data
        )

        return {
            "overall_score": overall_score,
            "technical": tech_data,
            "hook": hook_data,
            "audio": audio_data,
            "loop": loop_data,
            "scores": {
                "technical": score_tech,
                "hook": score_hook,
                "audio": score_audio,
                "retention": score_retention,
            },
            "checks": {
                "technical": tech_checks,
                "hook": hook_checks,
                "audio": audio_checks,
                "retention": retention_checks,
            },
            "recommendations": recommendations,
        }

    def _analyze_technical(self) -> dict:
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            return {"error": "Impossible d'ouvrir le fichier vidéo."}

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        cap.release()

        aspect_ratio = width / height if height > 0 else 0
        is_9_16 = 0.54 <= aspect_ratio <= 0.58  # 9/16 = 0.5625

        return {
            "width": width,
            "height": height,
            "fps": round(fps, 2),
            "total_frames": total_frames,
            "duration": round(duration, 2),
            "aspect_ratio": round(aspect_ratio, 3),
            "is_9_16": is_9_16,
            "resolution_label": f"{width}x{height}",
        }

    def _analyze_hook_dynamism(self, fps: float, duration: float) -> dict:
        """
        Mesure la variation de mouvement (dynamisme visuel) sur les 3 premières secondes.
        Un score faible sur un plan statique = fort risque de drop immédiat.
        """
        cap = cv2.VideoCapture(self.video_path)
        max_duration = min(3.0, duration)
        frames_to_sample = int(max_duration * fps)

        # Échantillonnage à 5 fps pour comparer le mouvement
        step = max(1, int(fps / 5))
        diffs = []
        prev_gray = None
        frame_idx = 0

        first_frame = None

        while cap.isOpened() and frame_idx < frames_to_sample:
            ret, frame = cap.read()
            if not ret:
                break

            if first_frame is None:
                first_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            if frame_idx % step == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (160, 284))  # miniature pour rapidité
                if prev_gray is not None:
                    # Différence absolue moyenne entre deux images
                    diff = np.mean(np.abs(gray.astype(float) - prev_gray.astype(float)))
                    diffs.append(diff)
                prev_gray = gray

            frame_idx += 1

        cap.release()

        avg_motion = float(np.mean(diffs)) if diffs else 0.0
        max_motion = float(np.max(diffs)) if diffs else 0.0

        # Classification du dynamisme
        if avg_motion < 2.5:
            status = "tres_statique"
            label = "Plan très statique (aucun cut ni zoom détecté)"
        elif avg_motion < 7.0:
            status = "modere"
            label = "Mouvement modéré (stabilité correcte mais hook doux)"
        else:
            status = "dynamique"
            label = "Très dynamique (fort changement visuel)"

        return {
            "avg_motion": round(avg_motion, 2),
            "max_motion": round(max_motion, 2),
            "status": status,
            "label": label,
            "first_frame": first_frame,
        }

    def _analyze_audio(self) -> dict:
        """
        Extrait la piste audio et analyse :
        1. Présence d'une piste sonore.
        2. Silence dans les 0.5 premières secondes (départ mort).
        3. Volume moyen / saturation.
        """
        temp_wav = tempfile.mktemp(suffix=".wav")
        try:
            # Extraction audio brute via ffmpeg intégré
            cmd = [
                self.ffmpeg_exe,
                "-y",
                "-i", self.video_path,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                temp_wav,
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) < 500:
                return {
                    "has_audio": False,
                    "initial_silence": True,
                    "energy": 0,
                    "label": "Aucune piste audio détectée (Critique pour l'algorithme)",
                }

            # Lecture du fichier WAV
            with open(temp_wav, "rb") as f:
                # Saut de l'en-tête WAV (44 octets)
                f.seek(44)
                raw_data = f.read()

            audio_samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
            if len(audio_samples) == 0:
                return {"has_audio": False, "initial_silence": True, "energy": 0, "label": "Audio vide"}

            # Normalisation
            audio_samples = audio_samples / 32768.0

            # Vérification des 0.5 premières secondes (8000 échantillons à 16kHz)
            first_half_sec = audio_samples[: min(8000, len(audio_samples))]
            initial_rms = float(np.sqrt(np.mean(first_half_sec**2))) if len(first_half_sec) > 0 else 0.0

            overall_rms = float(np.sqrt(np.mean(audio_samples**2)))

            has_intro_silence = initial_rms < 0.015

            return {
                "has_audio": True,
                "initial_silence": has_intro_silence,
                "initial_rms": round(initial_rms, 4),
                "overall_rms": round(overall_rms, 4),
                "label": "Silence au démarrage détecté" if has_intro_silence else "Entrée audio immédiate",
            }

        except Exception as e:
            return {
                "has_audio": False,
                "error": str(e),
                "label": "Erreur lors de l'analyse audio",
            }
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass

    def _analyze_loop_potential(self, total_frames: int) -> dict:
        """
        Compare la première et la dernière frame pour évaluer si la vidéo peut
        boucler de manière invisible (secret des vidéos virales de 10-20s).
        """
        cap = cv2.VideoCapture(self.video_path)
        first_frame = None
        last_frame = None

        if total_frames > 2:
            # Première frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame1 = cap.read()
            if ret:
                first_frame = cv2.resize(cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY), (120, 213))

            # Dernière frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total_frames - 2))
            ret, frame2 = cap.read()
            if ret:
                last_frame = cv2.resize(cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY), (120, 213))

        cap.release()

        if first_frame is not None and last_frame is not None:
            # Corrélation de couleur/structure
            hist1 = cv2.calcHist([first_frame], [0], None, [32], [0, 256])
            hist2 = cv2.calcHist([last_frame], [0], None, [32], [0, 256])
            cv2.normalize(hist1, hist1)
            cv2.normalize(hist2, hist2)
            similarity = float(cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL))
        else:
            similarity = 0.0

        is_seamless = similarity > 0.85
        return {
            "loop_similarity": round(max(0.0, similarity), 2),
            "is_seamless": is_seamless,
            "label": "Boucle quasi-invisible (Boucle infinie)" if is_seamless else "Fin et début distincts",
        }

    # --- Moteurs de Notation ---

    def _score_technical(self, tech: dict) -> tuple:
        score = 25
        checks = []

        # Ratio 9:16
        if tech["is_9_16"]:
            checks.append({"name": "Format 9:16 vertical", "status": "ok", "msg": "Parfait pour l'affichage plein écran mobile."})
        else:
            score -= 15
            checks.append({"name": "Format 9:16 vertical", "status": "error", "msg": f"Votre ratio est de {tech['aspect_ratio']}. TikTok pénalise lourdement les formats horizontaux ou carrés."})

        # Résolution
        if tech["height"] >= 1080 and tech["width"] >= 720:
            checks.append({"name": "Qualité HD (>= 1080p)", "status": "ok", "msg": f"Résolution nette ({tech['resolution_label']})."})
        else:
            score -= 5
            checks.append({"name": "Qualité HD", "status": "warn", "msg": f"Résolution faible ({tech['resolution_label']}). Visez 1080x1920."})

        # Durée (idéal 10s-30s)
        if 8 <= tech["duration"] <= 35:
            checks.append({"name": "Durée stratégique (10-30s)", "status": "ok", "msg": f"{tech['duration']}s : Excellent format pour maximiser le taux de complétion (>60%)."})
        elif tech["duration"] < 8:
            score -= 3
            checks.append({"name": "Durée vidéo", "status": "warn", "msg": f"{tech['duration']}s : Très court. L'algorithme exigera >80% de complétion."})
        else:
            score -= 3
            checks.append({"name": "Durée vidéo", "status": "warn", "msg": f"{tech['duration']}s : Format plus long. Nécessite des relances de rythme toutes les 5s."})

        return max(0, score), checks

    def _score_hook(self, hook: dict, style: str) -> tuple:
        score = 35
        checks = []

        if hook["status"] == "dynamique":
            checks.append({"name": "Dynamisme du Hook (0-3s)", "status": "ok", "msg": "Excellente variation visuelle dès l'entrée ! Capture l'attention."})
        elif hook["status"] == "modere":
            score -= 10
            checks.append({"name": "Dynamisme du Hook (0-3s)", "status": "warn", "msg": "Variation moyenne. Risque de décrochage sur les 2 premières secondes."})
        else:
            score -= 20
            if style == "statique":
                checks.append({"name": "Dynamisme du Hook (0-3s)", "status": "error", "msg": "Plan 100% immobile détecté au départ ! Cause n°1 du blocage à 800 vues."})
            else:
                checks.append({"name": "Dynamisme du Hook (0-3s)", "status": "error", "msg": "Départ trop lent pour une vidéo d'action/catastrophe. L'impact visuel doit frapper immédiatement."})

        return max(0, score), checks

    def _score_audio(self, audio: dict) -> tuple:
        score = 20
        checks = []

        if not audio.get("has_audio", False):
            score -= 20
            checks.append({"name": "Piste sonore", "status": "error", "msg": "Aucun son détecté. 95% des vidéos virales reposent sur un audio ou une voix claire."})
            return 0, checks

        checks.append({"name": "Piste sonore active", "status": "ok", "msg": "Audio présent."})

        if audio.get("initial_silence", False):
            score -= 10
            checks.append({"name": "Silence d'intro (0-0.5s)", "status": "error", "msg": "Un blanc audio est détecté au tout début ! Coupez ce temps mort au montage."})
        else:
            checks.append({"name": "Entrée audio immédiate", "status": "ok", "msg": "Pas de temps mort au départ."})

        return max(0, score), checks

    def _score_retention(self, tech: dict, loop: dict, style: str) -> tuple:
        score = 20
        checks = []

        if loop.get("is_seamless", False):
            score += 0  # plein score
            checks.append({"name": "Potentiel de boucle infinie (Loop)", "status": "ok", "msg": "La fin s'enchaîne avec le début (+15% de watchtime estimé)."})
        else:
            score -= 6
            checks.append({"name": "Potentiel de boucle infinie", "status": "info", "msg": "Fin classique. Une transition en boucle permettrait de dépasser 100% de complétion."})

        # Cible de complétion
        d = tech["duration"]
        if d <= 15:
            target = "70% à 80%"
        else:
            target = "50% à 65%"
        checks.append({"name": "Seuil algorithmique de rétention", "status": "info", "msg": f"Pour percer le plafond des 800 vues, ce format {d}s requiert un taux de complétion d'au moins {target}."})

        return max(0, score), checks

    def _generate_recommendations(self, tech_c, hook_c, audio_c, ret_c, style: str, tech: dict) -> list:
        recs = []

        # Recommandations selon le style de vidéo
        if style == "statique":
            recs.append("🔍 **Pour vos plans statiques / personnes** : Ajoutez un léger zoom numérique progressif (punch-in zoom de 5-10%) ou changez d'angle de caméra dès la 2ème seconde pour forcer le cerveau du spectateur à rester attentif.")
            recs.append("💬 **Sous-titres animés au centre** : Les personnes statiques ont besoin de sous-titres dynamiques mot à mot au centre de l'écran (Safe Zone). 40% des utilisateurs lisent avant d'écouter.")
            recs.append("✂️ **Supprimez les respirations initiales** : Coupez la vidéo exactement à la première micro-seconde où vous commencez à parler. Tout blanc de 0.3s au départ divise le hook par 2.")
        else:
            recs.append("🚀 **Pour vos vidéos de fusées / avions / collisions** : Ne commencez jamais par une montée lente. Commencez au moment le plus intrigant (l'explosion imminente, l'angle spectaculaire) avec un texte d'accroche mystère : *'Ce qui arrive quand Mach 10 frappe l'atmosphère...'*")
            recs.append("🔊 **Sound Design percutant** : Ajoutez un effet sonore 'Whoosh' ou une basse lourde dès 0.0s pour réveiller l'attention.")
            recs.append("🔁 **L'illusion de boucle (Loop Hack)** : Faites en sorte que la collision ou la trajectoire de l'avion sorte de l'écran exactement à la même position où la vidéo recommence.")

        # Recommandations techniques générales
        if not tech["is_9_16"]:
            recs.append("⚠️ **Passez en 9:16 natif (1080x1920)** : L'algorithme pénalise les vidéos ayant des barres noires ou un format horizontal.")

        return recs
