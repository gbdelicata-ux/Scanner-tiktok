#!/bin/bash
# Script de lancement rapide du Dossier Magique TikTok
cd "$(dirname "$0")"

TARGET_DIR="$(pwd)/A_CONVERTIR_TIKTOK"
mkdir -p "$TARGET_DIR"

# 1. Ouvrir immédiatement le dossier dans le Finder de macOS
open "$TARGET_DIR"

echo "======================================================"
echo "✨ DOSSIER MAGIQUE TIKTOK STUDIO (ACTIF) ✨"
echo "======================================================"
echo "📂 Le dossier Finder s'est ouvert sur votre écran !"
echo "👉 DÉPOSEZ vos vidéos (.mp4 ou .mov) dans ce dossier."
echo "------------------------------------------------------"
echo "Chaque vidéo déposée est automatiquement :"
echo "  1. Cadrée en format 9:16 Full HD (avec fond flou)"
echo "  2. Nettoyée du silence initial (0.4s)"
echo "  3. Téléversée directement dans Google Drive (AIvidéo)"
echo "  4. Une notification sonnera sur votre Mac !"
echo "------------------------------------------------------"
echo "💡 ASTUCE : Appuyez sur [ENTRÉE] pour tester maintenant"
echo "   avec une vidéo de démonstration !"
echo "Pour quitter : fermez cette fenêtre ou tapez Ctrl+C."
echo "======================================================"

.venv/bin/python3 magic_folder.py --dir "$TARGET_DIR" --interactive
