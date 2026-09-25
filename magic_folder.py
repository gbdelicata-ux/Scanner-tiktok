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
import threading
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
    filename = os.path.basename(video_path)
    base_name, _ = os.path.splitext(filename)
    fixed_name = f"{base_name}_tiktok_hd.mp4"
    output_path = os.path.join(output_dir, fixed_name)

    print("\n" + "=" * 60)
    print(f"🎬 NOUVELLE VIDÉO DÉTECTÉE : {filename}")
    print("=" * 60)
    logger.info(f"Début du traitement de : {filename}")

    # 1. Analyse rapide (silence et ratio)
    print("⚙️ [1/3] Analyse du format et du silence d'introduction...")
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

    print(f"🪄 [1/3] Conversion 1080x1920 HD (Mode: {mode}, Coupe silence: {trim_start}s)...")
    converter = TikTokVideoConverter()
    res = converter.convert_to_tiktok_format(
        input_path=video_path,
        output_path=output_path,
        mode=mode,
        trim_start_sec=trim_start,
    )

    if not res.get("success"):
        logger.error(f"❌ Échec de la conversion de {filename} : {res.get('error')}")
        send_macos_notification("Erreur TikTok Studio", f"Échec sur {filename} : {res.get('error')}", sound="Basso")
        print(f"❌ Échec de conversion : {res.get('error')}")
        return {"success": False, "error": res.get("error")}

    print(f"✅ [1/3] Vidéo convertie avec succès ({res.get('file_size_mb')} Mo) !")

    # 2. Dépôt Google Drive AIvidéo
    drive_ready, drive_desc = is_gdrive_configured()
    drive_res = None
    if drive_ready:
        print(f"☁️ [2/3] Téléversement direct dans Google Drive (AIvidéo)...")
        logger.info(f"Dépôt de {fixed_name} dans Google Drive (AIvidéo)...")
        drive_res = upload_video_to_gdrive(output_path, destination_filename=fixed_name)
        if drive_res.get("success"):
            print(f"🎉 [3/3] SUCCÈS ! Vidéo disponible dans votre dossier Google Drive AIvidéo !")
            logger.info(f"Vidéo {fixed_name} envoyée avec succès sur Google Drive !")
            send_macos_notification(
                "🎉 Vidéo prête sur iPad & Drive !",
                f"{fixed_name} est disponible dans votre dossier AIvidéo.",
                sound="Hero",
            )
        else:
            print(f"⚠️ [2/3] Erreur Google Drive : {drive_res.get('error')}")
            logger.warning(f"Avertissement Google Drive: {drive_res.get('error')}")
            send_macos_notification("TikTok Studio", f"Convertie en local mais erreur Drive : {drive_res.get('error')}")
    else:
        print(f"📁 [2/3] Google Drive non configuré, vidéo enregistrée en local : {output_path}")
        send_macos_notification("TikTok Studio", f"Vidéo prête localement : {fixed_name}")

    print("=" * 60)
    print("👀 Retour en veille : déposez une autre vidéo quand vous le souhaitez.\n")
    return {
        "success": True,
        "input": video_path,
        "output": output_path,
        "drive": drive_res,
        "filename": fixed_name,
    }


def _interactive_test_listener(target_dir: str):
    """Permet à l'utilisateur d'appuyer sur Entrée pour injecter une vidéo test."""
    while True:
        try:
            user_input = sys.stdin.readline()
            if not user_input:
                break
            demo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_sample.mp4")
            if os.path.exists(demo_path):
                dest_demo = os.path.join(target_dir, f"test_demo_{int(time.time())}.mp4")
                print("\n🧪 [TEST DEMO DÉCLENCHÉ] Copie de la vidéo démo dans le Dossier Magique...")
                shutil.copy2(demo_path, dest_demo)
            else:
                print("\n⚠️ Fichier demo_sample.mp4 introuvable.")
        except Exception:
            break


def run_watch_loop(watch_dir: Optional[str] = None, interval_sec: float = 2.0, interactive: bool = False):
    """Boucle principale de surveillance du dossier."""
    target_dir = watch_dir or LOCAL_WATCH_DIR
    os.makedirs(target_dir, exist_ok=True)
    processed_dir = os.path.join(target_dir, "traitees")
    export_dir = os.path.join(target_dir, "export_tiktok")
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(export_dir, exist_ok=True)

    # Ouvrir et activer la fenêtre du dossier dans le Finder si macOS
    if sys.platform == "darwin":
        try:
            subprocess.run([
                "osascript",
                "-e", 'tell application "Finder" to activate',
                "-e", f'tell application "Finder" to open POSIX file "{target_dir}"',
            ], check=False)
        except Exception:
            pass

    print("=" * 60)
    print("🚀 DOSSIER MAGIQUE TIKTOK STUDIO (EN VEILLE ACTIVE)")
    print(f"📂 Dossier surveillé : {target_dir}")
    print("👉 Glissez une vidéo (.mp4 ou .mov) dans ce dossier Finder.")
    print("💡 Appuyez sur [ENTRÉE] dans ce terminal pour tester avec une démo !")
    print("=" * 60)

    send_macos_notification("TikTok Studio", "Dossier Magique actif : fenêtre Finder ouverte !")

    valid_exts = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}

    # Lancer le thread de test interactif si demandé
    if interactive or sys.stdin.isatty():
        t = threading.Thread(target=_interactive_test_listener, args=(target_dir,), daemon=True)
        t.start()

    loop_count = 0
    while True:
        try:
            entries = os.listdir(target_dir)
            files_to_process = [
                f for f in entries
                if os.path.isfile(os.path.join(target_dir, f))
                and os.path.splitext(f)[1].lower() in valid_exts
                and not f.startswith(".")
                and not f.startswith("temp_")
            ]

            if files_to_process:
                for item in files_to_process:
                    full_path = os.path.join(target_dir, item)
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
            else:
                loop_count += 1
                if loop_count % 6 == 0:  # Toutes les ~12 secondes
                    now_str = datetime.now().strftime("%H:%M:%S")
                    print(f"[{now_str}] ⏳ En veille active : glissez une vidéo dans 'A_CONVERTIR_TIKTOK' (ou tapez Entrée pour tester)...")

            time.sleep(interval_sec)

        except KeyboardInterrupt:
            print("\n👋 Arrêt du Dossier Magique. À bientôt !")
            break
        except Exception as e:
            logger.error(f"Erreur inattendue dans la boucle de surveillance: {e}")
            time.sleep(interval_sec)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Surveillant Dossier Magique TikTok")
    parser.add_argument("--dir", default=None, help="Chemin du dossier à surveiller")
    parser.add_argument("--interactive", action="store_true", help="Active l'écoute des touches du clavier pour test démo")
    args = parser.parse_args()
    run_watch_loop(args.dir, interactive=args.interactive)
