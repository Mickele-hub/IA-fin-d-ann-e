"""Module de traitement et classification : point d'entrée.

Enchaîne, sur le JSON produit par n8n (personne 1) :
    nettoyage -> suppression des doublons -> classification -> préparation
et écrit un JSON prêt pour le module Ollama + SQLite (personne 3).

Usage, depuis la racine du dépôt :
    python3 traitement/main.py data/articles_demo.json
    python3 traitement/main.py data/articles.json --sortie data/articles_traites.json

Par défaut, la sortie est data/articles_traites.json.
"""

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from classification import classifier_articles
from doublons import supprimer_doublons
from nettoyage import charger_articles, nettoyer_articles
from preparation import preparer_articles

SORTIE_PAR_DEFAUT = Path(__file__).resolve().parents[1] / "data" / "articles_traites.json"


def traiter(articles_bruts):
    """Applique toute la chaîne. Retourne (articles prêts, statistiques)."""
    propres = nettoyer_articles(articles_bruts)
    uniques = supprimer_doublons(propres)
    classes = classifier_articles(uniques)
    prets = preparer_articles(classes)
    statistiques = {
        "entree": len(articles_bruts),
        "apres_nettoyage": len(propres),
        "apres_doublons": len(uniques),
        "sortie": len(prets),
        "par_categorie": dict(Counter(a["category"] for a in prets)),
    }
    return prets, statistiques


def ecrire_articles(articles, chemin):
    """Écrit la liste d'articles en JSON (UTF-8), en créant le dossier si besoin."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(articles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lancer(entree, sortie=SORTIE_PAR_DEFAUT):
    """Lit le fichier d'entrée, traite, écrit le fichier de sortie. Retourne les statistiques."""
    articles, statistiques = traiter(charger_articles(entree))
    ecrire_articles(articles, sortie)
    return statistiques


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    analyseur = argparse.ArgumentParser(description="Traitement et classification des articles.")
    analyseur.add_argument("entree", type=Path, help="JSON produit par n8n (ex. data/articles.json)")
    analyseur.add_argument("--sortie", type=Path, default=SORTIE_PAR_DEFAUT, help="JSON de sortie")
    args = analyseur.parse_args()

    try:
        stats = lancer(args.entree, args.sortie)
    except (OSError, ValueError) as erreur:  # fichier absent, JSON invalide, mauvais format
        sys.exit(f"Erreur : {erreur}")

    print(f"{stats['entree']} articles lus -> {stats['apres_nettoyage']} après nettoyage "
          f"-> {stats['apres_doublons']} après doublons -> {stats['sortie']} écrits dans {args.sortie}")
    for categorie, nombre in sorted(stats["par_categorie"].items(), key=lambda kv: -kv[1]):
        print(f"  {categorie:<26} {nombre:>4}")
