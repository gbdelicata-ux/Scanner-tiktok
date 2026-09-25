"""
Module 'Dossier Magique' (Hot Folder 100% Zéro Clic) pour Mac.
Surveille en continu un dossier local. Dès qu'une vidéo y est déposée :
1. Analyse et génère automatiquement le PACK A/B TESTING TIKTOK :
   - Variante A (14s Express - Complétion maximale + Hook 0-2s)
   - Variante B (15s Action Peak - Hook Cyber)
   - Version Complète 9:16 HD
2. Dépôt immédiat des alternatives dans le dossier Google Drive cible ('AIvidéo').
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

from converter import TikTokVideoConverter, get_short_clean_name
from analyzer import TikTokVideoAnalyzer
from gdrive_uploader import upload_video_to_gdrive, is_gdrive_configured

# Configuration par défaut du dossier
DEFAULT_WATCH_DIR = os.path.expanduser("~/Movies/A_CONVERTIR_TIKTOK")
LOCAL_WATCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "A_CONVERTIR_TIKTOK")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "magic_folder.log")

handlers = [logging.StreamHandler(sys.stdout)]
try:
    handlers.append(logging.FileHandler(LOG_FILE, encoding="utf-8"))
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=handlers,
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
    """Traite automatiquement une vidéo déposée en générant le Pack A/B Testing."""
    filename = os.path.basename(video_path)
    base_name, _ = os.path.splitext(filename)

    print("\n" + "=" * 65)
    print(f"🎬 NOUVELLE VIDÉO DÉTECTÉE : {filename}")
    print("=" * 65)
    logger.info(f"Début du traitement de : {filename}")

    # 1. Analyse préliminaire
    print("⚙️ [1/3] Analyse du format, de la durée et du son...")
    duration = 30.0
    has_silence = False
    is_9_16 = False
    try:
        analyzer = TikTokVideoAnalyzer(video_path)
        report = analyzer.analyze_all()
        has_silence = report.get("audio", {}).get("initial_silence", False)
        is_9_16 = report.get("technical", {}).get("is_9_16", False)
        duration = float(report.get("technical", {}).get("duration", 30.0))
    except Exception as e:
        logger.warning(f"Analyse préliminaire : {e}")

    mode = "blur_bg" if not is_9_16 else "crop"
    trim_start = 0.4 if has_silence else 0.0

    print(f"⏱️ Durée détectée : {duration}s | Ratio : {'9:16' if is_9_16 else 'Non-9:16 (fond flou actif)'}")
    print("\n🧪 [2/3] Génération automatique du PACK A/B TESTING TIKTOK :")

    converter = TikTokVideoConverter()
    generated_videos = []

    short_tag = get_short_clean_name(filename)

    # ----------------------------------------------------
    # A. VARIANTE A : Express 14s (Taux de complétion maximal)
    # ----------------------------------------------------
    name_a = f"{short_tag}_A_14s.mp4"
    path_a = os.path.join(output_dir, name_a)
    print(f"   🅰️ Variante A (14s Express - Hook Jaune/Noir) -> {name_a}...")
    dur_a = 14.0 if duration > 14.0 else None
    res_a = converter.convert_to_tiktok_format(
        input_path=video_path,
        output_path=path_a,
        mode=mode,
        trim_start_sec=trim_start,
        duration_sec=dur_a,
        hook_text="🚀 Regardez bien à la 4e seconde...",
        hook_style="yellow_impact",
        hook_duration=2.2,
    )
    if res_a.get("success"):
        print(f"      ✅ Variante A prête ({res_a.get('file_size_mb')} Mo)")
        generated_videos.append(("🅰️ Variante A (Express 14s)", path_a, name_a))
    else:
        print(f"      ⚠️ Variante A : {res_a.get('error')}")

    # ----------------------------------------------------
    # B. VARIANTE B : Action Peak 15s (Milieu / Moment fort)
    # ----------------------------------------------------
    name_b = f"{short_tag}_B_15s.mp4"
    path_b = os.path.join(output_dir, name_b)
    print(f"   🅱️ Variante B (15s Action Peak - Hook Cyber) -> {name_b}...")
    start_b = max(0.0, (duration / 2.0) - 7.0) if duration > 16.0 else 0.0
    dur_b = 15.0 if duration > 15.0 else None
    res_b = converter.convert_to_tiktok_format(
        input_path=video_path,
        output_path=path_b,
        mode=mode,
        trim_start_sec=start_b,
        duration_sec=dur_b,
        hook_text="😱 Ce que personne ne vous a dit :",
        hook_style="cyber_cyan",
        hook_duration=2.2,
    )
    if res_b.get("success"):
        print(f"      ✅ Variante B prête ({res_b.get('file_size_mb')} Mo)")
        generated_videos.append(("🅱️ Variante B (Action 15s)", path_b, name_b))
    else:
        print(f"      ⚠️ Variante B : {res_b.get('error')}")

    # ----------------------------------------------------
    # C. VERSION COMPLÈTE (Intégrale sans découpe)
    # ----------------------------------------------------
    name_c = f"{short_tag}_FULL.mp4"
    path_c = os.path.join(output_dir, name_c)
    print(f"   🎬 Version Complète 9:16 -> {name_c}...")
    res_c = converter.convert_to_tiktok_format(
        input_path=video_path,
        output_path=path_c,
        mode=mode,
        trim_start_sec=trim_start,
    )
    if res_c.get("success"):
        print(f"      ✅ Version Complète prête ({res_c.get('file_size_mb')} Mo)")
        generated_videos.append(("🎬 Version Complète", path_c, name_c))

    # ----------------------------------------------------
    # 3. Dépôt de toutes les variantes dans Google Drive
    # ----------------------------------------------------
    drive_ready, _ = is_gdrive_configured()
    uploaded_count = 0
    if drive_ready:
        print(f"\n☁️ [3/3] Téléversement des {len(generated_videos)} alternatives sur Google Drive (AIvidéo)...")
        for label, f_path, f_name in generated_videos:
            print(f"   🚀 Dépôt de {f_name}...")
            up_res = upload_video_to_gdrive(f_path, destination_filename=f_name)
            if up_res.get("success"):
                uploaded_count += 1
                print(f"      ✅ {label} déposée avec succès !")
            else:
                print(f"      ⚠️ Erreur {label} : {up_res.get('error')}")

        if uploaded_count > 0:
            send_macos_notification(
                "🎉 Pack A/B prêt sur iPad & Drive !",
                f"{uploaded_count} versions (Variante A et B) sont prêtes dans AIvidéo.",
                sound="Hero",
            )
            print(f"\n🎉 {uploaded_count}/{len(generated_videos)} vidéos déposées avec succès dans votre dossier Google Drive AIvidéo !")
            print("👉 Rendez-vous sur votre iPad pour publier les deux et voir laquelle décolle le plus !")
    else:
        print(f"\n📁 Fichiers enregistrés localement dans : {output_dir}")
        send_macos_notification("TikTok Studio", f"{len(generated_videos)} variantes prêtes en local.")

    print("=" * 65)
    print("👀 Retour en veille active : glissez une autre vidéo quand vous le souhaitez.\n")
    return {
        "success": True,
        "variants": generated_videos,
        "uploaded_count": uploaded_count,
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
                dest_demo = os.path.join(target_dir, f"demo_test_{int(time.time())}.mp4")
                print("\n🧪 [TEST PACK A/B DÉCLENCHÉ] Traitement de la vidéo démo...")
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

    print("=" * 65)
    print("🚀 DOSSIER MAGIQUE TIKTOK STUDIO (PACK A/B AUTOMATIQUE)")
    print(f"📂 Dossier surveillé : {target_dir}")
    print("👉 Glissez une vidéo (.mp4 ou .mov) dans ce dossier.")
    print("✨ Il génère AUTOMATIQUEMENT la Variante A (14s) ET la Variante B (15s) !")
    print("💡 Appuyez sur [ENTRÉE] dans ce terminal pour tester immédiatement !")
    print("=" * 65)

    send_macos_notification("TikTok Studio", "Dossier Magique A/B actif : déposez vos vidéos !")

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
                    print(f"[{now_str}] ⏳ En veille active : glissez une vidéo dans 'A_CONVERTIR_TIKTOK' (ou tapez Entrée)...")

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
