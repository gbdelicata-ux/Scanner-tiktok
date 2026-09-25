"""
Module 'Dossier Magique' (Hot Folder 100% Zéro Clic) pour Mac.
Surveille en continu un dossier local. Dès qu'une vidéo y est déposée :
1. Analyse et conversion automatique en 9:16 HD (fond flou dynamique + coupe silence).
2. Dépôt immédiat dans le dossier Google Drive cible ('AIvidéo').
3. Déplacement du fichier source dans le sous-dossier 'traitees/'.
4. Notification visuelle et sonore native macOS sur le bureau de Gilbert.
"""

import os
import sys
import time
import shutil
import logging
import subprocess
from datetime import datetime
from typing import Optional, List, Dict, Any

from converter import TikTokVideoConverter
from analyzer import TikTokVideoAnalyzer
from gdrive_uploader import upload_video_to_gdrive, is_gdrive_configured

# Configuration par défaut du dossier
DEFAULT_WATCH_DIR = os.path.expanduser("~/Movies/A_CONVERTIR_TIKTOK")
LOCAL_WATCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "A_CONVERTIR_TIKTOK")

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "magic_folder.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("MagicFolder")


def send_macos_notification(title: str, message: str, sound: str = "Glass"):
    """Envoie une notification native macOS."""
    if sys.platform == "darwin":
        apple_script = f'''display notification "{message}" with title "{title}" sound name "{sound}"'''
        try:
            subprocess.run(["osascript", "-e", apple_script], check=False)
        except Exception as e:
            logger.warning(f"Erreur notification macOS: {e}")


def is_file_ready(file_path: str, wait_seconds: float = 1.5) -> bool:
    """Vérifie que la copie du fichier est bien terminée (taille stable)."""
    try:
        initial_size = os.path.getsize(file_path)
        time.sleep(wait_seconds)
        current_size = os.path.getsize(file_path)
        return initial_size == current_size and current_size > 0
    except Exception:
        return False


def process_single_video(video_path: str, output_dir: str) -> Dict[str, Any]:
    """Traite automatiquement une vidéo déposée."""
    logger.info(f"Début du traitement de : {os.path.basename(video_path)}")
    filename = os.path.basename(video_path)
    base_name, _ = os.path.splitext(filename)
    fixed_name = f"{base_name}_tiktok_hd.mp4"
    output_path = os.path.join(output_dir, fixed_name)

    # 1. Analyse rapide (silence et ratio)
    try:
        analyzer = TikTokVideoAnalyzer(video_path)
        report = analyzer.analyze_all()
        has_silence = report.get("audio", {}).get("initial_silence", False)
        is_9_16 = report.get("technical", {}).get("is_9_16", False)
    except Exception as e:
        logger.warning(f"Analyse préliminaire impossible : {e}, conversion standard appliquée.")
        has_silence = False
        is_9_16 = False

    mode = "blur_bg" if not is_9_16 else "crop"
    trim_start = 0.4 if has_silence else 0.0

    # 2. Conversion
    converter = TikTokVideoConverter()
    res = converter.convert_to_tiktok_format(
        input_path=video_path,
        output_path=output_path,
        mode=mode,
        trim_start_sec=trim_start,
    )

    if not res.get("success"):
        logger.error(f"Échec de la conversion de {filename} : {res.get('error')}")
        send_macos_notification("Erreur TikTok Studio", f"Échec sur {filename} : {res.get('error')}", sound="Basso")
        return {"success": False, "error": res.get("error")}

    logger.info(f"Conversion réussie : {fixed_name} ({res.get('file_size_mb')} Mo)")

    # 3. Dépôt Google Drive AIvidéo
    drive_ready, _ = is_gdrive_configured()
    drive_res = None
    if drive_ready:
        logger.info(f"Dépôt de {fixed_name} dans Google Drive (AIvidéo)...")
        drive_res = upload_video_to_gdrive(output_path, destination_filename=fixed_name)
        if drive_res.get("success"):
            logger.info(f"Vidéo {fixed_name} envoyée avec succès sur Google Drive !")
            send_macos_notification(
                "🎉 Vidéo prête sur iPad & Drive !",
                f"{fixed_name} est disponible dans votre dossier AIvidéo.",
                sound="Hero",
            )
        else:
            logger.warning(f"Avertissement Google Drive: {drive_res.get('error')}")
            send_macos_notification("TikTok Studio", f"Convertie en local mais erreur Drive : {drive_res.get('error')}")
    else:
        send_macos_notification("TikTok Studio", f"Vidéo prête localement : {fixed_name}")

    return {
        "success": True,
        "input": video_path,
        "output": output_path,
        "drive": drive_res,
        "filename": fixed_name,
    }


def run_watch_loop(watch_dir: Optional[str] = None, interval_sec: float = 3.0):
    """Boucle principale de surveillance du dossier."""
    target_dir = watch_dir or LOCAL_WATCH_DIR
    os.makedirs(target_dir, exist_ok=True)
    processed_dir = os.path.join(target_dir, "traitees")
    export_dir = os.path.join(target_dir, "export_tiktok")
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(export_dir, exist_ok=True)

    logger.info("=" * 60)
    logger.info(f"🚀 Dossier Magique TikTok ACTIF.")
    logger.info(f"Dossier surveillé : {target_dir}")
    logger.info(f"Déposez vos vidéos directement dans ce dossier pour un envoi 100% auto.")
    logger.info("=" * 60)

    send_macos_notification("TikTok Studio", "Dossier Magique actif : déposez vos vidéos !")

    valid_exts = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}

    while True:
        try:
            entries = os.listdir(target_dir)
            for item in entries:
                full_path = os.path.join(target_dir, item)
                if not os.path.isfile(full_path):
                    continue

                ext = os.path.splitext(item)[1].lower()
                if ext not in valid_exts:
                    continue

                # Ignorer les fichiers temporaires
                if item.startswith(".") or item.startswith("temp_"):
                    continue

                # Vérifier que l'écriture est terminée
                if not is_file_ready(full_path):
                    continue

                # Traiter
                result = process_single_video(full_path, export_dir)

                # Déplacer la source originale dans 'traitees/' pour éviter les doublons
                dest_orig = os.path.join(processed_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}")
                try:
                    shutil.move(full_path, dest_orig)
                except Exception as e:
                    logger.warning(f"Erreur déplacement fichier source: {e}")

            time.sleep(interval_sec)

        except KeyboardInterrupt:
            logger.info("Arrêt du Dossier Magique.")
            break
        except Exception as e:
            logger.error(f"Erreur inattendue dans la boucle de surveillance: {e}")
            time.sleep(interval_sec)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Surveillant Dossier Magique TikTok")
    parser.add_argument("--dir", default=None, help="Chemin du dossier à surveiller")
    args = parser.parse_args()
    run_watch_loop(args.dir)
