"""
Test unitaire pour le convertisseur TikTok.
Crée un clip 16:9 paysage et vérifie la conversion en 9:16 avec fond flou et recadrage centré.
"""

import os
import subprocess
import cv2
import numpy as np
import imageio_ffmpeg
from converter import TikTokVideoConverter


def test_conversion():
    # 1. Créer une vidéo 16:9 paysage de 3 secondes
    test_16_9 = "test_horizontal_16_9.mp4"
    width, height = 640, 360  # 16:9
    fps = 30
    out = cv2.VideoWriter(test_16_9, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for i in range(fps * 3):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Balle se déplaçant horizontalement
        x = int((i / (fps * 3)) * (width - 100)) + 50
        cv2.circle(frame, (x, height // 2), 40, (0, 255, 255), -1)
        cv2.putText(frame, "HORIZONTAL 16:9", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        out.write(frame)
    out.release()

    # Ajouter une piste audio minimale
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    test_16_9_audio = "test_horizontal_audio.mp4"
    subprocess.run([
        ffmpeg_exe, "-y",
        "-i", test_16_9,
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "copy", "-c:a", "aac",
        test_16_9_audio
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    converter = TikTokVideoConverter()

    # Test 1 : Conversion fond flouté (blur_bg)
    out_blur = "test_out_blur_9_16.mp4"
    res_blur = converter.convert_to_tiktok_format(
        test_16_9_audio,
        out_blur,
        mode="blur_bg",
        target_width=1080,
        target_height=1920
    )
    assert res_blur["success"], f"Erreur blur_bg: {res_blur.get('error')}"
    assert os.path.exists(out_blur), "Fichier out_blur non créé"

    # Vérification des dimensions du fichier converti
    cap = cv2.VideoCapture(out_blur)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    assert w == 1080 and h == 1920, f"Dimensions incorrectes: {w}x{h}"
    print(f"✅ Conversion fond flouté réussie : {w}x{h}, taille: {res_blur['file_size_mb']} Mo")

    # Test 2 : Conversion recadrage centré (crop)
    out_crop = "test_out_crop_9_16.mp4"
    res_crop = converter.convert_to_tiktok_format(
        test_16_9_audio,
        out_crop,
        mode="crop",
        target_width=1080,
        target_height=1920
    )
    assert res_crop["success"], f"Erreur crop: {res_crop.get('error')}"
    assert os.path.exists(out_crop), "Fichier out_crop non créé"
    print(f"✅ Conversion recadrage centré réussie : taille: {res_crop['file_size_mb']} Mo")

    # Nettoyage des tests
    for f in [test_16_9, test_16_9_audio, out_blur, out_crop]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    print("\n🎉 TOUS LES TESTS DU CONVERTISSEUR SONT VALIDÉS !")


if __name__ == "__main__":
    test_conversion()
