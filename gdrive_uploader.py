"""
Module d'intégration Google Drive pour le Scanner & Studio TikTok.
Permet le téléversement direct et automatique des vidéos corrigées
dans le dossier Google Drive cible (ex: 'AIvidéo', ID: 1yO7GS0GJgDI0Waq1wdIo0tLtKFxOWjYD).

Prend en charge :
1. OAuth 2.0 (recommandé pour les comptes personnels @gmail.com)
2. Compte de service Google Cloud (Service Account)
3. Synchronisation locale Mac si disponible
"""

import os
import shutil
import logging
from typing import Optional, Dict, Any, Tuple

# Import optionnel de streamlit pour lire st.secrets sans planter si exécuté en script CLI
try:
    import streamlit as st
except ImportError:
    st = None

# Configuration par défaut
DEFAULT_FOLDER_ID = "1yO7GS0GJgDI0Waq1wdIo0tLtKFxOWjYD"
DEFAULT_FOLDER_URL = f"https://drive.google.com/drive/folders/{DEFAULT_FOLDER_ID}"
SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

logger = logging.getLogger(__name__)


def get_gdrive_config() -> Tuple[Optional[str], Optional[Any]]:
    """
    Détecte la méthode d'authentification Google Drive disponible.
    Retourne (type_methode, donnees_config).
    Types possibles :
      - 'secrets_oauth'
      - 'secrets_service_account'
      - 'file_token'
      - 'file_service_account'
      - 'local_sync'
      - None
    """
    # 1. Vérification dans Streamlit secrets
    if st is not None:
        try:
            if hasattr(st, "secrets"):
                if "gdrive_oauth" in st.secrets:
                    return "secrets_oauth", st.secrets["gdrive_oauth"]
                if "gcp_service_account" in st.secrets:
                    return "secrets_service_account", st.secrets["gcp_service_account"]
        except Exception:
            pass

    # 2. Vérification fichier local token.json (OAuth)
    for token_path in ["token.json", ".streamlit/token.json"]:
        if os.path.exists(token_path):
            return "file_token", token_path

    # 3. Vérification fichier local service_account.json
    for sa_path in [
        "service_account.json",
        ".streamlit/service_account.json",
        "credentials.json",
    ]:
        if os.path.exists(sa_path):
            # Vérifier si c'est un fichier service account ou client OAuth
            try:
                import json
                with open(sa_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("type") == "service_account":
                        return "file_service_account", sa_path
                    elif "installed" in data or "web" in data:
                        return "file_oauth_client", sa_path
            except Exception:
                pass

    # 4. Vérification d'un dossier de synchronisation locale Google Drive (Mac)
    local_drive_paths = [
        "/Users/gilbertdelicata/Library/CloudStorage/GoogleDrive-gb.delicata@gmail.com/Mon Drive/AIvidéo",
        "/Users/gilbertdelicata/Library/CloudStorage/GoogleDrive-gb.delicata@gmail.com/Mon Drive/AIvideo",
        os.path.expanduser("~/Google Drive/AIvidéo"),
        os.path.expanduser("~/Google Drive/AIvideo"),
    ]
    for p in local_drive_paths:
        if os.path.exists(p) and os.path.isdir(p) and os.access(p, os.W_OK):
            return "local_sync", p

    return None, None


def is_gdrive_configured() -> Tuple[bool, str]:
    """
    Vérifie si Google Drive est prêt pour l'envoi automatique.
    Retourne (est_configure, description_methode).
    """
    method, _ = get_gdrive_config()
    if method == "secrets_oauth":
        return True, "OAuth 2.0 (Streamlit Secrets)"
    elif method == "secrets_service_account":
        return True, "Compte de Service (Streamlit Secrets)"
    elif method == "file_token":
        return True, "OAuth 2.0 (Fichier token.json)"
    elif method == "file_service_account":
        return True, "Compte de Service (Fichier JSON)"
    elif method == "local_sync":
        return True, "Dossier Mac Synchronisé (Google Drive)"
    return False, "Non configuré"


def build_drive_service():
    """
    Construit le client d'API Google Drive v3 selon la méthode détectée.
    """
    method, config = get_gdrive_config()
    if not method or method == "local_sync":
        return None

    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        if method == "secrets_oauth":
            creds = Credentials(
                token=None,
                refresh_token=config["refresh_token"],
                token_uri=config.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                scopes=SCOPES,
            )
            creds.refresh(Request())
            return build("drive", "v3", credentials=creds, cache_discovery=False)

        elif method == "file_token":
            import json
            with open(config, "r", encoding="utf-8") as f:
                token_info = json.load(f)
            creds = Credentials.from_authorized_user_info(token_info, scopes=SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return build("drive", "v3", credentials=creds, cache_discovery=False)

        elif method == "secrets_service_account":
            # Conversion to dict si c'est un format Toml/Mapping
            info = dict(config)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            return build("drive", "v3", credentials=creds, cache_discovery=False)

        elif method == "file_service_account":
            creds = service_account.Credentials.from_service_account_file(config, scopes=SCOPES)
            return build("drive", "v3", credentials=creds, cache_discovery=False)

    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du service Drive: {e}")
        raise e

    return None


def upload_video_to_gdrive(
    local_file_path: str,
    target_folder_id: str = DEFAULT_FOLDER_ID,
    destination_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Dépose une vidéo dans le dossier Google Drive cible.
    
    Paramètres:
      - local_file_path : chemin d'accès absolu au fichier MP4/MOV local
      - target_folder_id : identifiant du dossier Google Drive (par défaut AIvidéo)
      - destination_filename : nom souhaité pour la vidéo dans Google Drive
      
    Retourne un dictionnaire avec :
      - 'success': bool
      - 'file_id': identifiant du fichier créé (si API)
      - 'web_link': lien direct pour ouvrir la vidéo dans Google Drive
      - 'filename': nom final du fichier
      - 'error': message d'erreur si échec
      - 'method': méthode utilisée ('api' ou 'local_sync')
    """
    if not os.path.exists(local_file_path):
        return {
            "success": False,
            "error": f"Fichier local introuvable: {local_file_path}",
        }

    final_name = destination_filename or os.path.basename(local_file_path)
    method, config = get_gdrive_config()

    # CAS 1 : Dossier local synchronisé (Google Drive Desktop sur Mac)
    if method == "local_sync":
        try:
            dest_dir = config
            dest_file = os.path.join(dest_dir, final_name)
            shutil.copy2(local_file_path, dest_file)
            return {
                "success": True,
                "file_id": None,
                "web_link": f"https://drive.google.com/drive/folders/{target_folder_id}",
                "filename": final_name,
                "method": "local_sync",
                "message": f"Fichier synchronisé directement via le dossier Mac : {dest_file}",
            }
        except Exception as e:
            logger.warning(f"Échec copie locale Drive: {e}, tentative via API...")

    # CAS 2 : Upload direct via Google Drive API
    try:
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError

        service = build_drive_service()
        if not service:
            return {
                "success": False,
                "error": "Google Drive n'est pas encore configuré. Ajoutez vos clés d'accès.",
                "configured": False,
            }

        file_metadata = {
            "name": final_name,
            "parents": [target_folder_id] if target_folder_id else [],
        }

        # Détection mimetype
        ext = os.path.splitext(final_name)[1].lower()
        mimetype = "video/quicktime" if ext == ".mov" else "video/mp4"

        media = MediaFileUpload(
            local_file_path,
            mimetype=mimetype,
            resumable=True,
            chunksize=1024 * 1024 * 5,  # Chunks de 5MB
        )

        drive_file = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink, webContentLink",
                supportsAllDrives=True,
            )
            .execute()
        )

        file_id = drive_file.get("id")
        web_link = drive_file.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"

        return {
            "success": True,
            "file_id": file_id,
            "web_link": web_link,
            "filename": final_name,
            "method": "api",
        }

    except HttpError as http_err:
        err_msg = str(http_err)
        if "storageQuotaExceeded" in err_msg:
            err_msg = (
                "Quota Google Drive dépassé : les comptes de service gratuits ne disposent pas d'espace personnel. "
                "Utilisez une connexion OAuth2 avec votre compte Gmail principal."
            )
        elif "notFound" in err_msg or "File not found" in err_msg:
            err_msg = (
                f"Le dossier ID '{target_folder_id}' est introuvable ou non partagé avec l'adresse du compte connecté."
            )
        logger.error(f"Erreur HTTP Google Drive: {err_msg}")
        return {"success": False, "error": err_msg}

    except Exception as e:
        logger.error(f"Erreur upload Google Drive: {e}")
        return {"success": False, "error": str(e)}
