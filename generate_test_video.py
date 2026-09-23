"""
Générateur d'une vidéo synthétique de test au format TikTok (9:16, 1080x1920, 12 secondes)
avec son pour valider les algorithmes d'analyse.
"""

import os
import subprocess
import cv2
import numpy as np
import imageio_ffmpeg


def generate_sample_video(output_path: str = "demo_sample.mp4"):
    width, height = 720, 1280  # 9:16 optimisé pour test rapide
    fps = 30
    duration_sec = 12
    total_frames = int(fps * duration_sec)

    temp_raw_video = "temp_raw.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(temp_raw_video, fourcc, fps, (width, height))

    # Génération des images : un objet en mouvement (type fusée / météore)
    for i in range(total_frames):
        t = i / fps
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Fond spatial dégradé
        frame[:, :, 0] = np.clip(10 + int(i * 0.05), 0, 50)  # B
        frame[:, :, 2] = np.clip(20 + int(i * 0.1), 0, 60)   # R

        # Trajectoire d'une fusée / météore
        pos_y = int((t / duration_sec) * (height - 200)) + 100
        pos_x = int(width / 2 + 100 * np.sin(t * 3))

        # Trainée lumineuse
        cv2.circle(frame, (pos_x, pos_y), 30, (0, 165, 255), -1)
        cv2.circle(frame, (pos_x, pos_y), 15, (255, 255, 255), -1)

        # Texte au centre dans la Safe Zone
        cv2.putText(
            frame,
            "TEST COLLISION 2026",
            (int(width * 0.15), int(height * 0.45)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        out.write(frame)

    out.release()

    # Génération d'une piste audio synthétique (bip/sonorité) via ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    temp_audio = "temp_audio.wav"

    # Génération d'un bip de 12 secondes avec ffmpeg (sinus 440Hz + bruit)
    cmd_audio = [
        ffmpeg_exe,
        "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency=220:duration={duration_sec}",
        temp_audio,
    ]
    subprocess.run(cmd_audio, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Fusion vidéo + audio avec encodage H.264 compatible web
    cmd_mux = [
        ffmpeg_exe,
        "-y",
        "-i", temp_raw_video,
        "-i", temp_audio,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    subprocess.run(cmd_mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Nettoyage des fichiers temporaires
    for f in [temp_raw_video, temp_audio]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    print(f"Vidéo de démonstration générée avec succès : {output_path}")


if __name__ == "__main__":
    generate_sample_video()
