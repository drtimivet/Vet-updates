"""Notes d'épisode (HTML + Markdown), page d'accueil et flux RSS podcast (compatible Apple/Spotify)."""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from .disciplines import label
from .writer import group_by_discipline

E = html.escape


def show_notes_md(meta: dict, articles, stats: dict) -> str:
    out = [f"# {meta['title']}", "", f"*Période du {meta['week']} — {len(articles)} études*", ""]
    for d, arts in group_by_discipline(articles).items():
        out += [f"## {label(d)}", ""]
        for a in arts:
            s = a.summary
            out += [f"### {s.get('titre_fr') or a.title}",
                    f"*{a.title}*  ",
                    f"{a.first_author} — **{a.journal}**, {a.pub_date} · {a.evidence} · "
                    f"{', '.join(a.species)}  ",
                    f"[PubMed {a.pmid}]({a.url})" + (f" · [DOI {a.doi}]({a.doi_url})" if a.doi else ""), ""]
            if s.get("resultats"):
                out += [f"- {r}" for r in s["resultats"]] + [""]
            if s.get("message_clinique"):
                out += [f"**À retenir :** {s['message_clinique']}", ""]
            if s.get("limites"):
                out += [f"**Limites :** {s['limites']}", ""]
    out += ["---", "Méthode : recherche PubMed (NCBI E-utilities) sur les revues vétérinaires à comité de lecture "
            "listées dans sources.yaml, chiens et chats uniquement, articles entrés dans PubMed durant les 7 "
            "derniers jours. Synthèses fondées sur les résumés publiés.",
            "Filtrage : " + ", ".join(f"{k} {v}" for k, v in stats.items())]
    return "\n".join(out)


def show_notes_html(meta: dict, articles) -> str:
    parts = [f"<p>Période du {E(meta['week'])} — {len(articles)} études issues de revues à comité de lecture.</p>"]
    for d, arts in group_by_discipline(articles).items():
        parts.append(f"<h3>{E(label(d))}</h3><ul>")
        for a in arts:
            s = a.summary
            parts.append(
                f"<li><b>{E(s.get('titre_fr') or a.title)}</b> — {E(a.first_author)}, <i>{E(a.journal)}</i> "
                f"({E(a.evidence)}). {E(s.get('message_clinique', ''))} "
                f"<a href=\"{E(a.doi_url)}\">Article</a></li>")
        parts.append("</ul>")
    return "".join(parts)


def update_feed(pub: Path, pod: dict, meta: dict, articles, mp3: Path | None, duration: int):
    """Ajoute l'épisode à episodes.json puis régénère feed.xml et index.html."""
    db_path = pub / "episodes.json"
    episodes = json.loads(db_path.read_text()) if db_path.exists() else []
    episodes = [e for e in episodes if e["id"] != meta["id"]]
    episodes.append({
        "id": meta["id"], "number": meta["number"], "title": meta["title"], "week": meta["week"],
        "date": format_datetime(datetime.now(timezone.utc)),
        "audio": mp3.name if mp3 else None, "size": mp3.stat().st_size if mp3 else 0,
        "duration": duration, "notes_html": show_notes_html(meta, articles),
        "notes_page": f"{meta['id']}.html",
    })
    episodes.sort(key=lambda e: e["number"], reverse=True)
    db_path.write_text(json.dumps(episodes, ensure_ascii=False, indent=1))

    base = pod["base_url"].rstrip("/")
    items = []
    for e in episodes:
        if not e["audio"]:
            continue
        items.append(f"""  <item>
    <title>{E(e['title'])}</title>
    <guid isPermaLink="false">{E(e['id'])}</guid>
    <pubDate>{e['date']}</pubDate>
    <link>{base}/{e['notes_page']}</link>
    <enclosure url="{base}/{e['audio']}" length="{e['size']}" type="audio/mpeg"/>
    <itunes:duration>{e['duration']}</itunes:duration>
    <itunes:episode>{e['number']}</itunes:episode>
    <itunes:explicit>false</itunes:explicit>
    <description><![CDATA[{e['notes_html']}]]></description>
  </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{E(pod['title'])}</title>
  <link>{base}/</link>
  <atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>
  <language>{pod.get('language', 'fr')}</language>
  <description>{E(pod['description'].strip())}</description>
  <itunes:author>{E(pod['author'])}</itunes:author>
  <itunes:owner><itunes:name>{E(pod['author'])}</itunes:name><itunes:email>{E(pod.get('email', ''))}</itunes:email></itunes:owner>
  <itunes:image href="{base}/{pod.get('cover_image', 'cover.jpg')}"/>
  <itunes:category text="Science"><itunes:category text="Life Sciences"/></itunes:category>
  <itunes:category text="Health &amp; Fitness"><itunes:category text="Medicine"/></itunes:category>
  <itunes:explicit>false</itunes:explicit>
{chr(10).join(items)}
</channel>
</rss>
"""
    (pub / "feed.xml").write_text(feed)

    rows = "".join(
        f"<article><h2>{E(e['title'])}</h2>"
        + (f"<audio controls preload=\"none\" src=\"{E(e['audio'])}\"></audio>" if e["audio"] else "")
        + f"<p><a href=\"{E(e['notes_page'])}\">Notes et références</a></p>{e['notes_html']}</article>"
        for e in episodes)
    (pub / "index.html").write_text(PAGE.format(title=E(pod["title"]), desc=E(pod["description"].strip()),
                                                body=rows))


def notes_page(pub: Path, meta: dict, md_html: str):
    (pub / f"{meta['id']}.html").write_text(PAGE.format(title=E(meta["title"]), desc="", body=md_html))


PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<link rel="alternate" type="application/rss+xml" href="feed.xml">
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:760px;margin:auto;padding:16px;color:#1d2a2a;background:#fbfaf7}}
h1{{font-size:1.6em}}h2{{margin-top:2em;border-top:1px solid #ddd;padding-top:1em}}h3{{color:#21615a}}
audio{{width:100%}}a{{color:#21615a}}@media(prefers-color-scheme:dark){{body{{background:#151a1a;color:#e6ece9}}h3,a{{color:#7fc8bd}}}}</style>
</head><body><h1>{title}</h1><p>{desc}</p><p><a href="feed.xml">Flux RSS du podcast</a></p>{body}</body></html>"""
