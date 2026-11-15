"""Nettoyage des articles collectés par n8n (module de traitement, étape 1).

Entrée : liste d'objets JSON avec les champs titre, description, date, lien, source.
Sortie : la même liste, nettoyée, sans les articles invalides.

Usage rapide, depuis la racine du dépôt :
    python3 traitement/nettoyage.py data/articles_demo.json
"""

import html
import json
import logging
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

logger = logging.getLogger(__name__)

# n8n coupe les descriptions à 1000 caractères : au-delà de ce seuil sans
# ponctuation finale, on considère que la description a été tronquée.
SEUIL_TRONQUE = 990
LONGUEUR_MAX = 1000
# On ne recoupe à la dernière phrase que si on garde au moins cette part du texte.
PART_MIN_CONSERVEE = 0.4

PARAMS_TRACKING = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src"}
FIN_DE_PHRASE = (".", "!", "?", "…", '"', "'", ")", "»")
RE_BALISE = re.compile(r"<\s*/?\s*[a-zA-Z!]")
RE_FIN_PHRASE = re.compile(r"[.!?](?=\s|$)")
RE_CONTROLES = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Les flux arXiv commencent chaque description par « arXiv:2611.12933v1
# Announce Type: new Abstract: » : du bruit pour la classification et le résumé.
RE_PREFIXE_ARXIV = re.compile(r"^arXiv:\S+\s+Announce Type:\s*\S+\s+Abstract:\s*", re.IGNORECASE)


def nettoyer_texte(texte):
    """Retire le HTML, décode les entités, normalise l'Unicode et les espaces."""
    if not isinstance(texte, str):
        return ""
    texte = html.unescape(texte)
    if RE_BALISE.search(texte):
        texte = BeautifulSoup(texte, "html.parser").get_text(" ")
    texte = unicodedata.normalize("NFKC", texte)
    texte = RE_CONTROLES.sub(" ", texte)
    return re.sub(r"\s+", " ", texte).strip()


def normaliser_lien(lien):
    """Retourne le lien sans paramètres de tracking ni ancre, ou None s'il est invalide."""
    if not isinstance(lien, str):
        return None
    lien = lien.strip()
    parties = urlsplit(lien)
    if parties.scheme.lower() not in ("http", "https") or not parties.netloc:
        return None
    requete = [
        (cle, valeur)
        for cle, valeur in parse_qsl(parties.query, keep_blank_values=True)
        if not cle.lower().startswith("utm_") and cle.lower() not in PARAMS_TRACKING
    ]
    return urlunsplit(
        (parties.scheme, parties.netloc, parties.path, urlencode(requete), "")
    )


def normaliser_date(valeur, maintenant=None):
    """Retourne la date en ISO 8601 UTC (ex. 2026-11-14T08:00:00Z).

    Si la date est absente ou illisible, on utilise la date du traitement
    plutôt que de perdre l'article.
    """
    maintenant = maintenant or datetime.now(timezone.utc)
    try:
        date = dateparser.parse(str(valeur))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        date = date.astimezone(timezone.utc)
    except (ValueError, OverflowError, TypeError):
        logger.warning("Date illisible (%r) : date du traitement utilisée", valeur)
        date = maintenant
    return date.strftime("%Y-%m-%dT%H:%M:%SZ")


def reparer_description(description):
    """Recoupe proprement une description tronquée par n8n (max. LONGUEUR_MAX caractères)."""
    if len(description) < SEUIL_TRONQUE or description.endswith(FIN_DE_PHRASE):
        return description

    fins = [m.end() for m in RE_FIN_PHRASE.finditer(description)]
    if fins and fins[-1] >= len(description) * PART_MIN_CONSERVEE:
        return description[: fins[-1]].strip()

    # On réserve la place des trois points pour ne jamais dépasser LONGUEUR_MAX.
    # Attention : on utilise "..." et non "…", car la normalisation NFKC
    # transformerait "…" en "..." à la passe suivante (résultat non stable).
    coupe = description[: LONGUEUR_MAX - 3]
    dernier_mot = coupe.rfind(" ")
    if dernier_mot > 0:
        coupe = coupe[:dernier_mot]
    return coupe.rstrip(" ,;:-") + "..."


def retirer_prefixe_arxiv(description):
    """Retire l'en-tête automatique « arXiv:... Announce Type: ... Abstract: »."""
    return RE_PREFIXE_ARXIV.sub("", description, count=1)


def nettoyer_article(brut, maintenant=None):
    """Nettoie un article. Retourne None si l'article est invalide."""
    if not isinstance(brut, dict):
        return None

    titre = nettoyer_texte(brut.get("titre"))
    lien = normaliser_lien(brut.get("lien"))
    if not titre or not lien:
        return None

    # On répare la troncature avant de retirer l'en-tête arXiv : le seuil de
    # détection se mesure sur le texte tel que n8n l'a coupé.
    description = reparer_description(nettoyer_texte(brut.get("description")))
    return {
        "titre": titre,
        "description": retirer_prefixe_arxiv(description),
        "date": normaliser_date(brut.get("date"), maintenant),
        "lien": lien,
        "source": nettoyer_texte(brut.get("source")) or "Inconnue",
    }


def nettoyer_articles(articles):
    """Nettoie une liste d'articles et écarte les invalides."""
    maintenant = datetime.now(timezone.utc)
    propres = []
    for brut in articles:
        article = nettoyer_article(brut, maintenant)
        if article is None:
            logger.warning("Article rejeté (titre ou lien invalide) : %.80r", brut)
            continue
        propres.append(article)
    logger.info("%d articles en entrée, %d conservés", len(articles), len(propres))
    return propres


def charger_articles(chemin):
    """Charge le JSON produit par n8n (une liste d'articles)."""
    with open(chemin, encoding="utf-8") as fichier:
        donnees = json.load(fichier)
    if isinstance(donnees, dict) and isinstance(donnees.get("articles"), list):
        donnees = donnees["articles"]
    if not isinstance(donnees, list):
        raise ValueError(f"{chemin} doit contenir une liste d'articles")
    return donnees


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if len(sys.argv) != 2:
        sys.exit("Usage : python3 traitement/nettoyage.py chemin/vers/articles.json")
    entree = charger_articles(Path(sys.argv[1]))
    sortie = nettoyer_articles(entree)
    vides = sum(1 for a in sortie if not a["description"])
    print(f"{len(entree)} en entrée -> {len(sortie)} conservés, {vides} descriptions vides")
