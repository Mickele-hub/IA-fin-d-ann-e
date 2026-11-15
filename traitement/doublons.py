"""Suppression des doublons dans un lot d'articles déjà nettoyés (étape 5).

Trois niveaux, du plus sûr au plus souple :
  1. même lien (après normalisation : sans http/https, sans www., sans « / » final) ;
  2. même titre (sans accents, majuscules ni ponctuation) ;
  3. titres très proches (similarité >= SEUIL_SIMILARITE et l'un contient tous
     les mots de l'autre). Choix prudent : mieux vaut laisser passer un
     doublon que fusionner deux articles différents.

Quand deux articles sont doublons, on garde le plus complet (description la
plus longue) et, à égalité, le plus ancien.

Ce module ne voit qu'un lot à la fois. Les doublons entre deux jours sont
gérés par la base SQLite (colonne link UNIQUE + INSERT OR IGNORE).

Usage rapide, depuis la racine du dépôt :
    python3 traitement/doublons.py data/articles_demo.json
"""

import logging
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

logger = logging.getLogger(__name__)

SEUIL_SIMILARITE = 0.85
# En dessous de cette longueur, un titre n'est comparé qu'en égalité stricte :
# des titres très courts se ressemblent trop facilement par hasard.
LONGUEUR_MIN_SIMILARITE = 20


def cle_lien(lien):
    """Clé de comparaison d'un lien (ignore http/https, www., « / » final, ancre)."""
    parties = urlsplit(str(lien).strip())
    hote = parties.netloc.lower()
    if hote.startswith("www."):
        hote = hote[4:]
    chemin = parties.path.rstrip("/")
    requete = urlencode(sorted(parse_qsl(parties.query, keep_blank_values=True)))
    return f"{hote}{chemin}?{requete}" if requete else f"{hote}{chemin}"


def cle_titre(titre):
    """Titre en minuscules, sans accents ni ponctuation, espaces réduits."""
    texte = unicodedata.normalize("NFD", str(titre).lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = re.sub(r"[^\w\s]", " ", texte)
    return re.sub(r"\s+", " ", texte).strip()


def titres_proches(titre_a, titre_b, seuil=SEUIL_SIMILARITE):
    """True si les deux titres (déjà normalisés) sont très ressemblants.

    Deux conditions : similarité >= seuil ET tous les mots du titre le plus
    court se retrouvent dans l'autre (même titre avec un suffixe, un article
    en plus, etc.). La seconde condition évite de fusionner deux articles
    différents qui ne changent que d'un mot, par exemple « Learning to rank
    with graph networks » et « Learning to cluster with graph networks ».
    """
    if min(len(titre_a), len(titre_b)) < LONGUEUR_MIN_SIMILARITE:
        return False
    mots_a, mots_b = set(titre_a.split()), set(titre_b.split())
    if not (mots_a <= mots_b or mots_b <= mots_a):
        return False
    comparateur = SequenceMatcher(None, titre_a, titre_b)
    # Les deux premiers calculs sont des majorants rapides : ils évitent le
    # calcul complet quand les titres sont manifestement différents.
    return (
        comparateur.real_quick_ratio() >= seuil
        and comparateur.quick_ratio() >= seuil
        and comparateur.ratio() >= seuil
    )


def meilleur_article(a, b):
    """Garde le plus complet ; à égalité, le plus ancien ; sinon le premier."""
    longueur_a, longueur_b = len(a.get("description", "")), len(b.get("description", ""))
    if longueur_a != longueur_b:
        return a if longueur_a > longueur_b else b
    date_a, date_b = a.get("date", ""), b.get("date", "")
    if date_a != date_b:
        return a if date_a < date_b else b
    return a


def supprimer_doublons(articles):
    """Retourne la liste sans doublons, dans l'ordre d'apparition."""
    gardes = []          # article retenu pour chaque emplacement
    titres = []          # clé de titre de l'article retenu, par emplacement
    par_lien = {}        # clé de lien -> emplacement
    par_titre = {}       # clé de titre -> emplacement

    for article in articles:
        k_lien = cle_lien(article["lien"])
        k_titre = cle_titre(article["titre"])

        emplacement = par_lien.get(k_lien)
        if emplacement is None:
            emplacement = par_titre.get(k_titre)
        if emplacement is None:
            for i, titre_garde in enumerate(titres):
                if titres_proches(k_titre, titre_garde):
                    emplacement = i
                    break

        if emplacement is None:
            emplacement = len(gardes)
            gardes.append(article)
            titres.append(k_titre)
        else:
            logger.info("Doublon : %.60r ~ %.60r", article["titre"], gardes[emplacement]["titre"])
            retenu = meilleur_article(gardes[emplacement], article)
            gardes[emplacement] = retenu
            titres[emplacement] = cle_titre(retenu["titre"])

        par_lien[k_lien] = emplacement
        par_titre[k_titre] = emplacement

    logger.info("%d articles en entrée, %d après suppression des doublons", len(articles), len(gardes))
    return gardes


if __name__ == "__main__":
    from nettoyage import charger_articles, nettoyer_articles

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if len(sys.argv) != 2:
        sys.exit("Usage : python3 traitement/doublons.py chemin/vers/articles.json")
    propres = nettoyer_articles(charger_articles(Path(sys.argv[1])))
    uniques = supprimer_doublons(propres)
    print(f"{len(propres)} articles propres -> {len(uniques)} sans doublons")
