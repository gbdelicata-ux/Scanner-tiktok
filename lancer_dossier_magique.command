#!/bin/bash
# Script de lancement rapide du Dossier Magique TikTok
cd "$(dirname "$0")"
echo "======================================================"
echo "✨ LANCEMENT DU DOSSIER MAGIQUE TIKTOK STUDIO ✨"
echo "======================================================"
echo "Dès que vous déposez une vidéo dans A_CONVERTIR_TIKTOK,"
echo "elle sera convertie et envoyée directement dans AIvidéo."
echo "Pour arrêter : fermez cette fenêtre ou tapez Ctrl+C."
echo "======================================================"
.venv/bin/python3 magic_folder.py
