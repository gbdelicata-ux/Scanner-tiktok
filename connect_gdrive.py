"""
Script d'authentification 1-Clic pour Google Drive.
Permet d'autoriser l'accès au Google Drive de Gilbert (gb.delicata@gmail.com)
et de configurer automatiquement les secrets pour le Mac et l'iPad (Streamlit Cloud).
"""

import os
import sys
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = ".streamlit/token.json"
SECRETS_FILE = ".streamlit/secrets.toml"


def run_setup():
    print("=" * 60)
    print("🤖 CONFIGURATION DE LA CONNEXION GOOGLE DRIVE (AIvidéo)")
    print("=" * 60)

    # Vérifier si un credentials.json existe
    client_config = None
    if os.path.exists(CREDENTIALS_FILE):
        print(f"✅ Fichier '{CREDENTIALS_FILE}' détecté.")
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    else:
        print("\nPour connecter Google Drive sans limite de stockage :")
        print("1. Rendez-vous sur https://console.cloud.google.com")
        print("2. Activez 'Google Drive API' et créez un ID client OAuth (Application de bureau)")
        print("3. Téléchargez le fichier sous le nom 'credentials.json' dans ce dossier.")
        print("\nOu saisissez directement vos identifiants ci-dessous :")
        
        client_id = input("Client ID (laisser vide pour annuler) : ").strip()
        if not client_id:
            print("Configuration annulée.")
            return
        client_secret = input("Client Secret : ").strip()
        if not client_secret:
            print("Configuration annulée.")
            return

        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8080/"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    print("\n🌐 Ouverture du navigateur pour autoriser l'accès à Google Drive...")
    creds = flow.run_local_server(port=8080)

    # Sauvegarder dans .streamlit/token.json
    os.makedirs(".streamlit", exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    print(f"✅ Jeton d'accès sauvegardé dans {TOKEN_FILE}")

    # Préparer les secrets Streamlit
    secrets_content = f"""# Configuration automatique Google Drive pour TikTok Studio
[gdrive_oauth]
client_id = "{creds.client_id}"
client_secret = "{creds.client_secret}"
refresh_token = "{creds.refresh_token}"
token_uri = "https://oauth2.googleapis.com/token"
"""
    with open(SECRETS_FILE, "w", encoding="utf-8") as f:
        f.write(secrets_content)
    print(f"✅ Secrets configurés localement dans {SECRETS_FILE}")

    print("\n" + "=" * 60)
    print("🎉 SUCCÈS ! Votre application TikTok Studio est connectée à Google Drive.")
    print("Vos vidéos seront maintenant déposées directement dans votre dossier AIvidéo.")
    print("=" * 60)
    print("\n📱 POUR VOTRE IPAD (Streamlit Cloud) :")
    print("Copiez/collez le texte ci-dessous dans les 'Secrets' de votre application Streamlit Cloud :")
    print("-" * 60)
    print(secrets_content.strip())
    print("-" * 60)


if __name__ == "__main__":
    run_setup()
