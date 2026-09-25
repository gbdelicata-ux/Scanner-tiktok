"""
Module de génération de titres, légendes (captions) et hashtags pour TikTok.
Optimisé pour maximiser le taux d'engagement (commentaires, partages, complétion)
et percer l'algorithme au-delà des 800 vues.
"""

from typing import Dict, List, Any


NICHE_PRESETS = {
    "espace_astronomie": {
        "name": "🪐 Espace, Fusées & Astronomie",
        "hashtags": ["#astronomie", "#espace", "#science", "#univers", "#fusee", "#nasa", "#spacex", "#pourtoi", "#fyp", "#cultureg"],
        "angles": [
            {
                "title": "Style Intrigue & Débat (Maximise les commentaires)",
                "template": "Que se passerait-il réellement si cet événement arrivait sur Terre ? 😱 Donnez votre avis en commentaire !\n\n{keywords}\n\n{hashtags}",
            },
            {
                "title": "Style Révélation Scientifique (Maximise les partages)",
                "template": "Ce que la plupart des gens ignorent sur ce phénomène spatial... 🪐 Regardez bien jusqu'au bout !\n\n{keywords}\n\n{hashtags}",
            },
            {
                "title": "Style Choc & Punchline (Maximise les vues rapides)",
                "template": "La vitesse et la puissance de cet engin sont tout simplement colossales 🚀\n\n{keywords}\n\n{hashtags}",
            },
        ],
    },
    "cgi_simulation": {
        "name": "💻 3D, CGI & Simulation",
        "hashtags": ["#cgi", "#3danimation", "#blender3d", "#vfx", "#simulation", "#scifi", "#rendu3d", "#fypfrance", "#pourtoi"],
        "angles": [
            {
                "title": "Style Défi Technique & Réalisme",
                "template": "Plus de 20 heures de calcul pour simuler cette collision en haute fidélité 💥 Vous en pensez quoi ?\n\n{keywords}\n\n{hashtags}",
            },
            {
                "title": "Style Test de Réaction / Rétention",
                "template": "Attendez la 5e seconde pour voir la déflagration complète... 🤯\n\n{keywords}\n\n{hashtags}",
            },
            {
                "title": "Style Curiosité & Détails Cachés",
                "template": "Avez-vous remarqué le détail caché à la fin de cette séquence 3D ? 👀\n\n{keywords}\n\n{hashtags}",
            },
        ],
    },
    "facecam_conseil": {
        "name": "🎙️ Facecam, Culture & Conseils",
        "hashtags": ["#astuces", "#conseilstiktok", "#secret", "#motivation", "#developpement", "#apprendresurtiktok", "#fyp"],
        "angles": [
            {
                "title": "Style Interpellation Directe",
                "template": "Si vous faites encore cette erreur en 2026, écoutez bien attentivement ce conseil 👇\n\n{keywords}\n\n{hashtags}",
            },
            {
                "title": "Style Récit & Storytelling",
                "template": "Pourquoi personne ne vous parle de cette règle fondamentale ? La réponse va vous surprendre 💡\n\n{keywords}\n\n{hashtags}",
            },
            {
                "title": "Style Question Finale (Appel aux commentaires)",
                "template": "Et vous, vous auriez réagi comment dans cette situation ? Répondez honnêtement en commentaire ! 💬\n\n{keywords}\n\n{hashtags}",
            },
        ],
    },
}


def generate_captions(niche_key: str, topic_keywords: str = "") -> List[Dict[str, str]]:
    """
    Génère 3 propositions de légendes percutantes avec hashtags adaptés.
    """
    niche = NICHE_PRESETS.get(niche_key, NICHE_PRESETS["espace_astronomie"])
    hashtags_str = " ".join(niche["hashtags"])
    clean_kw = f"🔎 Sujet : {topic_keywords.strip()}" if topic_keywords.strip() else ""

    results = []
    for angle in niche["angles"]:
        content = angle["template"].format(
            keywords=clean_kw,
            hashtags=hashtags_str,
        ).strip()
        results.append({
            "title": angle["title"],
            "caption": content,
            "hashtags": hashtags_str,
        })

    return results
