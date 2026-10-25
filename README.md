# VetPod — podcast hebdomadaire de veille vétérinaire (petits animaux)

Chaque semaine, VetPod :

1. **collecte** sur PubMed (API officielle NCBI) les articles entrés dans la base durant les 7 derniers jours, publiés dans ~30 revues vétérinaires internationales à comité de lecture (`sources.yaml`) ;
2. **filtre** : chien et chat uniquement (NAC en option), résumé obligatoire, exclusion des lettres, éditoriaux, erratums, études sur bovins/équidés/porcins/volailles et modèles murins, cas cliniques hors revues de tier 1 ;
3. **évalue** le niveau de preuve (méta-analyse, essai randomisé, cohorte, rétrospective…) et le rang de la revue, puis retient les meilleures études (18 max, 4 par discipline) ;
4. **classe** chaque étude dans l'une des 22 disciplines (dermatologie, cardiologie, oncologie, néphrologie, gastro-entérologie, endocrinologie, neurologie, ophtalmologie, chirurgie, anesthésie, urgences, imagerie, infectiologie, hématologie-immunologie, médecine interne, etc.) ;
5. **rédige** avec Claude une fiche par étude puis un script en français (un narrateur ou dialogue à deux voix), en s'appuyant **uniquement sur les résumés publiés** ;
6. **génère l'audio** (voix neuronales suisses romandes par défaut, gratuites) et publie l'épisode, les notes avec liens PubMed/DOI, une page web et un **flux RSS** compatible Apple Podcasts / Spotify.

## Installation locale

```bash
pip install -r requirements.txt        # + ffmpeg installé sur la machine
export ANTHROPIC_API_KEY=sk-ant-...     # clé API Claude (console.anthropic.com)
python -m vetpod run                    # épisode complet
python -m vetpod run --no-audio         # script + notes seulement
python -m vetpod run --no-llm           # sans IA (lecture structurée des conclusions, en anglais)
python -m vetpod query                  # voir la requête PubMed
python -m pytest -q tests               # tests hors ligne
```

Résultats : `docs/` (mp3, `feed.xml`, `index.html`, notes) et `work/` (script, fiches JSON).

## Automatisation hebdomadaire gratuite (GitHub)

1. Créez un dépôt GitHub et poussez ce dossier.
2. *Settings → Secrets and variables → Actions* : ajoutez `ANTHROPIC_API_KEY` (et `NCBI_API_KEY`, facultatif, gratuit sur ncbi.nlm.nih.gov).
3. *Settings → Pages* : source « Deploy from a branch », branche `main`, dossier `/docs`.
4. Dans `config.yaml`, remplacez `base_url` par `https://<utilisateur>.github.io/<dépôt>` et ajoutez `docs/cover.jpg` (3000×3000).
5. Le workflow `.github/workflows/weekly.yml` tourne chaque lundi matin (bouton *Run workflow* pour tester).
6. Soumettez `https://<utilisateur>.github.io/<dépôt>/feed.xml` à Apple Podcasts Connect / Spotify for Creators, ou abonnez-vous directement à ce flux dans votre application de podcast.

## Personnalisation

- `sources.yaml` : ajouter/retirer des revues (titre abrégé NLM), changer leur rang.
- `vetpod/disciplines.py` : disciplines et mots-clés de classement.
- `config.yaml` : durée, nombre d'études, voix (`fr-FR-DeniseNeural`, `fr-FR-HenriNeural`…), NAC, 1 ou 2 animateurs.

## Limites à connaître

- Les synthèses reposent sur les **résumés**, pas sur les textes intégraux (souvent payants) ; le podcast le rappelle à chaque épisode.
- Un délai d'indexation PubMed de quelques jours existe ; la fenêtre « date d'entrée PubMed » évite d'oublier des articles.
- Le contenu est généré automatiquement : il s'agit d'un outil de veille, pas d'une recommandation clinique. Une relecture humaine avant diffusion publique est conseillée.
- Coût indicatif : généralement moins d'un dollar d'API Claude par épisode ; NCBI, Edge TTS et GitHub Pages sont gratuits.
