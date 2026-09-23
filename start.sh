#!/bin/bash
# Script de lancement rapide du TikTok Video Pre-Flight Scanner
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

echo "🚀 Lancement de l'application Streamlit..."
.venv/bin/streamlit run app.py
