"""
Application Streamlit : Scanner, Convertisseur & Publication TikTok
Permet d'auditer vos vidéos avant publication, de convertir automatiquement
au format 9:16 optimal (1080x1920) et d'ouvrir l'application TikTok pour publier.
"""

import os
import io
import zipfile
import subprocess
import tempfile
import streamlit as st
import cv2
import numpy as np

from analyzer import TikTokVideoAnalyzer
from safe_zone import render_tiktok_overlay
from converter import TikTokVideoConverter, get_short_clean_name
from theme_detector import VideoThemeDetector
from gdrive_uploader import (
    upload_video_to_gdrive,
    is_gdrive_configured,
    DEFAULT_FOLDER_ID,
    DEFAULT_FOLDER_URL,
)
from hook_generator import (
    HOOK_STYLES,
    HOOK_PRESETS,
    create_hook_banner_image,
    preview_hook_on_frame,
)
from cover_generator import (
    extract_best_cover_frames,
    create_cover_with_sticker,
)
from caption_generator import (
    NICHE_PRESETS,
    generate_captions,
)
import magic_folder

st.set_page_config(
    page_title="TikTok Scanner, Convertisseur & Publication",
    page_icon="📱",
    layout="wide",
)

# Initialisation de l'état de session pour partager la vidéo prête
if "ready_video_path" not in st.session_state:
    st.session_state["ready_video_path"] = None
if "ready_video_name" not in st.session_state:
    st.session_state["ready_video_name"] = None

# Style CSS pour une interface soignée
st.markdown(
    """
    <style>
    .main-score {
        font-size: 3.2rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .score-green { color: #00d26a; }
    .score-orange { color: #ffab00; }
    .score-red { color: #ff385c; }
    .check-row {
        padding: 8px 12px;
        border-radius: 6px;
        margin-bottom: 6px;
        font-size: 0.95rem;
    }
    .check-ok { background-color: rgba(0, 210, 106, 0.15); border-left: 4px solid #00d26a; }
    .check-warn { background-color: rgba(255, 171, 0, 0.15); border-left: 4px solid #ffab00; }
    .check-error { background-color: rgba(255, 56, 92, 0.15); border-left: 4px solid #ff385c; }
    .check-info { background-color: rgba(0, 242, 254, 0.15); border-left: 4px solid #00f2fe; }
    .conversion-box {
        background-color: rgba(0, 242, 254, 0.08);
        border: 1px solid rgba(0, 242, 254, 0.3);
        border-radius: 12px;
        padding: 20px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .action-card {
        background-color: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Barre latérale : Paramètres & Informations
st.sidebar.title("⚙️ Paramètres & Niche")
content_style = st.sidebar.radio(
    "Type de contenu principal :",
    options=[
        ("statique", "👤 Plan statique / Humain (facecam, personnage)"),
        ("action", "🚀 Action / CGI (fusées, avions, collisions)"),
    ],
    format_func=lambda x: x[1],
    index=0,
)
selected_style = content_style[0]

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    ### 🎯 Pourquoi les vidéos bloquent à 800 vues ?
    - **Format non 9:16** : Les bandes noires détruisent l'immersion mobile.
    - **Hook trop lent** : Aucun mouvement ou cut dans les 2 premières secondes.
    - **Blanc sonore au départ** : 0.3s de silence fait swiper 40% des utilisateurs.
    - **Texte masqué** : Sous-titres situés sous les boutons TikTok (J'aime, Commentaire).
    """
)

# Détection configuration Google Drive
is_gdrive_ready, gdrive_desc = is_gdrive_configured()
GOOGLE_DRIVE_FOLDER_URL = DEFAULT_FOLDER_URL

st.sidebar.markdown("---")
st.sidebar.markdown("### ☁️ Google Drive (AIvidéo)")
if is_gdrive_ready:
    st.sidebar.success(f"🟢 **Connecté pour envoi direct**\n\n*{gdrive_desc}*")
    if st.sidebar.button("🧪 Déposer un fichier test dans Drive", key="btn_quick_test_drive", use_container_width=True):
        test_tmp = tempfile.mktemp(suffix=".mp4")
        with open(test_tmp, "w") as f:
            f.write("test_antigravity_video")
        t_res = upload_video_to_gdrive(test_tmp, destination_filename="test_connexion_drive.mp4")
        if t_res.get("success"):
            st.sidebar.success("🎉 Fichier `test_connexion_drive.mp4` déposé avec succès dans votre dossier Google Drive AIVIDEO !")
        else:
            st.sidebar.error(f"Erreur : {t_res.get('error')}")
else:
    st.sidebar.info("⚪ **Dépôt direct non configuré**\n\n(Lien manuel actif)")

st.sidebar.link_button(
    "📂 Ouvrir le dossier AIvidéo",
    GOOGLE_DRIVE_FOLDER_URL,
    use_container_width=True,
)

with st.sidebar.expander("⚙️ Configuration Dépôt Direct (Format TOML / iPad)"):
    st.markdown(
        """
        **Pour Streamlit Cloud (iPad & Web) :**
        Dans le tableau de bord Streamlit Cloud (*Settings > Secrets*), collez votre configuration au format **TOML** :
        """
    )
    # Lecture dynamique du fichier local sans exposer les clés en dur dans le code source git
    local_toml_text = ""
    for sec_file in [".streamlit/secrets.toml", "secrets.toml"]:
        if os.path.exists(sec_file):
            try:
                with open(sec_file, "r", encoding="utf-8") as f_sec:
                    local_toml_text = f_sec.read()
                break
            except Exception:
                pass

    if not local_toml_text:
        local_toml_text = """[gdrive_oauth]
client_id = "VOTRE_CLIENT_ID.apps.googleusercontent.com"
client_secret = "VOTRE_CLIENT_SECRET"
refresh_token = "VOTRE_REFRESH_TOKEN"
token_uri = "https://oauth2.googleapis.com/token"
"""
    st.code(local_toml_text, language="toml")
    st.caption("ℹ️ Ce format TOML remplace le fichier JSON et active l'envoi direct depuis n'importe quel navigateur (iPad, Chrome, Safari).")

    st.markdown("---")
    st.markdown(
        """
        **Pour votre Mac local :**
        Le fichier `.streamlit/secrets.toml` et le token sont déjà configurés ! Si besoin de renouveler :
        - Lancez dans le Terminal : `python3 connect_gdrive.py`
        """
    )
    up_cred = st.file_uploader(
        "Ou déposez un nouveau fichier JSON Google Cloud :",
        type=["json"],
        key="gdrive_json_key_uploader",
    )
    if up_cred is not None:
        try:
            import json
            cred_dict = json.load(up_cred)
            os.makedirs(".streamlit", exist_ok=True)
            if cred_dict.get("type") == "service_account":
                with open(".streamlit/service_account.json", "w", encoding="utf-8") as f:
                    json.dump(cred_dict, f, indent=2)
                st.success("✅ Compte de service activé !")
                st.rerun()
            elif "installed" in cred_dict or "web" in cred_dict:
                with open("credentials.json", "w", encoding="utf-8") as f:
                    json.dump(cred_dict, f, indent=2)
                st.success("✅ credentials.json enregistré ! Lancez `python3 connect_gdrive.py` pour valider l'accès.")
        except Exception as e:
            st.error(f"Fichier JSON invalide : {e}")

# En-tête principal avec statut Google Drive
col_head1, col_head2 = st.columns([2, 1])
with col_head1:
    st.markdown("## 📱 TikTok Video Studio & Scanner")
with col_head2:
    st.write("")
    drive_label = "🟢 AIvidéo Connecté (Drive)" if is_gdrive_ready else "☁️ Mon Dossier AIvidéo (Drive)"
    st.link_button(
        drive_label,
        GOOGLE_DRIVE_FOLDER_URL,
        use_container_width=True,
    )

# Onglets principaux
tab_scan, tab_convert, tab_batch, tab_covers, tab_captions, tab_magic, tab_publish = st.tabs([
    "📊 Scanner & Audit TikTok",
    "🎯 Studio 9:16 & Accroches",
    "⚡ Mode Rafale (Multi-Vidéos)",
    "🖼️ Vignettes & Covers HD",
    "💡 Titres & Hashtags FYP",
    "📂 Dossier Magique (Mac Auto)",
    "🚀 Envoyer & Publier",
])

# ==========================================
# ONGLET 1 : SCANNER & AUDIT ALGORITHMIQUE
# ==========================================
with tab_scan:
    st.title("📱 TikTok Pre-Flight Video Scanner")
    st.subheader("Auditez votre vidéo avant de la publier pour identifier les blocages.")

    uploaded_file = st.file_uploader(
        "Déposez votre vidéo au format MP4 ou MOV :",
        type=["mp4", "mov"],
        key="uploader_scanner",
        help="La vidéo reste analysée localement sur votre Mac.",
    )

    demo_btn = None
    demo_video_path = os.path.join(os.path.dirname(__file__), "demo_sample.mp4")
    if uploaded_file is None and os.path.exists(demo_video_path):
        st.info("💡 Vous pouvez tester immédiatement avec une vidéo de démonstration :")
        demo_btn = st.button("▶️ Charger la vidéo de test (Démo)", key="btn_demo_scanner")

    target_video_path = None
    if uploaded_file is not None:
        temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_video.write(uploaded_file.read())
        target_video_path = temp_video.name
        st.session_state["ready_video_path"] = target_video_path
        st.session_state["ready_video_name"] = uploaded_file.name
    elif demo_btn:
        target_video_path = demo_video_path
        st.session_state["ready_video_path"] = demo_video_path
        st.session_state["ready_video_name"] = "demo_sample.mp4"

    if target_video_path:
        with st.spinner("Analyse algorithmique en cours..."):
            analyzer = TikTokVideoAnalyzer(target_video_path)
            report = analyzer.analyze_all(content_style=selected_style)

        if "error" in report:
            st.error(f"Erreur d'analyse : {report['error']}")
        else:
            score = report["overall_score"]
            if score >= 85:
                score_class = "score-green"
                verdict = "🔥 EXCELLENT - Prête pour la FYP ! Tous les signaux sont au vert."
            elif score >= 65:
                score_class = "score-orange"
                verdict = "⚠️ PASSABLE - Quelques corrections recommandées pour éviter le plafond des 800 vues."
            else:
                score_class = "score-red"
                verdict = "🛑 RISQUE ÉLEVÉ DE BLOCAGE À 800 VUES - Des erreurs pénalisantes ont été détectées."

            st.markdown("---")

            # Affichage du Score
            col_score, col_verdict = st.columns([1, 2])
            with col_score:
                st.markdown(
                    f"<div class='main-score {score_class}'>{score} <span style='font-size: 1.5rem;'>/ 100</span></div>",
                    unsafe_allow_html=True,
                )
                st.caption(f"Score de Préparation TikTok ({report['technical']['duration']}s)")

            with col_verdict:
                st.markdown(f"### {verdict}")
                st.markdown(
                    f"**Résolution :** `{report['technical']['resolution_label']}` | "
                    f"**Ratio :** `{report['technical']['aspect_ratio']}` ({'9:16 vertical' if report['technical']['is_9_16'] else 'Format non optimal'}) | "
                    f"**FPS :** `{report['technical']['fps']}`"
                )

            # --- Boîte d'action rapide si format problématique ou silence ---
            needs_format_fix = not report["technical"]["is_9_16"]
            has_silence = report["audio"].get("initial_silence", False)

            if needs_format_fix or has_silence:
                st.markdown(
                    """
                    <div class='conversion-box'>
                        <h4>🪄 Correction automatique disponible</h4>
                        <p>Votre vidéo présente des points techniques pénalisants (ratio ou silence initial). Vous pouvez la corriger immédiatement au format 1080x1920 certifié TikTok !</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                col_c1, col_c2, col_c3 = st.columns([1, 1, 1])
                with col_c1:
                    fix_mode = st.selectbox(
                        "Mode de cadrage :",
                        options=[
                            ("blur_bg", "🌟 Fond flou dynamique (Recommandé)"),
                            ("crop", "✂️ Recadrage plein écran 9:16"),
                        ],
                        format_func=lambda x: x[1],
                        key="fix_mode_select",
                    )[0]
                with col_c2:
                    auto_trim = st.checkbox("✂️ Couper le silence d'introduction (0.4s)", value=has_silence)
                    auto_drive_tab1 = st.checkbox("☁️ Déposer directement dans AIvidéo (Drive)", value=is_gdrive_ready, key="chk_auto_drive_tab1")
                with col_c3:
                    st.write("")
                    convert_now_btn = st.button("🚀 Corriger la vidéo", key="btn_fix_now")

                if convert_now_btn:
                    with st.spinner("Conversion en 1080x1920 HD en cours..."):
                        converter = TikTokVideoConverter()
                        out_fixed = tempfile.mktemp(suffix="_tiktok_fixed.mp4")
                        trim_sec = 0.4 if auto_trim else 0.0
                        res = converter.convert_to_tiktok_format(
                            input_path=target_video_path,
                            output_path=out_fixed,
                            mode=fix_mode,
                            trim_start_sec=trim_sec,
                        )
                        if res["success"]:
                            raw_name = uploaded_file.name if uploaded_file else "video"
                            base_name, _ = os.path.splitext(raw_name)
                            download_filename = f"{base_name}_corrige.mp4"

                            st.session_state["ready_video_path"] = out_fixed
                            st.session_state["ready_video_name"] = download_filename
                            st.session_state["tab1_fixed_path"] = out_fixed
                            st.session_state["tab1_fixed_name"] = download_filename
                            st.session_state["tab1_fixed_res"] = res

                            # Envoi automatique vers Google Drive si coché
                            if auto_drive_tab1:
                                with st.spinner("☁️ Dépôt direct dans votre dossier Google Drive (AIvidéo)..."):
                                    up_res = upload_video_to_gdrive(out_fixed, destination_filename=download_filename)
                                    if up_res.get("success"):
                                        st.session_state["tab1_drive_url"] = up_res.get("web_link", GOOGLE_DRIVE_FOLDER_URL)
                                        st.session_state["tab1_drive_status"] = "auto_success"
                                    else:
                                        st.session_state["tab1_drive_status"] = f"warning: {up_res.get('error')}"
                        else:
                            st.error(f"Erreur lors de la conversion : {res.get('error')}")

                if st.session_state.get("tab1_fixed_path") and os.path.exists(st.session_state["tab1_fixed_path"]):
                    out_fixed = st.session_state["tab1_fixed_path"]
                    download_filename = st.session_state["tab1_fixed_name"]
                    res = st.session_state.get("tab1_fixed_res", {})
                    st.success(f"Vidéo convertie avec succès en {res.get('resolution', '1080x1920')} ({res.get('file_size_mb', '')} Mo) !")

                    if st.session_state.get("tab1_drive_status") == "auto_success":
                        st.success("🎉 **Vidéo déposée automatiquement dans votre Google Drive AIvidéo !**")
                    elif str(st.session_state.get("tab1_drive_status", "")).startswith("warning:"):
                        st.warning(f"⚠️ Info Google Drive : {st.session_state['tab1_drive_status']}")

                    col_dl_fix1, col_dl_fix2 = st.columns(2)
                    with col_dl_fix1:
                        with open(out_fixed, "rb") as f:
                            st.download_button(
                                label=f"⬇️ Enregistrer sur cet appareil",
                                data=f.read(),
                                file_name=download_filename,
                                mime="video/mp4",
                                key="dl_btn_fixed",
                                use_container_width=True,
                            )
                    with col_dl_fix2:
                        if st.button(
                            "☁️ Déposer MAINTENANT dans Google Drive",
                            key="btn_upload_drive_tab1",
                            use_container_width=True,
                        ):
                            with st.spinner("Téléversement vers Google Drive (AIvidéo)..."):
                                man_res = upload_video_to_gdrive(out_fixed, destination_filename=download_filename)
                                if man_res.get("success"):
                                    st.session_state["tab1_drive_url"] = man_res.get("web_link", GOOGLE_DRIVE_FOLDER_URL)
                                    st.session_state["tab1_drive_status"] = "auto_success"
                                    st.success(f"🎉 Vidéo « {download_filename} » déposée dans Google Drive !")
                                else:
                                    st.error(f"Erreur d'envoi : {man_res.get('error')}")

                    if st.session_state.get("tab1_drive_url"):
                        st.link_button("📂 Voir la vidéo dans mon Google Drive", st.session_state["tab1_drive_url"], use_container_width=True)
                    else:
                        st.link_button("📂 Ouvrir le dossier AIvidéo sur Google Drive", GOOGLE_DRIVE_FOLDER_URL, use_container_width=True)
            else:
                st.markdown(
                    """
                    <div style='background: rgba(37, 244, 238, 0.08); border: 1px solid #25f4ee; border-radius: 8px; padding: 12px; margin-bottom: 12px;'>
                        <h4 style='color: #25f4ee; margin: 0 0 6px 0;'>✅ Vidéo déjà au format optimal 9:16 !</h4>
                        <p style='margin: 0;'>Cette vidéo respecte les dimensions TikTok. Vous pouvez la déposer directement dans votre dossier Google Drive AIvidéo.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                col_ok_dl, col_ok_drive = st.columns(2)
                raw_name = uploaded_file.name if uploaded_file else "video.mp4"
                with col_ok_dl:
                    with open(target_video_path, "rb") as f:
                        st.download_button(
                            label=f"⬇️ Enregistrer « {raw_name} »",
                            data=f.read(),
                            file_name=raw_name,
                            mime="video/mp4",
                            key="dl_btn_ok_scan",
                            use_container_width=True,
                        )
                with col_ok_drive:
                    if st.button("☁️ Déposer MAINTENANT dans Google Drive (AIvidéo)", key="btn_upload_scan_ok", use_container_width=True):
                        with st.spinner("Téléversement vers Google Drive (AIvidéo)..."):
                            up_res = upload_video_to_gdrive(target_video_path, destination_filename=raw_name)
                            if up_res.get("success"):
                                st.session_state["tab1_drive_url"] = up_res.get("web_link", GOOGLE_DRIVE_FOLDER_URL)
                                st.success(f"🎉 Vidéo « {raw_name} » déposée avec succès dans votre dossier Google Drive AIVIDEO !")
                            else:
                                st.error(f"Erreur d'envoi : {up_res.get('error')}")

                if st.session_state.get("tab1_drive_url"):
                    st.link_button("📂 Voir la vidéo dans mon Google Drive", st.session_state["tab1_drive_url"], use_container_width=True)

            st.session_state["ready_video_path"] = target_video_path
            st.session_state["ready_video_name"] = uploaded_file.name if uploaded_file else "video.mp4"

            st.markdown("---")

            # Grille principale : Vidéo / Safe Zone & Diagnostics
            col_vid, col_diag = st.columns([1, 1])

            with col_vid:
                st.markdown("### 👁️ Inspection & Safe Zone TikTok")
                show_overlay = st.checkbox("📱 Superposer l'interface officielle TikTok (Safe Zone)", value=True, key="overlay_chk")

                # Extraction d'une frame représentative (Hook à t=0.5s)
                cap = cv2.VideoCapture(target_video_path)
                fps = report["technical"]["fps"] or 30.0
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(0.5 * fps))
                ret, frame = cap.read()
                cap.release()

                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    if show_overlay:
                        frame_with_overlay = render_tiktok_overlay(frame_rgb)
                        st.image(
                            frame_with_overlay,
                            caption="Zones rouges = boutons de l'interface / Zone verte = Safe Zone",
                            use_container_width=True,
                        )
                    else:
                        st.image(frame_rgb, caption="Frame d'accroche (t=0.5s)", use_container_width=True)

                st.video(target_video_path)

            with col_diag:
                st.markdown("### 📊 Piliers de l'Algorithme TikTok")

                sc = report["scores"]
                p1, p2 = st.columns(2)
                with p1:
                    st.metric("1. Format & Technique", f"{sc['technical']} / 25")
                    st.metric("2. Hook Dynamique (0-3s)", f"{sc['hook']} / 35")
                with p2:
                    st.metric("3. Audio & Entrée Sonore", f"{sc['audio']} / 20")
                    st.metric("4. Potentiel Rétention / Loop", f"{sc['retention']} / 20")

                st.markdown("#### 🔍 Détail des vérifications :")

                all_checks = (
                    report["checks"]["technical"]
                    + report["checks"]["hook"]
                    + report["checks"]["audio"]
                    + report["checks"]["retention"]
                )

                for chk in all_checks:
                    status = chk["status"]
                    icon = "✅" if status == "ok" else "⚠️" if status == "warn" else "❌" if status == "error" else "ℹ️"
                    css = f"check-{status}"
                    st.markdown(
                        f"<div class='check-row {css}'><strong>{icon} {chk['name']}</strong> : {chk['msg']}</div>",
                        unsafe_allow_html=True,
                    )

            st.markdown("---")

            # Section Recommandations Stratégiques
            st.markdown("### 🚀 Plan d'action pour débloquer votre vidéo")
            for rec in report["recommendations"]:
                st.markdown(rec)


# ==========================================
# ONGLET 2 : CONVERTISSEUR 9:16 DÉDIÉ
# ==========================================
with tab_convert:
    st.title("🪄 Convertisseur de Vidéos TikTok 9:16 (1080x1920)")
    col_cv_t1, col_cv_t2 = st.columns([3, 2])
    with col_cv_t1:
        st.write(
            "Transformez n'importe quelle vidéo (horizontale 16:9, carrée ou basse résolution) "
            "en format vertical immersif optimisé pour l'algorithme TikTok."
        )
    with col_cv_t2:
        st.link_button(
            "☁️ Ouvrir mon dossier AIvidéo (Drive)",
            GOOGLE_DRIVE_FOLDER_URL,
            use_container_width=True,
        )

    conv_upload = st.file_uploader(
        "Sélectionnez une vidéo à convertir :",
        type=["mp4", "mov"],
        key="uploader_converter",
    )

    if conv_upload:
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_input.write(conv_upload.read())
        conv_input_path = temp_input.name

        cap = cv2.VideoCapture(conv_input_path)
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        orig_fps = round(cap.get(cv2.CAP_PROP_FPS) or 30.0, 1)
        cap.release()

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_duration = round(total_frames / orig_fps, 1) if orig_fps > 0 else 30.0
        st.info(f"📁 Fichier d'origine détecté : **{orig_w}x{orig_h}** ({orig_fps} FPS - {orig_duration}s)")

        st.markdown("### 🎛️ 1. Cadrage vertical & Audio")
        col_opt1, col_opt2 = st.columns(2)

        with col_opt1:
            selected_mode = st.radio(
                "Style de cadrage vertical :",
                options=[
                    ("blur_bg", "🌟 Fond flou dynamique (Idéal pour les vidéos horizontales d'avions/fusées)"),
                    ("crop", "✂️ Recadrage centré plein écran 9:16 (Zoom sans bande)"),
                    ("fit", "⬛ Ajustement avec bandes noires classiques"),
                ],
                format_func=lambda x: x[1],
                index=0,
            )[0]

        with col_opt2:
            trim_seconds = st.slider(
                "Couper le début de la vidéo (suppression du silence d'intro) :",
                min_value=0.0,
                max_value=3.0,
                value=0.0,
                step=0.1,
                format="%.1f secondes",
            )
            auto_drive_tab2 = st.checkbox(
                "☁️ Déposer directement dans AIvidéo (Google Drive)",
                value=is_gdrive_ready,
                key="chk_auto_drive_tab2",
            )

        # ----------------------------------------------------
        # 2. Accroche Visuelle ("Hook 0-2s")
        # ----------------------------------------------------
        st.markdown("---")
        st.markdown("### 🎯 2. Accroche Visuelle (« Hook 0-2s » - Anti-Zap)")
        enable_hook = st.checkbox(
            "⚡ Incruster une accroche visuelle dans les premières secondes (Recommandé pour percer le plafond des 800 vues)",
            value=True,
            key="chk_enable_hook",
        )
        hook_text = ""
        hook_style = "yellow_impact"
        hook_duration = 2.0
        if enable_hook:
            col_hk1, col_hk2 = st.columns([2, 1])
            with col_hk1:
                hook_preset_cat = st.selectbox(
                    "Thématique de l'accroche :",
                    options=[
                        ("espace_cgi", "🪐 Espace, Fusées & Simulations CGI"),
                        ("facecam_conseil", "🎙️ Facecam, Secrets & Conseils"),
                        ("curiosite_generale", "😱 Choc & Grande Curiosité"),
                        ("custom", "✍️ Rédiger mon propre texte personnalisé"),
                    ],
                    format_func=lambda x: x[1],
                    key="sel_hook_cat",
                )[0]
                if hook_preset_cat == "custom":
                    hook_text = st.text_input("Votre texte d'accroche (max 60 caractères) :", value="Que se passe-t-il si vous ratez ce détail ?", key="txt_hook_custom")
                else:
                    hook_text = st.selectbox("Sélectionnez l'accroche prête à l'emploi :", options=HOOK_PRESETS[hook_preset_cat], key="sel_hook_preset")
            with col_hk2:
                hook_style = st.selectbox(
                    "Style graphique :",
                    options=list(HOOK_STYLES.keys()),
                    format_func=lambda k: HOOK_STYLES[k]["name"],
                    key="sel_hook_style",
                )
                hook_duration = st.slider("Durée d'affichage :", min_value=1.5, max_value=4.0, value=2.0, step=0.5, format="%.1f s", key="slider_hook_dur")

        # ----------------------------------------------------
        # 3. Découpeur de Rétention (12-18s)
        # ----------------------------------------------------
        st.markdown("---")
        st.markdown("### ✂️ 3. Découpeur de Rétention (Format Optimal 12-18s TikTok)")
        enable_retention = st.checkbox("✂️ Activer le découpage court (Maximise le taux de complétion pour la FYP)", value=False, key="chk_retention")
        cut_duration = None
        cut_start = trim_seconds
        if enable_retention:
            col_ret1, col_ret2 = st.columns(2)
            with col_ret1:
                retention_preset = st.radio(
                    "Format de rétention :",
                    options=[
                        (14.0, "⚡ Format Express (14s) - Taux de complétion maximal"),
                        (18.0, "🔥 Format Standard (18s) - Bon équilibre action/contexte"),
                        ("custom", "✂️ Durée personnalisée"),
                    ],
                    format_func=lambda x: x[1],
                    key="radio_retention",
                )[0]
                if retention_preset == "custom":
                    cut_duration = st.slider("Durée de l'extrait :", min_value=5.0, max_value=30.0, value=15.0, step=1.0, format="%.0f s", key="slider_custom_cut")
                else:
                    cut_duration = float(retention_preset)
            with col_ret2:
                max_s = max(1.0, orig_duration - 5.0)
                cut_start = st.slider("Commencer l'extrait à :", min_value=0.0, max_value=float(max_s), value=float(trim_seconds), step=0.5, format="%.1f s", key="slider_cut_start")

        # Identifiant court et lisible pour l'export (compatible mobile / iPad / TikTok)
        raw_input_name = conv_upload.name if conv_upload else "video"
        default_tag = get_short_clean_name(raw_input_name)
        col_tag1, col_tag2 = st.columns([1, 1])
        with col_tag1:
            short_tag = st.text_input(
                "🏷️ Nom court de la vidéo :",
                value=default_tag,
                help="Nom concis (ex: 76662, mars) pour que vos variantes restent courtes et faciles à lire sur iPad sans être tronquées.",
                key="input_short_tag",
            ).strip() or default_tag
        with col_tag2:
            st.caption("📱 Aperçu des noms générés (ultra-lisibles sur iPad & TikTok) :")
            st.code(f"🅰️ {short_tag}_A_14s.mp4\n🅱️ {short_tag}_B_15s.mp4\n🎬 {short_tag}_FULL.mp4", language="text")

        st.markdown("---")
        run_full_pack = st.button("⚡ Tout Générer en 1 clic : Vidéo Complète 9:16 + Pack A/B Testing (Recommandé)", key="btn_full_pack", type="primary", use_container_width=True)
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            run_conv_btn = st.button("🎬 Convertir uniquement la vidéo intégrale (9:16)", key="btn_run_conversion", use_container_width=True)
        with col_act2:
            run_ab_btn = st.button("🧪 Générer uniquement le Pack A/B Testing (Variante A & B)", key="btn_ab_testing", use_container_width=True)

        if run_full_pack or run_conv_btn:
            with st.spinner("Conversion en cours avec encodage H.264 certifié TikTok..."):
                converter = TikTokVideoConverter()
                output_converted = tempfile.mktemp(suffix="_tiktok_converted.mp4")
                res = converter.convert_to_tiktok_format(
                    input_path=conv_input_path,
                    output_path=output_converted,
                    mode=selected_mode,
                    trim_start_sec=cut_start,
                    duration_sec=cut_duration,
                    hook_text=hook_text if enable_hook else None,
                    hook_style=hook_style,
                    hook_duration=hook_duration,
                )

            if res["success"]:
                download_filename = f"{short_tag}_FULL.mp4"

                st.session_state["ready_video_path"] = output_converted
                st.session_state["ready_video_name"] = download_filename
                st.session_state["tab2_output_path"] = output_converted
                st.session_state["tab2_download_filename"] = download_filename
                st.session_state["tab2_res"] = res

                # Téléversement direct dans Google Drive si activé
                if auto_drive_tab2:
                    with st.spinner("☁️ Dépôt direct dans votre dossier Google Drive (AIvidéo)..."):
                        up_res = upload_video_to_gdrive(output_converted, destination_filename=download_filename)
                        if up_res.get("success"):
                            st.session_state["tab2_drive_url"] = up_res.get("web_link", GOOGLE_DRIVE_FOLDER_URL)
                            st.session_state["tab2_drive_status"] = "auto_success"
                        else:
                            st.session_state["tab2_drive_status"] = f"warning: {up_res.get('error')}"
            else:
                st.error(f"Erreur de conversion : {res.get('error')}")

        if run_full_pack or run_ab_btn:
            with st.spinner("Génération des 2 variantes A/B Testing en cours..."):
                converter = TikTokVideoConverter()
                ab_dir = tempfile.mkdtemp()
                ab_res = converter.generate_ab_variants(
                    input_path=conv_input_path,
                    output_dir=ab_dir,
                    mode=selected_mode,
                    total_duration=orig_duration,
                    hook_a=hook_text or "🚀 Regardez bien jusqu'à la fin...",
                    hook_b="😱 Ce que personne ne vous a dit :",
                    short_name=short_tag,
                )
                st.session_state["tab2_ab_res"] = ab_res
                st.session_state["tab2_ab_dir"] = ab_dir

                # Téléversement automatique des 2 variantes dans Google Drive si activé
                if auto_drive_tab2:
                    with st.spinner("☁️ Dépôt des variantes A et B dans votre dossier Google Drive (AIvidéo)..."):
                        va_path = ab_res.get("variant_a", {}).get("output_path")
                        vb_path = ab_res.get("variant_b", {}).get("output_path")
                        if va_path and os.path.exists(va_path):
                            up_a = upload_video_to_gdrive(va_path, destination_filename=os.path.basename(va_path))
                            if up_a.get("success"):
                                st.session_state["tab2_ab_va_drive"] = up_a.get("web_link", GOOGLE_DRIVE_FOLDER_URL)
                        if vb_path and os.path.exists(vb_path):
                            up_b = upload_video_to_gdrive(vb_path, destination_filename=os.path.basename(vb_path))
                            if up_b.get("success"):
                                st.session_state["tab2_ab_vb_drive"] = up_b.get("web_link", GOOGLE_DRIVE_FOLDER_URL)
                        st.session_state["tab2_ab_drive_success"] = True

        if st.session_state.get("tab2_ab_res"):
            ab_dict = st.session_state["tab2_ab_res"]
            st.success("🎉 **Pack A/B Testing généré avec succès !**")
            if st.session_state.get("tab2_ab_drive_success"):
                st.success("☁️ **Les 2 variantes A et B ont été déposées directement dans votre dossier Google Drive AIvidéo !**")

            col_ab1, col_ab2 = st.columns(2)
            with col_ab1:
                st.markdown("#### 🅰️ Variante A (Express 14s)")
                st.caption("Coupe courte pour un taux de complétion maximal (100% de rétention TikTok).")
                va = ab_dict.get("variant_a", {})
                if va.get("success"):
                    st.video(va["output_path"])
                    with open(va["output_path"], "rb") as f_a:
                        st.download_button("⬇️ Télécharger Variante A", f_a.read(), file_name=os.path.basename(va["output_path"]), mime="video/mp4", key="dl_va", use_container_width=True)
                    if st.session_state.get("tab2_ab_va_drive"):
                        st.link_button("📂 Voir Variante A sur Drive", st.session_state["tab2_ab_va_drive"], use_container_width=True)
                    else:
                        if st.button("☁️ Déposer Variante A sur Drive", key="btn_drv_va", use_container_width=True):
                            up_m_a = upload_video_to_gdrive(va["output_path"], destination_filename=os.path.basename(va["output_path"]))
                            if up_m_a.get("success"):
                                st.session_state["tab2_ab_va_drive"] = up_m_a.get("web_link")
                                st.success("Variante A envoyée sur Drive !")
                                st.rerun()
            with col_ab2:
                st.markdown("#### 🅱️ Variante B (Action 15s)")
                st.caption("Extrait centré sur le pic d'action visuelle avec accroche alternative.")
                vb = ab_dict.get("variant_b", {})
                if vb.get("success"):
                    st.video(vb["output_path"])
                    with open(vb["output_path"], "rb") as f_b:
                        st.download_button("⬇️ Télécharger Variante B", f_b.read(), file_name=os.path.basename(vb["output_path"]), mime="video/mp4", key="dl_vb", use_container_width=True)
                    if st.session_state.get("tab2_ab_vb_drive"):
                        st.link_button("📂 Voir Variante B sur Drive", st.session_state["tab2_ab_vb_drive"], use_container_width=True)
                    else:
                        if st.button("☁️ Déposer Variante B sur Drive", key="btn_drv_vb", use_container_width=True):
                            up_m_b = upload_video_to_gdrive(vb["output_path"], destination_filename=os.path.basename(vb["output_path"]))
                            if up_m_b.get("success"):
                                st.session_state["tab2_ab_vb_drive"] = up_m_b.get("web_link")
                                st.success("Variante B envoyée sur Drive !")
                                st.rerun()

        if st.session_state.get("tab2_output_path") and os.path.exists(st.session_state["tab2_output_path"]):
            output_converted = st.session_state["tab2_output_path"]
            download_filename = st.session_state["tab2_download_filename"]
            res = st.session_state.get("tab2_res", {})
            st.success(f"🎉 Vidéo convertie en {res.get('resolution', '1080x1920')} ! Taille : {res.get('file_size_mb', '')} Mo")

            if st.session_state.get("tab2_drive_status") == "auto_success":
                st.success("🎉 **Vidéo déposée automatiquement dans votre dossier Google Drive AIvidéo !**")
            elif str(st.session_state.get("tab2_drive_status", "")).startswith("warning:"):
                st.warning(f"⚠️ Info Google Drive : {st.session_state['tab2_drive_status']}")

            col_res_v, col_res_d = st.columns([1, 1])
            with col_res_v:
                st.video(output_converted)
            with col_res_d:
                st.markdown("#### 📱 Prête à publier")
                st.write("La vidéo est désormais parfaitement calibrée pour les smartphones et l'algorithme.")
                with open(output_converted, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Télécharger « {download_filename} »",
                        data=f.read(),
                        file_name=download_filename,
                        mime="video/mp4",
                        key="btn_download_final",
                        use_container_width=True,
                    )
                if st.button(
                    "☁️ Déposer MAINTENANT dans Google Drive (AIvidéo)",
                    key="btn_upload_drive_tab2",
                    use_container_width=True,
                ):
                    with st.spinner("Téléversement direct vers Google Drive (AIvidéo)..."):
                        man_res = upload_video_to_gdrive(output_converted, destination_filename=download_filename)
                        if man_res.get("success"):
                            st.session_state["tab2_drive_url"] = man_res.get("web_link", GOOGLE_DRIVE_FOLDER_URL)
                            st.session_state["tab2_drive_status"] = "auto_success"
                            st.success(f"🎉 Vidéo « {download_filename} » déposée dans Google Drive !")
                        else:
                            st.error(f"Erreur d'envoi : {man_res.get('error')}")

                if st.session_state.get("tab2_drive_url"):
                    st.link_button("📂 Voir la vidéo dans mon Google Drive", st.session_state["tab2_drive_url"], use_container_width=True)
                else:
                    st.link_button(
                        "📂 Ouvrir le dossier AIvidéo sur Google Drive",
                        GOOGLE_DRIVE_FOLDER_URL,
                        use_container_width=True,
                    )
                st.info("👉 Rendez-vous dans l'onglet **'🚀 Envoyer & Publier'** pour lancer TikTok !")


# ==========================================
# ONGLET 3 : MODE RAFALE (TRAITEMENT PAR LOT)
# ==========================================
with tab_batch:
    st.title("⚡ Mode Rafale : Traitez jusqu'à 10+ vidéos à la fois")
    col_bt_t1, col_bt_t2 = st.columns([3, 2])
    with col_bt_t1:
        st.write(
            "Déposez plusieurs vidéos en même temps (par exemple vos clips d'avions, fusées, collisions ou facecam). "
            "Vous pouvez toutes les convertir en 9:16 ou les auditer d'un coup, puis **télécharger le pack complet dans un fichier ZIP** !"
        )
    with col_bt_t2:
        st.link_button(
            "☁️ Ouvrir mon dossier AIvidéo (Drive)",
            GOOGLE_DRIVE_FOLDER_URL,
            use_container_width=True,
        )

    batch_action = st.radio(
        "Action à exécuter sur le lot de vidéos :",
        options=[
            ("convert", "🪄 Conversion 9:16 en Rafale (+ Téléchargement du pack ZIP)"),
            ("audit", "📊 Audit & Scan de Rétention en Rafale (Tableau comparatif)"),
        ],
        format_func=lambda x: x[1],
        index=0,
        horizontal=True,
    )[0]

    uploaded_batch = st.file_uploader(
        "Sélectionnez vos vidéos (vous pouvez en choisir jusqu'à 10 ou plus) :",
        type=["mp4", "mov"],
        accept_multiple_files=True,
        key="uploader_batch",
        help="Sur Mac ou iPad, sélectionnez plusieurs fichiers en même temps.",
    )

    if uploaded_batch:
        st.info(f"📂 **{len(uploaded_batch)} vidéo(s) chargée(s)** pour le traitement en rafale.")

        if batch_action == "convert":
            # --- Pré-scan instantané pour détecter la conformité TikTok & les Thèmes ---
            theme_det = VideoThemeDetector()
            inspected_files = []
            for file in uploaded_batch:
                file.seek(0)
                _, f_ext = os.path.splitext(file.name)
                f_ext = f_ext.lower() if f_ext in [".mp4", ".mov", ".m4v"] else ".mp4"
                temp_probe = tempfile.NamedTemporaryFile(delete=False, suffix=f_ext)
                temp_probe.write(file.read())
                temp_probe.close()
                file.seek(0)

                cap = cv2.VideoCapture(temp_probe.name)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = round(cap.get(cv2.CAP_PROP_FPS) or 30.0, 1)
                tot = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                dur = round(tot / fps, 1) if fps > 0 else 0
                cap.release()

                # Détection du thème (Fusée, Collision, Avion, Facecam, etc.)
                theme_info = theme_det.detect_theme(temp_probe.name)

                try:
                    os.remove(temp_probe.name)
                except Exception:
                    pass

                ratio = round(w / h, 3) if h > 0 else 0
                is_compliant_9_16 = (0.54 <= ratio <= 0.58) and (h >= 1080) and (w >= 720)

                if not (0.54 <= ratio <= 0.58):
                    issue_label = f"Format {w}x{h} (Ratio {ratio} non 9:16)"
                    needs_fix = True
                elif h < 1080:
                    issue_label = f"Basse résolution ({w}x{h} < 1080p)"
                    needs_fix = True
                else:
                    issue_label = f"Conforme 9:16 HD ({w}x{h})"
                    needs_fix = False

                inspected_files.append({
                    "file": file,
                    "name": file.name,
                    "w": w,
                    "h": h,
                    "ratio": ratio,
                    "duration": dur,
                    "needs_fix": needs_fix,
                    "issue_label": issue_label,
                    "theme_id": theme_info["theme_id"],
                    "theme_label": theme_info["theme_label"],
                    "slug": theme_info["slug"],
                    "hashtags": theme_info["hashtags"],
                })

            nb_compliant = sum(1 for it in inspected_files if not it["needs_fix"])
            nb_problematic = sum(1 for it in inspected_files if it["needs_fix"])

            # Tableau de bord du tri automatique
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total Vidéos", len(inspected_files))
            col_m2.metric("✅ Déjà Conformes TikTok", nb_compliant)
            col_m3.metric("⚠️ À Corriger", nb_problematic)

            st.markdown("### 🎯 Choix du mode de sélection")
            filter_mode = st.radio(
                "Quelles vidéos souhaitez-vous modifier ?",
                options=[
                    ("auto_problematic", f"🪄 Modifier UNIQUEMENT les vidéos non conformes ({nb_problematic} vidéo(s) ciblée(s))"),
                    ("custom", "✍️ Sélection personnalisée (cocher manuellement)"),
                    ("all", f"🔄 Tout modifier (forcer la conversion des {len(inspected_files)} vidéos)"),
                ],
                format_func=lambda x: x[1],
                index=0,
                key="filter_mode_radio",
            )[0]

            st.markdown("#### 📋 Diagnostic & Thèmes détectés pour chaque vidéo :")
            selected_indices = []
            for i, it in enumerate(inspected_files):
                if filter_mode == "auto_problematic":
                    default_checked = it["needs_fix"]
                    is_disabled = True
                elif filter_mode == "all":
                    default_checked = True
                    is_disabled = True
                else:  # custom
                    default_checked = it["needs_fix"]
                    is_disabled = False

                col_c1, col_c2 = st.columns([1, 14])
                with col_c1:
                    checked = st.checkbox(
                        "",
                        value=default_checked,
                        key=f"chk_vid_{i}_{it['name']}",
                        disabled=is_disabled,
                    )
                with col_c2:
                    theme_badge = f"🏷️ **{it['theme_label']}**"
                    if it["needs_fix"]:
                        st.markdown(
                            f"🛑 **{it['name']}** ➔ {theme_badge} | `{it['issue_label']}` ({it['duration']}s) "
                            f"{'➔ **Sélectionnée pour correction**' if checked else '*(Non cochée)*'}"
                        )
                    else:
                        st.markdown(
                            f"✅ **{it['name']}** ➔ {theme_badge} | `{it['issue_label']}` ({it['duration']}s) "
                            f"{'➔ *Préservée sans modification*' if not checked else '➔ **Forcée pour ré-encodage**'}"
                        )

                if checked:
                    selected_indices.append(i)

            st.markdown("---")
            st.markdown("### 🎛️ Paramètres & Nommage thématique")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                batch_style = st.selectbox(
                    "Style de cadrage 9:16 appliqué :",
                    options=[
                        ("blur_bg", "🌟 Fond flou dynamique (Idéal pour vidéos d'avions/fusées/espace 16:9)"),
                        ("crop", "✂️ Recadrage centré plein écran 9:16 (Zoom sans bande)"),
                        ("fit", "⬛ Ajustement avec bandes noires classiques"),
                    ],
                    format_func=lambda x: x[1],
                    key="batch_style_select",
                )[0]
                batch_naming = st.selectbox(
                    "🏷️ Comment nommer les fichiers corrigés (lisibles iPad) ?",
                    options=[
                        ("original", "📱 Identifiant court (ex: 76662_FULL.mp4 - Recommandé)"),
                        ("thematic", "🏷️ Nom thématique court (ex: Espace_01_FULL.mp4)"),
                        ("prefixed", "🔀 Thème + Identifiant (ex: Espace_76662_FULL.mp4)"),
                    ],
                    format_func=lambda x: x[1],
                    index=0,
                    key="batch_naming_select",
                )[0]

            with col_b2:
                batch_trim = st.slider(
                    "Couper les premières secondes de chaque vidéo :",
                    min_value=0.0,
                    max_value=3.0,
                    value=0.0,
                    step=0.1,
                    format="%.1f secondes",
                    key="batch_trim_slider",
                )
                auto_drive_batch = st.checkbox(
                    "☁️ Déposer automatiquement chaque vidéo corrigée dans Google Drive (AIvidéo)",
                    value=is_gdrive_ready,
                    key="chk_auto_drive_batch",
                    help="Dès qu'une vidéo est convertie, elle est envoyée directement dans votre dossier Google Drive sans aucune action manuelle.",
                )

            if len(selected_indices) == 0:
                st.warning("ℹ️ Aucune vidéo n'est sélectionnée pour la conversion (toutes vos vidéos sont déjà conformes ou décochées).")
            else:
                btn_convert_label = f"⚡ Lancer la correction des {len(selected_indices)} vidéo(s) sélectionnée(s)"
                if st.button(btn_convert_label, key="btn_start_batch_convert"):
                    progress_bar = st.progress(0, text="Démarrage du traitement par lot...")
                    converter = TikTokVideoConverter()
                    converted_files = []
                    theme_counters = {}

                    total_to_process = len(selected_indices)
                    for step_idx, orig_idx in enumerate(selected_indices):
                        item = inspected_files[orig_idx]
                        file = item["file"]
                        pct = int((step_idx / total_to_process) * 100)
                        progress_bar.progress(pct, text=f"Correction de la vidéo {step_idx + 1}/{total_to_process} : {file.name} [{item['theme_label']}]...")

                        file.seek(0)
                        _, f_ext = os.path.splitext(file.name)
                        f_ext = f_ext.lower() if f_ext in [".mp4", ".mov", ".m4v"] else ".mp4"
                        temp_in = tempfile.NamedTemporaryFile(delete=False, suffix=f_ext)
                        temp_in.write(file.read())
                        temp_in.close()

                        temp_out = tempfile.mktemp(suffix="_batch_fixed.mp4")

                        res = converter.convert_to_tiktok_format(
                            input_path=temp_in.name,
                            output_path=temp_out,
                            mode=batch_style,
                            trim_start_sec=batch_trim,
                        )

                        base_name, _ = os.path.splitext(file.name)
                        tag = get_short_clean_name(base_name)
                        slug = item["slug"]
                        theme_counters[slug] = theme_counters.get(slug, 0) + 1
                        num = theme_counters[slug]

                        if batch_naming == "thematic":
                            fixed_name = f"{slug}_{num:02d}_FULL.mp4"
                        elif batch_naming == "prefixed":
                            fixed_name = f"{slug}_{tag}_FULL.mp4"
                        else:
                            fixed_name = f"{tag}_FULL.mp4"

                        if res["success"] and os.path.exists(temp_out):
                            with open(temp_out, "rb") as f_out:
                                data = f_out.read()

                            # Téléversement direct Google Drive si activé
                            drive_info = None
                            if auto_drive_batch:
                                progress_bar.progress(pct, text=f"☁️ Dépôt dans Google Drive (AIvidéo) : {fixed_name}...")
                                drive_res = upload_video_to_gdrive(
                                    local_file_path=temp_out,
                                    destination_filename=fixed_name,
                                )
                                drive_info = drive_res

                            converted_files.append((fixed_name, data, res["file_size_mb"], item["theme_label"], drive_info))
                            try:
                                os.remove(temp_out)
                            except Exception:
                                pass
                        else:
                            st.error(f"❌ Échec pour {file.name} : {res.get('error', 'Erreur inconnue')}")

                        try:
                            os.remove(temp_in.name)
                        except Exception:
                            pass

                    progress_bar.progress(100, text="Traitement terminé !")

                    if converted_files:
                        # Archive 1 : Uniquement les vidéos corrigées
                        zip_corrige = io.BytesIO()
                        with zipfile.ZipFile(zip_corrige, "w", zipfile.ZIP_DEFLATED) as zf:
                            for item_f in converted_files:
                                zf.writestr(item_f[0], item_f[1])
                        zip_corrige.seek(0)

                        # Archive 2 : Pack complet (vidéos corrigées + vidéos déjà conformes d'origine)
                        zip_complet = io.BytesIO()
                        with zipfile.ZipFile(zip_complet, "w", zipfile.ZIP_DEFLATED) as zf_all:
                            # 1. Ajouter les corrigées
                            for item_f in converted_files:
                                zf_all.writestr(item_f[0], item_f[1])
                            # 2. Ajouter les intactes non modifiées
                            for i, it in enumerate(inspected_files):
                                if i not in selected_indices:
                                    it["file"].seek(0)
                                    zf_all.writestr(it["name"], it["file"].read())
                        zip_complet.seek(0)

                        st.session_state["tab3_converted_files"] = converted_files
                        st.session_state["tab3_zip_corrige"] = zip_corrige.getvalue()
                        st.session_state["tab3_zip_complet"] = zip_complet.getvalue()
                        st.session_state["tab3_total_inspected"] = len(inspected_files)

                # Affichage persistant des résultats de conversion
                if st.session_state.get("tab3_converted_files"):
                    converted_files = st.session_state["tab3_converted_files"]
                    st.success(f"🎉 **{len(converted_files)} vidéo(s) corrigée(s) avec succès en format 1080x1920 HD !**")

                    st.markdown("### 📦 Téléchargements groupés")
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        if st.session_state.get("tab3_zip_corrige"):
                            st.download_button(
                                label=f"📦 Télécharger uniquement les {len(converted_files)} vidéos corrigées (.ZIP)",
                                data=st.session_state["tab3_zip_corrige"],
                                file_name="videos_corrigees_tiktok.zip",
                                mime="application/zip",
                                key="btn_download_batch_zip_fixed",
                            )
                    with col_dl2:
                        if st.session_state.get("tab3_zip_complet"):
                            total_c = st.session_state.get("tab3_total_inspected", len(converted_files))
                            st.download_button(
                                label=f"🎁 Télécharger la collection complète de {total_c} vidéos (.ZIP)",
                                data=st.session_state["tab3_zip_complet"],
                                file_name="collection_complete_tiktok.zip",
                                mime="application/zip",
                                key="btn_download_batch_zip_all",
                            )

                    successful_uploads = [f for f in converted_files if len(f) > 4 and f[4] and f[4].get("success")]
                    if successful_uploads:
                        st.success(f"🎉 **{len(successful_uploads)}/{len(converted_files)} vidéo(s) déposée(s) automatiquement dans votre dossier Google Drive AIvidéo !**")
                    elif any(len(f) > 4 and f[4] and not f[4].get("success") for f in converted_files):
                        err = next(f[4]["error"] for f in converted_files if len(f) > 4 and f[4] and not f[4].get("success"))
                        st.warning(f"⚠️ Note Google Drive : {err}")
                    else:
                        if st.button("☁️ Déposer TOUTES ces vidéos dans mon Google Drive (AIvidéo)", key="btn_batch_upload_all_drive", use_container_width=True):
                            with st.spinner("Téléversement groupé dans votre Google Drive..."):
                                c_ok = 0
                                for item_entry in converted_files:
                                    fn = item_entry[0]
                                    d = item_entry[1]
                                    tmp_batch_f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                                    tmp_batch_f.write(d)
                                    tmp_batch_f.close()
                                    res_u = upload_video_to_gdrive(tmp_batch_f.name, destination_filename=fn)
                                    if res_u.get("success"):
                                        c_ok += 1
                                    try:
                                        os.remove(tmp_batch_f.name)
                                    except Exception:
                                        pass
                                st.success(f"🎉 **{c_ok}/{len(converted_files)} vidéo(s) déposée(s) avec succès dans votre dossier Google Drive AIvidéo !**")

                    st.link_button(
                        "📂 Ouvrir mon dossier AIvidéo sur Google Drive",
                        GOOGLE_DRIVE_FOLDER_URL,
                        use_container_width=True,
                    )

                    st.markdown("---")
                    st.markdown("#### 👁️ Téléchargement ou accès direct aux vidéos corrigées :")
                    for item_entry in converted_files:
                        filename = item_entry[0]
                        data = item_entry[1]
                        size_mb = item_entry[2]
                        theme_label = item_entry[3]
                        drive_info = item_entry[4] if len(item_entry) > 4 else None

                        col_f1, col_f2 = st.columns([3, 1])
                        with col_f1:
                            drive_badge = " | 🟢 **Déposé sur Google Drive**" if (drive_info and drive_info.get("success")) else ""
                            st.write(f"🎬 **{filename}** ➔ {theme_label} ({size_mb} Mo - 1080x1920){drive_badge}")
                        with col_f2:
                            if drive_info and drive_info.get("web_link"):
                                st.link_button(
                                    "📂 Voir sur Drive",
                                    drive_info["web_link"],
                                    use_container_width=True,
                                    key=f"drive_btn_{filename}",
                                )
                            else:
                                st.download_button(
                                    label="⬇️ Télécharger",
                                    data=data,
                                    file_name=filename,
                                    mime="video/mp4",
                                    key=f"dl_indiv_{filename}",
                                    use_container_width=True,
                                )

        elif batch_action == "audit":
            if st.button(f"🔍 Lancer l'audit de {len(uploaded_batch)} vidéo(s)", key="btn_start_batch_audit"):
                progress_bar = st.progress(0, text="Analyse du lot en cours...")
                results = []

                total = len(uploaded_batch)
                for idx, file in enumerate(uploaded_batch):
                    pct = int(((idx) / total) * 100)
                    progress_bar.progress(pct, text=f"Scan de la vidéo {idx + 1}/{total} : {file.name}...")

                    file.seek(0)
                    _, f_ext = os.path.splitext(file.name)
                    f_ext = f_ext.lower() if f_ext in [".mp4", ".mov", ".m4v"] else ".mp4"
                    temp_in = tempfile.NamedTemporaryFile(delete=False, suffix=f_ext)
                    temp_in.write(file.read())
                    temp_in.close()

                    analyzer = TikTokVideoAnalyzer(temp_in.name)
                    report = analyzer.analyze_all(content_style=selected_style)

                    try:
                        os.remove(temp_in.name)
                    except Exception:
                        pass

                    if "error" not in report:
                        score = report["overall_score"]
                        status = "🔥 Prête" if score >= 85 else "⚠️ À corriger" if score >= 65 else "🛑 Risque 800 vues"
                        format_str = "✅ 9:16 HD" if report["technical"]["is_9_16"] else f"❌ {report['technical']['resolution_label']}"
                        silence_str = "⚠️ Blanc au début" if report["audio"].get("initial_silence") else "✅ Son immédiat"
                        hook_str = "🔥 Dynamique" if report["hook"]["status"] == "dynamique" else "⚠️ Trop statique" if report["hook"]["status"] == "tres_statique" else "Moyen"

                        results.append({
                            "Vidéo": file.name,
                            "Score TikTok": f"{score} / 100",
                            "Statut": status,
                            "Format": format_str,
                            "Hook (0-3s)": hook_str,
                            "Audio": silence_str,
                            "Durée": f"{report['technical']['duration']}s",
                        })

                progress_bar.progress(100, text="Audit terminé !")
                st.session_state["tab3_audit_results"] = results

            if st.session_state.get("tab3_audit_results"):
                res_audit = st.session_state["tab3_audit_results"]
                st.success(f"📊 Audit terminé pour {len(res_audit)} vidéo(s) !")
                st.dataframe(res_audit, use_container_width=True)
                st.info("💡 Pour les vidéos à corriger, basculez sur l'option **'Conversion 9:16 en Rafale'** ci-dessus pour les convertir d'un coup !")


# ==========================================
# ONGLET 4 : VIGNETTES & COVERS HD
# ==========================================
with tab_covers:
    st.title("🖼️ Générateur Automatique de Vignettes (Cover Frames HD)")
    st.write(
        "L'algorithme de TikTok et vos spectateurs jugent votre vidéo sur la première image visible dans la grille. "
        "Cet outil analyse votre vidéo, extrait automatiquement les moments au plus fort contraste/netteté "
        "et génère une miniature 9:16 percutante avec titre de couverture."
    )

    cover_source_path = st.session_state.get("ready_video_path")
    cov_file = st.file_uploader(
        "Choisissez une vidéo (ou utilisez celle déjà chargée dans le Studio) :",
        type=["mp4", "mov"],
        key="uploader_covers",
    )
    if cov_file:
        tmp_cov = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tmp_cov.write(cov_file.read())
        tmp_cov.close()
        cover_source_path = tmp_cov.name

    if cover_source_path and os.path.exists(cover_source_path):
        st.success(f"🎬 Vidéo source prête pour extraction : `{os.path.basename(cover_source_path)}`")

        col_cov_act1, col_cov_act2 = st.columns([1, 1])
        with col_cov_act1:
            if st.button("🔍 Extraire les meilleures frames spectaculaires", key="btn_scan_covers", use_container_width=True):
                with st.spinner("Analyse du contraste et de la netteté en cours..."):
                    frames = extract_best_cover_frames(cover_source_path, max_candidates=12, top_k=4)
                    st.session_state["extracted_cover_frames"] = frames

        if st.session_state.get("extracted_cover_frames"):
            frames = st.session_state["extracted_cover_frames"]
            st.markdown("### 🏆 Top Frames Détectées (Classées par intensité visuelle)")
            cols_f = st.columns(len(frames))
            for i, f_data in enumerate(frames):
                with cols_f[i]:
                    st.image(f_data["frame_rgb"], caption=f_data["label"], use_container_width=True)
                    if st.button(f"Choisir #{i+1}", key=f"btn_pick_frame_{i}", use_container_width=True):
                        st.session_state["selected_cover_frame"] = f_data["frame_rgb"]

            selected_frame = st.session_state.get("selected_cover_frame", frames[0]["frame_rgb"])

            st.markdown("---")
            st.markdown("### 🎨 Personnaliser le Sticker de Couverture")
            col_stk1, col_stk2 = st.columns(2)
            with col_stk1:
                cover_title = st.text_input("Titre principal de la miniature :", value="COLLISION SPATIALE", key="txt_cov_title")
                cover_badge = st.text_input("Petit badge supérieur :", value="SIMULATION 3D", key="txt_cov_badge")
            with col_stk2:
                cover_style = st.selectbox("Style du sticker :", options=[("neon", "🔥 Néon TikTok (Rose/Blanc/Noir)"), ("gold", "⚡ Or Impact (Jaune/Noir)")], format_func=lambda x: x[1], key="sel_cov_style")[0]

            final_cover_rgb = create_cover_with_sticker(selected_frame, title_text=cover_title, badge_text=cover_badge, style=cover_style)
            st.image(final_cover_rgb, caption="Aperçu final de votre vignette TikTok 9:16", width=420)

            # Exportation image
            cover_pil = Image.fromarray(final_cover_rgb)
            img_buf = io.BytesIO()
            cover_pil.save(img_buf, format="JPEG", quality=95)
            img_bytes = img_buf.getvalue()

            col_cov_dl1, col_cov_dl2 = st.columns(2)
            with col_cov_dl1:
                st.download_button(
                    label="⬇️ Télécharger la vignette HD (.jpg)",
                    data=img_bytes,
                    file_name="vignette_tiktok_hd.jpg",
                    mime="image/jpeg",
                    key="btn_dl_cover_jpg",
                    use_container_width=True,
                )
            with col_cov_dl2:
                if st.button("☁️ Déposer la vignette dans Google Drive (AIvidéo)", key="btn_drv_cover", use_container_width=True):
                    tmp_cov_f = tempfile.mktemp(suffix="_vignette.jpg")
                    with open(tmp_cov_f, "wb") as f:
                        f.write(img_bytes)
                    up_cov_res = upload_video_to_gdrive(tmp_cov_f, destination_filename="vignette_tiktok_hd.jpg")
                    if up_cov_res.get("success"):
                        st.success("🎉 Vignette déposée avec succès dans votre Google Drive AIvidéo !")
                    else:
                        st.error(f"Erreur Drive : {up_cov_res.get('error')}")
    else:
        st.info("💡 Chargez une vidéo dans l'onglet **Scanner** ou **Studio 9:16**, ou déposez-en une ici pour extraire ses vignettes.")


# ==========================================
# ONGLET 5 : TITRES, SCRIPTS & HASHTAGS FYP
# ==========================================
with tab_captions:
    st.title("💡 Assistant Titres, Légendes & Hashtags FYP")
    st.write(
        "Une description bien calibrée et les bons hashtags augmentent l'indexation de votre vidéo par le moteur de recherche TikTok. "
        "Générez ici des propositions prêtes à copier-coller en 1 clic."
    )

    col_cp1, col_cp2 = st.columns([1, 1])
    with col_cp1:
        niche_selected = st.selectbox(
            "Thématique de votre vidéo :",
            options=list(NICHE_PRESETS.keys()),
            format_func=lambda k: NICHE_PRESETS[k]["name"],
            key="sel_niche_caption",
        )
    with col_cp2:
        keywords_input = st.text_input(
            "Mots-clés ou sujet spécifique (ex: fusée Starship, trou noir, collision) :",
            value="Astéroïde et collision avec la Terre",
            key="txt_keywords_caption",
        )

    captions_list = generate_captions(niche_selected, keywords_input)

    st.markdown("### 📝 Propositions optimisées pour l'engagement :")
    for idx, item in enumerate(captions_list):
        with st.expander(f"📌 {item['title']}", expanded=(idx == 0)):
            st.text_area(
                "Texte de description à copier :",
                value=item["caption"],
                height=130,
                key=f"area_cap_{idx}",
            )
            st.caption(f"🏷️ Hashtags ciblés : `{item['hashtags']}`")


# ==========================================
# ONGLET 6 : DOSSIER MAGIQUE (MAC 100% AUTO)
# ==========================================
with tab_magic:
    st.title("📂 Dossier Magique Mac (Zéro Clic 100% Automatisé)")
    st.write(
        "Le workflow ultime pour gagner du temps : déposez simplement vos fichiers vidéo dans un dossier sur votre Mac, "
        "et ils seront automatiquement convertis en 9:16 HD, nettoyés du silence d'intro et déposés dans votre Google Drive **AIvidéo** !"
    )

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown(
            """
            <div style='background: rgba(37, 244, 238, 0.08); border: 1px solid #25f4ee; border-radius: 10px; padding: 16px;'>
                <h4 style='color: #25f4ee; margin-top: 0;'>⚡ Comment ça fonctionne ?</h4>
                <ol style='padding-left: 20px; line-height: 1.8;'>
                    <li>Déposez vos rendus 3D/CGI ou vidéos dans le dossier <code>A_CONVERTIR_TIKTOK</code>.</li>
                    <li>Le script en arrière-plan détecte le fichier dès la fin de l'écriture.</li>
                    <li>Il coupe le silence, recadre au format 9:16 HD avec fond flou dynamique.</li>
                    <li>Il téléverse la vidéo directement dans votre Google Drive <strong>AIvidéo</strong>.</li>
                    <li>Une notification système apparaît sur votre Mac : <em>"Prêt pour l'iPad !"</em></li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_m2:
        st.markdown("#### 🚀 Lancer le Dossier Magique")
        watch_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "A_CONVERTIR_TIKTOK")
        try:
            os.makedirs(watch_path, exist_ok=True)
        except Exception:
            pass
        st.code(f"Dossier surveillé :\n{watch_path}", language="bash")

        import platform
        if platform.system() == "Darwin":
            if st.button("📂 Ouvrir le dossier A_CONVERTIR_TIKTOK dans le Finder", key="btn_open_magic_finder", use_container_width=True):
                subprocess.run(["open", watch_path])
                st.toast("Dossier ouvert dans le Finder !")

        st.markdown("##### 🖥️ Lancement en 1 double-clic :")
        st.write("Un fichier exécutable **`lancer_dossier_magique.command`** est disponible dans votre dossier. Double-cliquez dessus depuis votre Finder pour lancer la surveillance en tâche de fond !")

        # Affichage du journal d'activité
        st.markdown("##### 📜 Journal d'activité récent :")
        log_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "magic_folder.log")
        if os.path.exists(log_p):
            with open(log_p, "r", encoding="utf-8") as f_log:
                logs = f_log.readlines()[-8:]
            st.code("".join(logs) if logs else "En attente de nouvelles vidéos...", language="text")
        else:
            st.info("Aucune vidéo traitée récemment. Le journal s'affichera dès le premier dépôt.")

        # Affichage des vidéos générées prêtes dans export_tiktok
        st.markdown("##### 🎬 Vidéos prêtes pour publication (`export_tiktok`) :")
        exp_dir = os.path.join(watch_path, "export_tiktok")
        if os.path.exists(exp_dir):
            video_files = [
                f for f in sorted(os.listdir(exp_dir), reverse=True)
                if f.lower().endswith((".mp4", ".mov")) and not f.startswith(".")
            ]
            if video_files:
                for vf in video_files[:6]:
                    vf_path = os.path.join(exp_dir, vf)
                    size_mb = os.path.getsize(vf_path) / (1024 * 1024)
                    icon = "🅰️" if ("_A_14s" in vf or "VARIANTE_A" in vf) else ("🅱️" if ("_B_15s" in vf or "VARIANTE_B" in vf) else "🎬")
                    with st.expander(f"{icon} {vf} ({size_mb:.1f} Mo)", expanded=("_A_14s" in vf or "_B_15s" in vf or "VARIANTE" in vf)):
                        st.video(vf_path)
                        with open(vf_path, "rb") as f_dl:
                            st.download_button("⬇️ Télécharger ce fichier", f_dl.read(), file_name=vf, key=f"dl_tab6_{vf}", use_container_width=True)
            else:
                st.info("Aucune vidéo exportée pour l'instant.")


# ==========================================
# ONGLET 7 : ENVOYER & PUBLIER SUR TIKTOK
# ==========================================
with tab_publish:
    st.title("🚀 Envoyer & Publier sur TikTok")
    st.write(
        "Finalisez votre publication avec une description optimisée pour le SEO TikTok "
        "et ouvrez directement l'application pour publier votre vidéo !"
    )

    ready_path = st.session_state.get("ready_video_path")
    ready_name = st.session_state.get("ready_video_name", "Votre vidéo")

    col_pub_left, col_pub_right = st.columns([1, 1])

    with col_pub_left:
        st.markdown("### 1. Vidéo prête pour publication")
        if ready_path and os.path.exists(ready_path):
            st.success(f"✅ Vidéo sélectionnée : **{ready_name}**")
            st.video(ready_path)

            import platform
            is_mac = platform.system() == "Darwin"

            col_btn_f1, col_btn_f2 = st.columns(2)
            with col_btn_f1:
                if is_mac:
                    if st.button("📂 Révéler le fichier dans le Finder", key="btn_reveal_finder"):
                        subprocess.run(["open", "-R", ready_path])
                        st.toast("Dossier Finder ouvert avec le fichier sélectionné !")
                else:
                    st.info("💡 Enregistrez la vidéo ci-contre directement dans vos Photos iPad.")
            with col_btn_f2:
                with open(ready_path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Enregistrer « {ready_name} »",
                        data=f.read(),
                        file_name=ready_name or "video_corrige.mp4",
                        mime="video/mp4",
                        key="btn_pub_download",
                        use_container_width=True,
                    )

            col_drive_pub1, col_drive_pub2 = st.columns(2)
            with col_drive_pub1:
                if st.button("☁️ Déposer directement dans AIvidéo (Drive)", key="btn_pub_direct_drive", use_container_width=True):
                    with st.spinner("Téléversement direct vers Google Drive (AIvidéo)..."):
                        up_res = upload_video_to_gdrive(ready_path, destination_filename=ready_name)
                        if up_res.get("success"):
                            st.success("🎉 Vidéo déposée directement dans votre dossier AIvidéo !")
                            st.session_state["tab4_drive_link"] = up_res.get("web_link")
                        else:
                            st.error(f"Erreur d'envoi Google Drive : {up_res.get('error')}")

            with col_drive_pub2:
                target_link = st.session_state.get("tab4_drive_link", GOOGLE_DRIVE_FOLDER_URL)
                drive_btn_title = "📂 Voir la vidéo sur Drive" if "tab4_drive_link" in st.session_state else "📂 Accéder au dossier AIvidéo"
                st.link_button(
                    drive_btn_title,
                    target_link,
                    use_container_width=True,
                )
        else:
            st.warning("⚠️ Aucune vidéo n'a encore été analysée ou convertie.")
            st.info("Chargez d'abord une vidéo dans l'onglet **Scanner** ou **Convertisseur**, ou testez avec les boutons ci-dessous.")

        st.markdown("---")
        st.markdown("### 2. Conseils pour passer les 800 vues au moment de l'envoi")
        st.markdown(
            """
            - ⏰ **Meilleures heures de publication** : 12h00 - 13h30 ou 18h30 - 21h00.
            - 🎵 **Son tendance en sourdine** : Ajoutez une musique virale en arrière-plan à 5% de volume pour surfer sur l'algorithme.
            - 🖼️ **Couverture percutante** : Choisissez une frame avec du texte explicite comme couverture.
            """
        )

    with col_pub_right:
        st.markdown("### 3. Lanceur TikTok (En 1 clic)")

        import platform
        is_mac = platform.system() == "Darwin"

        # Carte 1 : Application TikTok
        st.markdown(
            """
            <div class='action-card'>
                <h4>📱 Lancer TikTok</h4>
                <p>Ouvre directement TikTok pour téléverser votre vidéo.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_app1, col_app2 = st.columns(2)
        with col_app1:
            if is_mac:
                if st.button("📱 Lancer l'Application TikTok", key="btn_open_tiktok_app"):
                    try:
                        res_app = subprocess.run(["open", "/Applications/App for TikTok.app"], capture_output=True, text=True)
                        if res_app.returncode == 0:
                            st.success("Application TikTok lancée !")
                        else:
                            subprocess.run(["open", "https://www.tiktok.com/upload"])
                            st.info("Portail TikTok ouvert dans votre navigateur !")
                    except Exception as e:
                        st.error(f"Erreur d'ouverture : {e}")
            else:
                st.link_button(
                    "📱 Ouvrir TikTok (App ou Web)",
                    "https://www.tiktok.com/upload",
                    use_container_width=True,
                )

        with col_app2:
            st.link_button(
                "🌐 TikTok Studio Web (Créateurs)",
                "https://www.tiktok.com/tiktokstudio/upload",
                use_container_width=True,
            )

        # Carte 2 : CapCut Desktop / Web
        st.markdown(
            """
            <div class='action-card'>
                <h4>🎬 CapCut</h4>
                <p>Besoin d'ajouter des sous-titres animés automatiques ou des effets ?</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if is_mac:
            if st.button("🎬 Ouvrir CapCut sur Mac", key="btn_open_capcut"):
                subprocess.run(["open", "/Applications/CapCut.app"])
                st.success("CapCut lancé !")
        else:
            st.link_button("🎬 Ouvrir CapCut Web", "https://www.capcut.com/editor", use_container_width=True)

        st.markdown("---")
        st.markdown("### 4. Générateur de Titre & Légende SEO")

        if selected_style == "action":
            default_caption = (
                "Regardez ce qui arrive lors d'un impact à plus de 40 000 km/h... 🚀💥\n\n"
                "La force de l'onde de choc est tout simplement inimaginable.\n\n"
                "Quel événement spatial voulez-vous voir ensuite ? Dites-le en commentaire ! 👇\n\n"
                "#espace #science #astronomie #simulation #collision #fusee #pourtoi #fyp"
            )
        else:
            default_caption = (
                "Voici pourquoi vous faites probablement cette erreur sans le savoir... 🤯\n\n"
                "Le secret repose sur un détail que 99% des gens ignorent.\n\n"
                "Vous étiez au courant ? Répondez en commentaire ! 👇\n\n"
                "#apprendre #astuce #conseil #motivation #faits #pourtoi #fyp"
            )

        caption_text = st.text_area(
            "Légende & Mots-clés optimisés pour l'algorithme :",
            value=default_caption,
            height=160,
        )
        st.caption("💡 Copiez cette description et collez-la directement dans TikTok lors du dépôt de la vidéo.")
