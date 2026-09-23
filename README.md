# 📱 TikTok Video Pre-Flight Scanner
> Outil d'audit algorithmique et d'optimisation pré-publication pour dépasser le palier des 800 vues sur TikTok.

---

## 🎯 Pourquoi cet outil ?
Sur TikTok, chaque vidéo est testée auprès d'une première vague de 200 à 800 personnes. Si durant ces premières secondes, les métriques clés (Hook, Safe Zone, Son, Rétention) sont sous-optimales, la distribution s'arrête net.

Ce scanner analyse votre vidéo localement avant publication et vous donne un **Score de Préparation (0-100)** ainsi qu'une checklist concrète.

---

## 🚀 Lancement rapide

Dans votre terminal :
```bash
./start.sh
```
Ou manuellement :
```bash
source .venv/bin/activate
streamlit run app.py
```
L'interface s'ouvrira automatiquement dans votre navigateur (à l'adresse `http://localhost:8501`).

---

## 🔍 Ce que le scanner vérifie

1. **📱 Safe Zone Officielle TikTok** :
   - Superposition d'un calque réaliste avec l'interface de TikTok (boutons J'aime, Commentaires, Partage, Son, Légende).
   - Vous permet de vérifier immédiatement qu'aucun sous-titre ou élément clé n'est masqué par les boutons de droite ou la description.

2. **⚡ Hook des 3 premières secondes (0 - 3s)** :
   - Mesure la variation visuelle et la dynamique du plan.
   - Alerte si le plan de départ est trop statique (cause n°1 de swipe immédiat sur les plans de facecam/personnes).

3. **🔊 Audio & Détection de silence d'entrée** :
   - Détecte si un blanc sonore supérieur à 0.3s existe au tout début de la vidéo.
   - Vérifie la présence d'une piste sonore active.

4. **🔁 Potentiel de Boucle Infinie (Loop Hack)** :
   - Compare la toute première frame et la dernière frame.
   - Calcule la fluidité d'enchaînement pour inciter les spectateurs à regarder la vidéo une deuxième fois (ce qui fait exploser le taux de complétion au-delà de 100%).

5. **📐 Respect strict du format 9:16 (1080x1920)** :
   - Détection des formats horizontaux ou carrés qui divisent par 3 la mise en avant algorithmique.

---

## 💡 Conseils spécifiques par format

### Pour vos plans statiques / personnes :
* **Punch-in Zoom** : Ajoutez un zoom de 5 à 10% toutes les 2,5 à 3 secondes pour relancer l'attention.
* **Sous-titres dynamiques** : Placez des sous-titres centrés dans la zone verte (Safe Zone).
* **Coupe à la micro-seconde** : Supprimez la respiration initiale avant le premier mot.

### Pour vos scènes d'action / fusées / collisions :
* **Hook de curiosité textuel** : Affichez un texte percutant dès 0.0s (*« Ce qui arrive si... »*).
* **Sound Design** : Un son 'Whoosh' ou une basse lourde dès la première frame.
* **Boucle** : Faites coïncider la fin du mouvement avec l'entrée au début.
