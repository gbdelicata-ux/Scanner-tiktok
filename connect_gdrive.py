"""
Script d'authentification 1-Clic pour Google Drive.
Permet d'autoriser l'accès au Google Drive de Gilbert (gb.delicata@gmail.com)
et de configurer automatiquement les secrets pour le Mac et l'iPad (Streamlit Cloud).
"""

import os
import glob
import json
import shutil
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

TOKEN_FILE = ".streamlit/token.json"
SECRETS_FILE = ".streamlit/secrets.toml"


def find_credentials_file():
    """
    Recherche automatiquement le fichier credentials.json, même s'il a été
    enregistré avec des espaces ou un nom comme client_secret_*.json.
    """
    # 1. Nom exact standard
    if os.path.exists("credentials.json"):
        return "credentials.json"

    # 2. Recherche avec espaces ou préfixes
    candidates = glob.glob("*credential*.json") + glob.glob("*client_secret*.json")
    for cand in candidates:
        try:
            with open(cand, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "installed" in data or "web" in data:
                    # Normaliser le nom vers credentials.json
                    if cand != "credentials.json":
                        shutil.copy2(cand, "credentials.json")
                    return "credentials.json"
        except Exception:
            continue
    return None


def run_setup():
    print("=" * 65)
    print("🤖 CONFIGURATION DE LA CONNEXION GOOGLE DRIVE (AIvidéo)")
    print("=" * 65)

    cred_file = find_credentials_file()

    if cred_file:
        with open(cred_file, "r", encoding="utf-8") as f:
            cred_data = json.load(f)
        client_info = cred_data.get("installed") or cred_data.get("web", {})
        project_id = client_info.get("project_id", "Inconnu")
        client_id = client_info.get("client_id", "")

        print(f"✅ Fichier d'identifiants détecté : {cred_file}")
        print(f"📦 Projet Google Cloud       : {project_id}")
        print(f"🆔 Client ID                 : {client_id[:20]}...{client_id[-15:] if len(client_id) > 35 else ''}")
        
        flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
    else:
        print("\n⚠️ Aucun fichier credentials.json trouvé.")
        print("1. Rendez-vous sur https://console.cloud.google.com")
        print("2. Dans 'Identifiants', téléchargez votre ID client OAuth")
        print("3. Glissez le fichier JSON dans ce dossier sous le nom 'credentials.json'\n")

        client_id = input("Client ID (laisser vide pour annuler) : ").strip()
        if not client_id:
            print("Configuration annulée.")
            return
        client_secret = input("Client Secret : ").strip()
        if not client_secret:
            print("Configuration annulée.")
            return
        project_id = input("Project ID (ex: flowing-mantis-509116-m0) : ").strip() or "tiktok-studio"

        client_config = {
            "installed": {
                "client_id": client_id,
                "project_id": project_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8080/", "http://localhost/"],
            }
        }
        # Sauvegarde propre
        with open("credentials.json", "w", encoding="utf-8") as f:
            json.dump(client_config, f, indent=2)
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    print("\n🌐 Ouverture automatique du navigateur pour valider l'accès à Google Drive...")
    print("👉 Si le navigateur ne s'ouvre pas, un lien direct sera affiché ci-dessous.")

    try:
        creds = flow.run_local_server(
            port=8080,
            prompt="consent",
            authorization_prompt_message="Veuillez autoriser l'accès sur la page Google qui s'ouvre...",
            success_message="✅ Authentification Google réussie ! Vous pouvez revenir à cette fenêtre.",
            open_browser=True,
        )
    except Exception as e:
        print(f"\nTentative sur un port alternatif (port dynamique)...")
        creds = flow.run_local_server(
            port=0,
            prompt="consent",
            open_browser=True,
        )

    # Sauvegarder dans .streamlit/token.json
    os.makedirs(".streamlit", exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    print(f"\n✅ Jeton d'accès sauvegardé dans {TOKEN_FILE}")

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

    print("\n" + "=" * 65)
    print("🎉 SUCCÈS TOTAL ! Votre application TikTok Studio est connectée à Google Drive.")
    print("Vos vidéos seront maintenant déposées directement dans votre dossier AIvidéo.")
    print("=" * 65)
    print("\n📱 POUR VOTRE IPAD (Streamlit Cloud) :")
    print("Copiez/collez le texte ci-dessous dans les 'Secrets' de votre application Streamlit Cloud :")
    print("-" * 65)
    print(secrets_content.strip())
    print("-" * 65)


if __name__ == "__main__":
    run_setup()
