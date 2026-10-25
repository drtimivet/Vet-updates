"""Rédaction : synthèse de chaque étude puis script de l'épisode (via Claude),
avec un mode de secours sans IA."""
from __future__ import annotations

import json
import os
import re
from collections import OrderedDict

from .disciplines import DISCIPLINES, label, order
from .pubmed import Article

SUMMARY_SYSTEM = """Tu es vétérinaire, rédacteur scientifique pour une revue de veille destinée aux
praticiens en médecine des animaux de compagnie. Règles absolues :
- Tu t'appuies EXCLUSIVEMENT sur le titre et le résumé fournis. Aucune information extérieure,
  aucune extrapolation, aucun chiffre qui ne figure pas dans le résumé.
- Si une information manque (effectif, durée, puissance statistique...), tu ne l'inventes pas.
- Tu restitues fidèlement les conclusions des auteurs, avec leur prudence, et tu signales les limites
  évidentes (petit effectif, rétrospectif, absence de groupe témoin, étude sur animaux sains...).
- Tu écris en français, terminologie vétérinaire francophone exacte (noms de molécules en DCI).
Réponds uniquement par un objet JSON valide."""

SUMMARY_USER = """Étude publiée dans {journal} ({date}). Espèce(s) : {species}. Type détecté : {evidence}.
Disciplines possibles (clé: libellé) :
{disciplines}
Classement automatique proposé : {discipline}

TITRE : {title}
RÉSUMÉ :
{abstract}

Renvoie ce JSON :
{{
  "discipline": "<clé de la liste ci-dessus la plus pertinente>",
  "titre_fr": "<titre traduit, concis>",
  "question": "<question de recherche en une phrase>",
  "methode": "<type d'étude, population, effectif si indiqué>",
  "resultats": ["<résultat clé 1 avec chiffres du résumé>", "..."],
  "limites": "<limites principales, ou 'Non précisées dans le résumé'>",
  "message_clinique": "<ce que le praticien peut retenir, formulé avec la prudence appropriée>",
  "pertinence": <1 à 5, intérêt pour un praticien généraliste petits animaux>
}}"""

SCRIPT_SYSTEM = """Tu écris le script d'un podcast audio francophone de veille scientifique vétérinaire
pour praticiens petits animaux. Le texte sera lu par une synthèse vocale : phrases naturelles à l'oral,
pas de listes, pas de markdown, pas d'abréviations ambiguës (écris « par exemple », « milligrammes par kilo »),
nombres écrits de façon prononçable. Tu n'ajoutes AUCUNE information qui ne figure pas dans les fiches
fournies : chaque affirmation scientifique provient d'une fiche. Tu cites la revue de chaque étude.
Tu rappelles en conclusion que les résumés ne remplacent pas la lecture des articles complets.
Réponds uniquement par du JSON valide."""

SCRIPT_USER = """Épisode {episode} — du {week}. Durée visée : environ {minutes} minutes
(≈ {words} mots). {hosts_desc}

Structure attendue : courte introduction (thèmes de la semaine) ; puis une rubrique par discipline,
annoncée clairement (« Passons à la dermatologie ») ; pour chaque étude : contexte, méthode,
résultats chiffrés, limites, message clinique ; transitions fluides ; conclusion brève.

Fiches des études, regroupées par discipline :
{fiches}

Renvoie : {{"segments": [{{"speaker": <index de l'animateur, 0{speaker_hint}>, "text": "..."}}]}}
Un segment = une prise de parole (2 à 6 phrases)."""


class Writer:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.enabled = cfg.get("enabled", True) and bool(os.getenv("ANTHROPIC_API_KEY"))
        self.model = cfg.get("model", "claude-sonnet-5-5")
        self.hosts = cfg.get("host_names", ["Claire", "Thomas"])[: max(1, cfg.get("hosts", 1))]
        if self.enabled:
            import anthropic
            self.client = anthropic.Anthropic()

    # ---------- appels LLM ----------
    def _ask_json(self, system: str, user: str, max_tokens: int) -> dict:
        msg = self.client.messages.create(
            model=self.model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}],
        )
        txt = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        m = re.search(r"\{.*\}", txt, re.S)
        return json.loads(m.group(0) if m else txt)

    def summarize(self, a: Article) -> dict:
        if not self.enabled:
            return fallback_summary(a)
        disc = "\n".join(f"- {k}: {v['label']}" for k, v in DISCIPLINES.items())
        try:
            s = self._ask_json(SUMMARY_SYSTEM, SUMMARY_USER.format(
                journal=a.journal, date=a.pub_date, species=", ".join(a.species), evidence=a.evidence,
                disciplines=disc, discipline=a.discipline, title=a.title, abstract=a.abstract), 1500)
        except Exception as e:  # robustesse : un échec n'arrête pas l'épisode
            print(f"  ! résumé IA impossible pour PMID {a.pmid} ({e}) — mode de secours")
            return fallback_summary(a)
        if s.get("discipline") in DISCIPLINES:
            a.discipline = s["discipline"]
        return s

    def script(self, articles: list[Article], episode: int, week: str, minutes: int) -> list[dict]:
        groups = group_by_discipline(articles)
        if not self.enabled:
            return fallback_script(groups, episode, week, self.hosts)
        fiches = []
        for d, arts in groups.items():
            fiches.append(f"### {label(d)}")
            for a in arts:
                s = a.summary
                fiches.append(json.dumps({
                    "revue": a.journal, "auteurs": a.first_author, "espèces": a.species,
                    "niveau_de_preuve": a.evidence, **{k: s.get(k) for k in
                    ("titre_fr", "question", "methode", "resultats", "limites", "message_clinique")}
                }, ensure_ascii=False))
        if len(self.hosts) > 1:
            hosts_desc = (f"Deux animateurs vétérinaires dialoguent : {self.hosts[0]} (index 0) et "
                          f"{self.hosts[1]} (index 1). Ils alternent naturellement, se posent des questions, "
                          f"mais restent factuels.")
            hint = " ou 1"
        else:
            hosts_desc = f"Un seul animateur : {self.hosts[0]} (index 0)."
            hint = ""
        try:
            data = self._ask_json(SCRIPT_SYSTEM, SCRIPT_USER.format(
                episode=episode, week=week, minutes=minutes, words=minutes * 150,
                hosts_desc=hosts_desc, fiches="\n".join(fiches), speaker_hint=hint), 16000)
            segs = [s for s in data["segments"] if s.get("text", "").strip()]
            for s in segs:
                s["speaker"] = int(s.get("speaker", 0)) % len(self.hosts)
            return segs
        except Exception as e:
            print(f"  ! script IA impossible ({e}) — mode de secours")
            return fallback_script(groups, episode, week, self.hosts)


def group_by_discipline(articles: list[Article]) -> "OrderedDict[str, list[Article]]":
    g: OrderedDict[str, list[Article]] = OrderedDict()
    for a in sorted(articles, key=lambda x: (order(x.discipline), -x.score)):
        g.setdefault(a.discipline, []).append(a)
    return g


# ---------- mode de secours (sans IA) ----------
def _conclusion(abstract: str) -> str:
    for line in abstract.splitlines():
        head, _, body = line.partition(":")
        if body and re.match(r"(CONCLUSION|CLINICAL (RELEVANCE|SIGNIFICANCE|IMPORTANCE))", head.strip().upper()):
            return body.strip()
    sents = re.split(r"(?<=[.!?])\s+", abstract.strip())
    return " ".join(sents[-2:])


def fallback_summary(a: Article) -> dict:
    return {"discipline": a.discipline, "titre_fr": a.title, "question": "", "methode": a.evidence,
            "resultats": [], "limites": "", "message_clinique": _conclusion(a.abstract), "pertinence": 3}


def fallback_script(groups, episode: int, week: str, hosts: list[str]) -> list[dict]:
    n = sum(len(v) for v in groups.values())
    segs = [{"speaker": 0, "text": (
        f"Bonjour et bienvenue dans l'épisode {episode} de votre veille scientifique vétérinaire, "
        f"du {week}. Au programme, {n} études publiées dans des revues à comité de lecture, "
        f"réparties en {len(groups)} rubriques : " + ", ".join(label(d).lower() for d in groups) + ".")}]
    i = 0
    for d, arts in groups.items():
        segs.append({"speaker": i % len(hosts), "text": f"Rubrique {label(d).lower()}."})
        for a in arts:
            i += 1
            segs.append({"speaker": i % len(hosts), "text": (
                f"Étude publiée dans {a.journal}, par {(a.first_author or 'une équipe').rstrip('.')}. "
                f"Type d'étude : {a.evidence.lower()}. Titre original : {a.title} "
                f"Conclusion des auteurs : {a.summary.get('message_clinique') or _conclusion(a.abstract)}")})
    segs.append({"speaker": 0, "text": (
        "C'est la fin de cet épisode. Les références complètes sont dans les notes de l'épisode ; "
        "ces synthèses ne remplacent pas la lecture des articles. À la semaine prochaine.")})
    return segs
