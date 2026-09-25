"""
Module de conversion et d'optimisation vidéo pour TikTok.
Permet de transformer n'importe quelle vidéo (16:9 paysage, carrée, basse résolution)
en format optimal TikTok 9:16 (1080x1920) avec encodage H.264/AAC certifié,
découpage de rétention (12-18s) et incrustation d'accroches visuelles.
"""

import os
import subprocess
import tempfile
from typing import Optional, Dict, Any, Tuple
import imageio_ffmpeg


class TikTokVideoConverter:
    def __init__(self):
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def convert_to_tiktok_format(
        self,
        input_path: str,
        output_path: str,
        mode: str = "blur_bg",
        trim_start_sec: float = 0.0,
        duration_sec: Optional[float] = None,
        hook_text: Optional[str] = None,
        hook_style: str = "yellow_impact",
        hook_duration: float = 2.5,
        target_width: int = 1080,
        target_height: int = 1920,
    ) -> dict:
        """
        Convertit une vidéo au format TikTok 9:16.
        Modes :
        - 'blur_bg' : Arrière-plan flouté dynamique (idéal pour les vidéos 16:9 d'avions/fusées/cinéma)
        - 'crop' : Recadrage centré plein écran 9:16 (zoom sans aucune bande)
        - 'fit' : Ajustement direct avec bandes noires
        """
        if not os.path.exists(input_path):
            return {"success": False, "error": "Fichier source introuvable."}

        cmd = [self.ffmpeg_exe, "-y"]

        # Coupe du silence d'intro ou point de départ si demandé
        if trim_start_sec > 0:
            cmd.extend(["-ss", str(trim_start_sec)])

        # Durée limitée (pour le découpeur de rétention 12-18s)
        if duration_sec is not None and duration_sec > 0:
            cmd.extend(["-t", str(duration_sec)])

        cmd.extend(["-i", input_path])

        # Préparation du bandeau d'accroche si demandé
        hook_png_path = None
        if hook_text and hook_text.strip():
            from hook_generator import create_hook_banner_image
            hook_png_path = tempfile.mktemp(suffix="_hook.png")
            banner_img = create_hook_banner_image(hook_text.strip(), style_key=hook_style, target_width=target_width, target_height=target_height)
            banner_img.save(hook_png_path, format="PNG")
            cmd.extend(["-i", hook_png_path])

        if mode == "blur_bg":
            # Fond agrandi + flou + superposition du flux original centré
            base_filter = (
                f"[0:v]split=2[bg_in][fg_in];"
                f"[bg_in]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
                f"crop={target_width}:{target_height},"
                f"boxblur=20:5[bg];"
                f"[fg_in]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2[basev]"
            )
        elif mode == "crop":
            base_filter = (
                f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
                f"crop={target_width}:{target_height}[basev]"
            )
        else:  # 'fit'
            base_filter = (
                f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black[basev]"
            )

        if hook_png_path:
            # Superposer le calque d'accroche sur basev pendant les N premières secondes
            filter_complex = f"{base_filter};[basev][1:v]overlay=0:0:enable='between(t,0,{hook_duration})'[outv]"
        else:
            filter_complex = f"{base_filter};[basev]copy[outv]"

        cmd.extend(["-filter_complex", filter_complex, "-map", "[outv]", "-map", "0:a?"])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",  # Haute qualité visuelle sans fichier trop lourd
            "-pix_fmt", "yuv420p",  # Compatibilité maximale smartphone
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-movflags", "+faststart",  # Lecture immédiate sans buffering TikTok
            output_path,
        ])

        try:
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if process.returncode != 0:
                return {
                    "success": False,
                    "error": f"Erreur FFmpeg: {process.stderr[-300:] if process.stderr else 'Inconnue'}",
                }

            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                return {"success": False, "error": "Le fichier de sortie n'a pas pu être créé."}

            file_size_mb = round(os.path.getsize(output_path) / (1024 * 1024), 2)
            return {
                "success": True,
                "output_path": output_path,
                "file_size_mb": file_size_mb,
                "resolution": f"{target_width}x{target_height}",
                "mode": mode,
                "duration_cut": duration_sec,
                "has_hook": bool(hook_png_path),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if hook_png_path and os.path.exists(hook_png_path):
                try:
                    os.remove(hook_png_path)
                except Exception:
                    pass

    def generate_ab_variants(
        self,
        input_path: str,
        output_dir: str,
        mode: str = "blur_bg",
        total_duration: float = 30.0,
        hook_a: str = "🚀 Regardez bien à la 5e seconde...",
        hook_b: str = "😱 Ce que personne ne vous a dit :",
    ) -> Dict[str, Any]:
        """
        Génère automatiquement 2 variantes courtes pour l'A/B testing TikTok :
        - Variante A : 14 secondes du début (Hook immédiat)
        - Variante B : 15 secondes au milieu / pic d'action
        """
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        out_a = os.path.join(output_dir, f"{base_name}_VARIANTE_A_express14s.mp4")
        out_b = os.path.join(output_dir, f"{base_name}_VARIANTE_B_action15s.mp4")

        # Variante A : 0s à 14s
        res_a = self.convert_to_tiktok_format(
            input_path=input_path,
            output_path=out_a,
            mode=mode,
            trim_start_sec=0.0,
            duration_sec=14.0,
            hook_text=hook_a,
            hook_style="yellow_impact",
        )

        # Variante B : milieu à milieu+15s
        mid_start = max(0.0, (total_duration / 2.0) - 7.5) if total_duration > 15 else 0.0
        res_b = self.convert_to_tiktok_format(
            input_path=input_path,
            output_path=out_b,
            mode=mode,
            trim_start_sec=mid_start,
            duration_sec=15.0,
            hook_text=hook_b,
            hook_style="cyber_cyan",
        )

        return {
            "variant_a": res_a,
            "variant_b": res_b,
        }
