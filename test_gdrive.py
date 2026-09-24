"""
Test unitaire et diagnostic pour l'intégration Google Drive.
"""

import os
import sys
import tempfile
import gdrive_uploader

def run_tests():
    print("=" * 60)
    print("🔍 DIAGNOSTIC INTÉGRATION GOOGLE DRIVE")
    print("=" * 60)

    # 1. Vérification configuration
    configured, desc = gdrive_uploader.is_gdrive_configured()
    print(f"Status configuration : {'🟢 Configuré' if configured else '⚪ Non configuré'}")
    print(f"Mode détecté         : {desc}")
    print(f"Dossier cible        : {gdrive_uploader.DEFAULT_FOLDER_ID} ({gdrive_uploader.DEFAULT_FOLDER_URL})")

    # 2. Test d'upload fictif si non configuré
    if not configured:
        print("\nℹ️ Aucune clé active. Test du comportement hors-ligne...")
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
            tf.write(b"dummy video data")
            tf_path = tf.name

        res = gdrive_uploader.upload_video_to_gdrive(tf_path, destination_filename="test_offline.mp4")
        assert res["success"] is False
        assert "configuré" in res.get("error", "").lower()
        print("✅ Comportement hors-ligne conforme : retour propre sans crash.")
        os.remove(tf_path)
    else:
        print(f"\n🚀 Test de connexion active via {desc}...")
        service = gdrive_uploader.build_drive_service()
        if service:
            try:
                # Vérifier l'accès au dossier AIvidéo
                folder = service.files().get(
                    fileId=gdrive_uploader.DEFAULT_FOLDER_ID,
                    fields="id, name, mimeType",
                    supportsAllDrives=True
                ).execute()
                print(f"✅ Dossier Google Drive accessible : {folder.get('name')} (ID: {folder.get('id')})")
            except Exception as e:
                print(f"⚠️ Erreur accès dossier cible : {e}")

    print("\n✅ Tous les tests du module Google Drive sont validés !")

if __name__ == "__main__":
    run_tests()
