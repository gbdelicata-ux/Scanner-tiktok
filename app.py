"""
Application Streamlit : Scanner, Convertisseur & Publication TikTok
Permet d'auditer vos vidéos avant publication, de convertir automatiquement
au format 9:16 optimal (1080x1920) et d'ouvrir l'application TikTok pour publier.
"""

import os
import subprocess
import tempfile
import streamlit as st
import cv2
import numpy as np

from analyzer import TikTokVideoAnalyzer
from safe_zone import render_tiktok_overlay
from converter import TikTokVideoConverter

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

# Onglets principaux
tab_scan, tab_convert, tab_publish = st.tabs([
    "📊 Scanner & Audit TikTok",
    "🪄 Convertisseur 9:16",
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
                with col_c3:
                    st.write("")
                    st.write("")
                    convert_now_btn = st.button("🚀 Corriger & Télécharger la vidéo", key="btn_fix_now")

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
                            st.success(f"Vidéo convertie avec succès en {res['resolution']} ({res['file_size_mb']} Mo) !")
                            with open(out_fixed, "rb") as f:
                                st.download_button(
                                    label=f"⬇️ Télécharger « {download_filename} »",
                                    data=f.read(),
                                    file_name=download_filename,
                                    mime="video/mp4",
                                    key="dl_btn_fixed",
                                )
                        else:
                            st.error(f"Erreur lors de la conversion : {res.get('error')}")

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
    st.write(
        "Transformez n'importe quelle vidéo (horizontale 16:9, carrée ou basse résolution) "
        "en format vertical immersif optimisé pour l'algorithme TikTok."
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

        st.info(f"📁 Fichier d'origine détecté : **{orig_w}x{orig_h}** ({orig_fps} FPS)")

        st.markdown("### 🎛️ Options de conversion")
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
                "Couper le début de la vidéo (pour supprimer un silence ou temps mort) :",
                min_value=0.0,
                max_value=3.0,
                value=0.0,
                step=0.1,
                format="%.1f secondes",
            )

        if st.button("⚡ Lancer la conversion TikTok HD", key="btn_run_conversion"):
            with st.spinner("Conversion en cours avec encodage H.264 certifié TikTok..."):
                converter = TikTokVideoConverter()
                output_converted = tempfile.mktemp(suffix="_tiktok_converted.mp4")
                res = converter.convert_to_tiktok_format(
                    input_path=conv_input_path,
                    output_path=output_converted,
                    mode=selected_mode,
                    trim_start_sec=trim_seconds,
                )

            if res["success"]:
                raw_name = conv_upload.name if conv_upload else "video"
                base_name, _ = os.path.splitext(raw_name)
                download_filename = f"{base_name}_corrige.mp4"

                st.session_state["ready_video_path"] = output_converted
                st.session_state["ready_video_name"] = download_filename
                st.success(f"🎉 Vidéo convertie en {res['resolution']} ! Taille : {res['file_size_mb']} Mo")

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
                        )
                    st.info("👉 Rendez-vous dans l'onglet **'🚀 Envoyer & Publier'** pour lancer TikTok !")
            else:
                st.error(f"Erreur de conversion : {res.get('error')}")


# ==========================================
# ONGLET 3 : ENVOYER & PUBLIER SUR TIKTOK
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
