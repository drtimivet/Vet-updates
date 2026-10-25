"""Filtrage (espèces, qualité), niveau de preuve, classement par discipline et sélection."""
from __future__ import annotations

import re
from collections import defaultdict

from .disciplines import DISCIPLINES, DEFAULT
from .pubmed import Article, EXCLUDED_PUBTYPES

SPECIES_PATTERNS = {
    "chien": r"\b(dogs?|canine|canines|puppies|puppy|bitch(es)?)\b",
    "chat": r"\b(cats?|feline|felines|kittens?|queens)\b",
    "lapin": r"\brabbits?\b",
    "furet": r"\bferrets?\b",
    "cobaye": r"\bguinea pigs?\b",
    "rongeur de compagnie": r"\b(chinchillas?|hamsters?|pet rats?|gerbils?)\b",
    "oiseau de compagnie": r"\b(parrots?|psittacines?|pet birds?|budgerigars?|cockatiels?)\b",
}
EXOTICS = {"lapin", "furet", "cobaye", "rongeur de compagnie", "oiseau de compagnie"}

# Espèces de rente / équidés / faune : un article qui ne parle QUE de ces espèces est écarté.
NON_PET = r"\b(cattle|cows?|bovine|dairy|calves|pigs?|swine|porcine|sows?|piglets?|sheep|ovine|lambs?|" \
          r"goats?|caprine|horses?|equine|foals?|mares?|poultry|chickens?|broilers?|layers|fish|" \
          r"salmon|camels?|wildlife|deer|wild boar|mink|bees?)\b"

# Modèles de laboratoire (souris, rat) — l'étude n'est pas de la clinique petits animaux.
LAB_MODEL = r"\b(mice|mouse|murine|rats?\b(?! terrier)|in vitro only)\b"

EVIDENCE_RULES = [  # (étiquette FR, poids, déclencheurs pubtype / texte)
    ("Méta-analyse / revue systématique", 5, ["Meta-Analysis", "Systematic Review"],
     r"\b(meta-analys[ie]s|systematic review)\b"),
    ("Essai contrôlé randomisé", 5, ["Randomized Controlled Trial"],
     r"\brandomi[sz]ed\b.*\b(controlled|blinded|placebo)\b|\b(double|single)[- ]blind"),
    ("Essai clinique", 4, ["Clinical Trial", "Controlled Clinical Trial", "Clinical Trial, Phase II",
                           "Clinical Trial, Phase III"],
     r"\bclinical trial\b"),
    ("Étude prospective / cohorte", 3, ["Observational Study"],
     r"\b(prospective|cohort study|longitudinal)\b"),
    ("Étude rétrospective", 2, [], r"\b(retrospective(ly)?|medical records were reviewed|case series)\b"),
    ("Étude transversale", 2, [], r"\b(cross-sectional|survey|questionnaire)\b"),
    ("Étude expérimentale", 2, [], r"\b(experimental(ly)?|healthy (beagle|dog|cat)s|research colony|ex vivo|cadaver)"),
    ("Revue narrative", 1, ["Review"], r"$^"),
    ("Cas clinique", 0, ["Case Reports"], r"\b(case report|we describe a|a \d+-year-old)\b"),
]


def detect_species(a: Article) -> list[str]:
    text = f"{a.title} {a.abstract} {' '.join(a.mesh)}".lower()
    found = [sp for sp, pat in SPECIES_PATTERNS.items() if re.search(pat, text)]
    if "Dogs" in a.mesh and "chien" not in found:
        found.append("chien")
    if "Cats" in a.mesh and "chat" not in found:
        found.append("chat")
    return found


def is_pet_relevant(a: Article, include_exotics: bool) -> bool:
    """Le chien/chat (ou NAC) doit être l'espèce étudiée, pas une mention marginale."""
    sp = detect_species(a)
    allowed = {"chien", "chat"} | (EXOTICS if include_exotics else set())
    pets = [s for s in sp if s in allowed]
    if not pets:
        return False
    title = a.title.lower()
    title_pets = any(re.search(SPECIES_PATTERNS[s], title) for s in pets)
    title_nonpet = re.search(NON_PET, title) or re.search(LAB_MODEL, title)
    if title_nonpet and not title_pets:
        return False
    # Si le chien/chat n'apparaît qu'une fois dans un résumé centré sur d'autres espèces, on écarte.
    text = f"{a.title} {a.abstract}".lower()
    pet_hits = sum(len(re.findall(SPECIES_PATTERNS[s], text)) for s in pets)
    other_hits = len(re.findall(NON_PET, text)) + len(re.findall(LAB_MODEL, text))
    return pet_hits >= 2 or title_pets or (pet_hits >= 1 and other_hits == 0)


def evidence_level(a: Article) -> tuple[str, int]:
    text = f"{a.title} {a.abstract}".lower()
    for lab, w, ptypes, pat in EVIDENCE_RULES:
        if any(p in a.pub_types for p in ptypes) or re.search(pat, text):
            return lab, w
    return "Étude originale", 2


def classify(a: Article, hint: str | None = None) -> str:
    title = a.title.lower()
    body = f"{a.abstract} {' '.join(a.keywords)} {' '.join(a.mesh)}".lower()
    scores = defaultdict(float)
    for key, d in DISCIPLINES.items():
        for kw in d["keywords"]:
            pat = r"\b" + re.escape(kw)
            scores[key] += 3 * len(re.findall(pat, title)) + len(re.findall(pat, body))
    # disciplines "transversales" : on les pénalise pour laisser gagner la spécialité
    for generic in ("epidemiologie", "pharmacologie", "biologie", "medecine_interne"):
        scores[generic] *= 0.6
    if hint:
        scores[hint] += 4
    best = max(scores, key=scores.get) if scores else DEFAULT
    return best if scores[best] >= 2 else (hint or DEFAULT)


def journal_info(a: Article, journals: list[dict]) -> dict:
    ab = a.journal_abbrev.lower().replace(".", "")
    for j in journals:
        if j["pubmed"].lower().replace(".", "") == ab or j["name"].lower() == a.journal.lower():
            return j
    for j in journals:  # correspondance partielle (ex. variantes de titre)
        if j["pubmed"].lower().split(" (")[0] in ab:
            return j
    return {"tier": 3}


def score(a: Article, evidence_weight: int) -> float:
    tier_bonus = {1: 3, 2: 2, 3: 0.5}.get(a.tier, 0)
    abstract_bonus = min(len(a.abstract) / 1500, 1.0)
    return evidence_weight * 1.5 + tier_bonus + abstract_bonus


def process(articles: list[Article], journals: list[dict], *, include_exotics=False,
            require_abstract=True, max_total=18, max_per_discipline=4) -> tuple[list[Article], dict]:
    stats = {"collectés": len(articles), "sans résumé": 0, "hors espèce": 0,
             "type exclu": 0, "doublons": 0, "retenus": 0}
    seen, kept = set(), []
    for a in articles:
        if a.pmid in seen or (a.doi and a.doi in seen):
            stats["doublons"] += 1
            continue
        seen.update({a.pmid, a.doi} - {""})
        if EXCLUDED_PUBTYPES & set(a.pub_types):
            stats["type exclu"] += 1
            continue
        if require_abstract and len(a.abstract) < 200:
            stats["sans résumé"] += 1
            continue
        if not is_pet_relevant(a, include_exotics):
            stats["hors espèce"] += 1
            continue
        lab, w = evidence_level(a)
        if lab == "Cas clinique" and a.tier > 1:
            stats["type exclu"] += 1
            continue
        j = journal_info(a, journals)
        a.tier = j.get("tier", 3)
        a.journal = j.get("name", a.journal)
        a.species = [s for s in detect_species(a) if s in {"chien", "chat"} | (EXOTICS if include_exotics else set())]
        a.evidence = lab
        a.discipline = classify(a, j.get("hint"))
        a.score = score(a, w)
        kept.append(a)

    # Sélection : meilleurs scores, plafond par discipline, puis ordre des rubriques.
    kept.sort(key=lambda x: x.score, reverse=True)
    per = defaultdict(int)
    selected = []
    for a in kept:
        if len(selected) >= max_total:
            break
        if per[a.discipline] >= max_per_discipline:
            continue
        per[a.discipline] += 1
        selected.append(a)
    stats["éligibles"] = len(kept)
    stats["retenus"] = len(selected)
    return selected, stats
