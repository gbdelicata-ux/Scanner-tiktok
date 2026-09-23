"""
Module de conversion et d'optimisation vidéo pour TikTok.
Permet de transformer n'importe quelle vidéo (16:9 paysage, carrée, basse résolution)
en format optimal TikTok 9:16 (1080x1920) avec encodage H.264/AAC certifié.
"""

import os
import subprocess
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

        # Coupe du silence d'intro si demandé
        if trim_start_sec > 0:
            cmd.extend(["-ss", str(trim_start_sec)])

        cmd.extend(["-i", input_path])

        if mode == "blur_bg":
            # Fond agrandi + flou + superposition du flux original centré
            filter_complex = (
                f"[0:v]split=2[bg_in][fg_in];"
                f"[bg_in]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
                f"crop={target_width}:{target_height},"
                f"boxblur=20:5[bg];"
                f"[fg_in]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
            )
            cmd.extend(["-filter_complex", filter_complex, "-map", "[outv]", "-map", "0:a?"])
        elif mode == "crop":
            filter_complex = (
                f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
                f"crop={target_width}:{target_height}[outv]"
            )
            cmd.extend(["-filter_complex", filter_complex, "-map", "[outv]", "-map", "0:a?"])
        else:  # 'fit'
            filter_complex = (
                f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black[outv]"
            )
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
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
