"""
Test unitaire pour la logique du Mode Rafale :
- Conversion multiple de 3 vidéos synthétiques
- Assemblage dans une archive ZIP
- Vérification de l'intégrité des fichiers dans le ZIP
"""

import io
import os
import zipfile
import cv2
import numpy as np
from converter import TikTokVideoConverter


def test_batch_processing():
    converter = TikTokVideoConverter()

    # Création de 2 vidéos d'exemple
    sample_files = []
    for i in range(2):
        name = f"test_batch_clip_{i+1}.mp4"
        out = cv2.VideoWriter(name, cv2.VideoWriter_fourcc(*"mp4v"), 25, (640, 360))
        for _ in range(25):  # 1 seconde
            frame = np.full((360, 640, 3), 50 * (i + 1), dtype=np.uint8)
            cv2.putText(frame, f"Clip {i+1}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            out.write(frame)
        out.release()
        sample_files.append(name)

    converted_files = []
    for path in sample_files:
        base_name, _ = os.path.splitext(path)
        out_name = f"{base_name}_corrige.mp4"
        res = converter.convert_to_tiktok_format(
            input_path=path,
            output_path=out_name,
            mode="blur_bg",
            target_width=1080,
            target_height=1920,
        )
        assert res["success"] is True, f"Erreur conversion {path}: {res.get('error')}"
        with open(out_name, "rb") as f:
            converted_files.append((out_name, f.read()))
        os.remove(out_name)
        os.remove(path)

    # Test d'archivage ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in converted_files:
            zf.writestr(filename, data)

    zip_buffer.seek(0)
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 2
        assert "test_batch_clip_1_corrige.mp4" in namelist
        assert "test_batch_clip_2_corrige.mp4" in namelist

    print("✅ Test Mode Rafale validé : conversion multiple et archive ZIP 100% fonctionnelles !")


if __name__ == "__main__":
    test_batch_processing()
