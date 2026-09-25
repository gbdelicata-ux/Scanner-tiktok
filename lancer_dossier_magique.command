#!/bin/bash
# Script de lancement rapide du Dossier Magique TikTok
cd "$(dirname "$0")"

TARGET_DIR="$(pwd)/A_CONVERTIR_TIKTOK"
mkdir -p "$TARGET_DIR"

# 1. Ouvrir et activer immédiatement la fenêtre Finder sur l'écran via AppleScript
osascript -e 'tell application "Finder" to activate' -e "tell application \"Finder\" to open POSIX file \"$TARGET_DIR\"" 2>/dev/null

echo "======================================================"
echo "✨ DOSSIER MAGIQUE TIKTOK STUDIO (ACTIF) ✨"
echo "======================================================"
echo "📂 Le dossier Finder s'est ouvert sur votre écran."
echo "📌 Vous avez aussi le raccourci sur votre BUREAU !"
echo "👉 GLISSEZ vos vidéos (.mp4 ou .mov) directement dedans."
echo "------------------------------------------------------"
echo "Chaque vidéo déposée génère AUTOMATIQUEMENT :"
echo "  🅰️ Variante A (14s Express - Maximise complétion >100%)"
echo "  🅱️ Variante B (15s Action Peak - Test d'accroche alternative)"
echo "  🎬 Version Complète 9:16 HD"
echo "  ☁️ Envoi automatique sur votre Google Drive (AIvidéo)"
echo "  📂 Enregistrement local dans le sous-dossier 'export_tiktok'"
echo "------------------------------------------------------"
echo "💡 ASTUCE : Appuyez sur [ENTRÉE] ici dans le terminal"
echo "   pour tester immédiatement avec une vidéo démo !"
echo "Pour quitter : fermez cette fenêtre ou tapez Ctrl+C."
echo "======================================================"

.venv/bin/python3 magic_folder.py --dir "$TARGET_DIR" --interactive
