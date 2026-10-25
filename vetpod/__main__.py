"""VetPod — génère l'épisode hebdomadaire.

Exemples :
  python -m vetpod run                 # collecte + rédaction + audio + flux RSS
  python -m vetpod run --no-audio      # script et notes seulement
  python -m vetpod run --days 14       # fenêtre de 14 jours
  python -m vetpod query               # affiche la requête PubMed utilisée
  python -m vetpod run --from-xml tests/fixtures/sample.xml   # test hors ligne
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import markdown
import yaml

from . import audio, publish
from .pubmed import PubMedClient, build_query, parse_pubmed_xml
from .selection import process
from .writer import Writer

ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vetpod")
    ap.add_argument("command", choices=["run", "query"])
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--sources", default=str(ROOT / "sources.yaml"))
    ap.add_argument("--days", type=int)
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--from-xml", help="fichier XML PubMed local (test hors ligne)")
    args = ap.parse_args(argv)

    cfg = load(Path(args.config))
    journals = load(Path(args.sources))["journals"]
    s = cfg["search"]
    days = args.days or s.get("days_back", 7)
    query = build_query(journals, s.get("include_exotics", False))
    if args.command == "query":
        print(query)
        return

    pub = ROOT / cfg["output"]["public_dir"]
    work = ROOT / cfg["output"]["work_dir"]
    pub.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    # 1. Collecte
    if args.from_xml:
        articles = parse_pubmed_xml(Path(args.from_xml).read_text(encoding="utf-8"))
        print(f"[1/5] {len(articles)} articles lus depuis {args.from_xml}")
    else:
        client = PubMedClient(s.get("ncbi_api_key", ""), s.get("ncbi_email", ""))
        pmids = client.search(query, days)
        print(f"[1/5] PubMed : {len(pmids)} articles sur {days} jours")
        articles = client.fetch(pmids) if pmids else []

    # 2. Filtrage, niveau de preuve, classement
    selected, stats = process(articles, journals, include_exotics=s.get("include_exotics", False),
                              require_abstract=s.get("require_abstract", True),
                              max_total=s.get("max_articles_total", 18),
                              max_per_discipline=s.get("max_per_discipline", 4))
    print(f"[2/5] Sélection : {stats}")
    if not selected:
        print("Aucune étude éligible cette semaine — pas d'épisode généré.")
        return

    # 3. Rédaction
    llm_cfg = dict(cfg["llm"])
    if args.no_llm:
        llm_cfg["enabled"] = False
    w = Writer(llm_cfg)
    print(f"[3/5] Rédaction ({'Claude ' + w.model if w.enabled else 'mode sans IA'})")
    for a in selected:
        a.summary = w.summarize(a)

    today = date.today()
    start = today - timedelta(days=days)
    iso = today.isocalendar()
    db = pub / "episodes.json"
    existing = json.loads(db.read_text()) if db.exists() else []
    ep_id = f"vetpod-{iso.year}-S{iso.week:02d}"
    number = next((e["number"] for e in existing if e["id"] == ep_id), len(existing) + 1)
    week = f"{start:%d/%m} au {today:%d/%m/%Y}"
    meta = {"id": ep_id, "number": number, "week": week,
            "title": f"Épisode {number} — Veille vétérinaire du {week}"}

    segments = w.script(selected, number, week, llm_cfg.get("target_minutes", 20))
    hosts = w.hosts
    script_txt = "\n\n".join(f"{hosts[sg['speaker'] % len(hosts)].upper()} : {sg['text']}" for sg in segments)
    (work / f"{ep_id}-script.txt").write_text(script_txt, encoding="utf-8")
    (work / f"{ep_id}-articles.json").write_text(
        json.dumps([a.to_dict() for a in selected], ensure_ascii=False, indent=1), encoding="utf-8")
    md = publish.show_notes_md(meta, selected, stats)
    (work / f"{ep_id}-notes.md").write_text(md, encoding="utf-8")
    publish.notes_page(pub, meta, markdown.markdown(md))
    print(f"[4/5] Script : {len(segments)} segments, {len(script_txt.split())} mots")

    # 4. Audio
    mp3, dur = None, 0
    if not args.no_audio and cfg["tts"].get("engine") == "edge":
        mp3 = audio.synthesize(segments, cfg["tts"]["voices"], cfg["tts"].get("rate", "+0%"),
                               pub / f"{ep_id}.mp3", work)
        dur = audio.duration_seconds(mp3)
        print(f"      Audio : {mp3.name} ({dur // 60} min {dur % 60} s)")

    # 5. Publication
    publish.update_feed(pub, cfg["podcast"], meta, selected, mp3, dur)
    print(f"[5/5] Publié dans {pub}/ (feed.xml, index.html, {ep_id}.html)")


if __name__ == "__main__":
    sys.exit(main())
