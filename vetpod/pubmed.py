"""Collecte des études via l'API officielle NCBI E-utilities (PubMed)."""
from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict

import requests

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Types de publication non retenus : ce ne sont pas des études originales/revues.
EXCLUDED_PUBTYPES = {
    "Comment", "Editorial", "Letter", "News", "Erratum", "Published Erratum",
    "Retracted Publication", "Retraction of Publication", "Expression of Concern",
    "Biography", "Portrait", "Congress", "Interview", "Corrected and Republished Article",
}

SPECIES_PETS = '("Dogs"[MeSH] OR "Cats"[MeSH] OR dog[tiab] OR dogs[tiab] OR canine[tiab] ' \
               'OR cat[tiab] OR cats[tiab] OR feline[tiab] OR puppies[tiab] OR kittens[tiab])'
SPECIES_EXOTICS = '("Rabbits"[MeSH] OR rabbit*[tiab] OR ferret*[tiab] OR "guinea pig*"[tiab] ' \
                  'OR chinchilla*[tiab] OR hamster*[tiab] OR "pet bird*"[tiab] OR parrot*[tiab] ' \
                  'OR "companion animal*"[tiab] OR "exotic pet*"[tiab])'


@dataclass
class Article:
    pmid: str
    title: str
    abstract: str
    journal: str
    journal_abbrev: str
    pub_date: str
    authors: list[str] = field(default_factory=list)
    doi: str = ""
    pub_types: list[str] = field(default_factory=list)
    mesh: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    # rempli plus tard
    tier: int = 3
    discipline: str = ""
    species: list[str] = field(default_factory=list)
    evidence: str = ""
    score: float = 0.0
    summary: dict = field(default_factory=dict)

    @property
    def url(self) -> str:
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"

    @property
    def doi_url(self) -> str:
        return f"https://doi.org/{self.doi}" if self.doi else self.url

    @property
    def first_author(self) -> str:
        if not self.authors:
            return ""
        return self.authors[0] + (" et al." if len(self.authors) > 1 else "")

    def to_dict(self) -> dict:
        return asdict(self)


def build_query(journals: list[dict], include_exotics: bool) -> str:
    jq = " OR ".join(f'"{j["pubmed"]}"[Journal]' for j in journals)
    species = SPECIES_PETS if not include_exotics else f"({SPECIES_PETS} OR {SPECIES_EXOTICS})"
    excl = " OR ".join(f'"{p}"[Publication Type]' for p in sorted(EXCLUDED_PUBTYPES))
    return f"({jq}) AND {species} AND english[Language] NOT ({excl})"


class PubMedClient:
    def __init__(self, api_key: str = "", email: str = "", tool: str = "vetpod"):
        self.api_key = api_key or os.getenv("NCBI_API_KEY", "")
        self.email = email or os.getenv("NCBI_EMAIL", "")
        self.tool = tool
        self.delay = 0.11 if self.api_key else 0.35
        self.session = requests.Session()

    def _params(self, **kw) -> dict:
        p = {"db": "pubmed", "tool": self.tool, **kw}
        if self.api_key:
            p["api_key"] = self.api_key
        if self.email:
            p["email"] = self.email
        return p

    def _get(self, endpoint: str, **kw) -> requests.Response:
        for attempt in range(4):
            time.sleep(self.delay)
            r = self.session.get(f"{EUTILS}/{endpoint}", params=self._params(**kw), timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r
        r.raise_for_status()
        return r

    def search(self, query: str, days_back: int, retmax: int = 1000) -> list[str]:
        """PMID des articles entrés dans PubMed pendant les `days_back` derniers jours."""
        r = self._get("esearch.fcgi", term=query, datetype="edat", reldate=days_back,
                      retmax=retmax, retmode="json")
        return r.json()["esearchresult"].get("idlist", [])

    def fetch(self, pmids: list[str]) -> list[Article]:
        out: list[Article] = []
        for i in range(0, len(pmids), 200):
            r = self._get("efetch.fcgi", id=",".join(pmids[i:i + 200]), retmode="xml")
            out.extend(parse_pubmed_xml(r.text))
        return out


def _text(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def parse_pubmed_xml(xml: str) -> list[Article]:
    root = ET.fromstring(xml)
    arts = []
    for pa in root.iter("PubmedArticle"):
        mc = pa.find("MedlineCitation")
        art = mc.find("Article")
        abstract_parts = []
        for at in art.findall("Abstract/AbstractText"):
            lab = at.get("Label")
            t = _text(at)
            abstract_parts.append(f"{lab}: {t}" if lab else t)
        authors = []
        for au in art.findall("AuthorList/Author"):
            last, ini = _text(au.find("LastName")), _text(au.find("Initials"))
            coll = _text(au.find("CollectiveName"))
            if last:
                authors.append(f"{last} {ini}".strip())
            elif coll:
                authors.append(coll)
        doi = ""
        for aid in pa.findall("PubmedData/ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = _text(aid)
        if not doi:
            for eid in art.findall("ELocationID"):
                if eid.get("EIdType") == "doi":
                    doi = _text(eid)
        pd = art.find("Journal/JournalIssue/PubDate")
        date = " ".join(x for x in [_text(pd.find("Year")), _text(pd.find("Month")),
                                    _text(pd.find("Day"))] if x) if pd is not None else ""
        if not date and pd is not None:
            date = _text(pd.find("MedlineDate"))
        arts.append(Article(
            pmid=_text(mc.find("PMID")),
            title=_text(art.find("ArticleTitle")),
            abstract="\n".join(abstract_parts),
            journal=_text(art.find("Journal/Title")),
            journal_abbrev=_text(mc.find("MedlineJournalInfo/MedlineTA")) or _text(art.find("Journal/ISOAbbreviation")),
            pub_date=date,
            authors=authors,
            doi=doi,
            pub_types=[_text(p) for p in art.findall("PublicationTypeList/PublicationType")],
            mesh=[_text(m.find("DescriptorName")) for m in mc.findall("MeshHeadingList/MeshHeading")],
            keywords=[_text(k) for k in mc.findall("KeywordList/Keyword")],
        ))
    return arts
