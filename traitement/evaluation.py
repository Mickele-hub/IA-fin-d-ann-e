"""Évaluation de la classification sur des articles étiquetés à la main.

Deux commandes, à lancer depuis la racine du dépôt :

  1. Étiqueter un échantillon (le programme n'affiche PAS sa prédiction, pour
     ne pas influencer ton jugement ; la source est cachée pour la même raison) :
        python3 traitement/evaluation.py etiqueter data/articles_demo.json
     Options : --n 40 (taille de l'échantillon), --graine 42 (tirage reproductible).
     Tes réponses sont enregistrées au fur et à mesure dans
     traitement/evaluation_etiquettes.json : tu peux arrêter (q) et reprendre.

  2. Mesurer la précision de la classification :
        python3 traitement/evaluation.py mesurer data/articles_demo.json
     Affiche le taux de bonnes classifications, la précision et le rappel par
     domaine, la matrice de confusion et la liste des erreurs avec les mots-clés
     qui ont déclenché la décision (utile pour ajuster classification.py).
"""

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from classification import CATEGORIE_PAR_DEFAUT, DOMAINES, classifier_article, scores_article
from doublons import supprimer_doublons
from nettoyage import charger_articles, nettoyer_articles

FICHIER_ETIQUETTES = Path(__file__).resolve().parent / "evaluation_etiquettes.json"
CATEGORIES = [*DOMAINES, CATEGORIE_PAR_DEFAUT]
CODES = {str(i): nom for i, nom in enumerate(CATEGORIES, start=1)}


# --- fonctions pures (testées) --------------------------------------------

def preparer_articles(chemin):
    """Même chaîne que la production : nettoyage, doublons (sans classification)."""
    return supprimer_doublons(nettoyer_articles(charger_articles(chemin)))


def echantillonner(articles, n=40, graine=42):
    """Tire n articles répartis à égalité entre les sources, dans un ordre mélangé."""
    rng = random.Random(graine)
    par_source = defaultdict(list)
    for article in articles:
        par_source[article["source"]].append(article)
    sources = sorted(par_source)
    part = max(1, n // len(sources)) if sources else 0
    choisis = []
    for source in sources:
        choisis += rng.sample(par_source[source], min(part, len(par_source[source])))
    rng.shuffle(choisis)
    return choisis


def calculer_metriques(attendus, predits):
    """Précision globale, précision/rappel par catégorie et matrice de confusion."""
    total = len(attendus)
    justes = sum(a == p for a, p in zip(attendus, predits))
    matrice = {c: Counter() for c in CATEGORIES}
    for attendu, predit in zip(attendus, predits):
        matrice[attendu][predit] += 1

    par_categorie = {}
    for c in CATEGORIES:
        vrais_positifs = matrice[c][c]
        nb_predits = sum(matrice[autre][c] for autre in CATEGORIES)
        nb_attendus = sum(matrice[c].values())
        par_categorie[c] = {
            "precision": vrais_positifs / nb_predits if nb_predits else None,
            "rappel": vrais_positifs / nb_attendus if nb_attendus else None,
            "support": nb_attendus,
        }
    return {
        "total": total,
        "justes": justes,
        "exactitude": justes / total if total else None,
        "par_categorie": par_categorie,
        "matrice": matrice,
    }


def charger_etiquettes(chemin=FICHIER_ETIQUETTES):
    chemin = Path(chemin)
    if not chemin.exists():
        return []
    return json.loads(chemin.read_text(encoding="utf-8"))


def sauvegarder_etiquettes(etiquettes, chemin=FICHIER_ETIQUETTES):
    Path(chemin).write_text(
        json.dumps(etiquettes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def rapprocher(articles, etiquettes):
    """Associe chaque étiquette à son article (par lien). Retourne (paires, introuvables)."""
    par_lien = {a["lien"]: a for a in articles}
    paires, introuvables = [], []
    for etiquette in etiquettes:
        article = par_lien.get(etiquette["lien"])
        if article is None:
            introuvables.append(etiquette)
        else:
            paires.append((article, etiquette["domaine"]))
    return paires, introuvables


# --- affichage ------------------------------------------------------------

def pourcentage(valeur):
    return "   -  " if valeur is None else f"{100 * valeur:5.1f} %".replace(".", ",")


def afficher_rapport(paires):
    attendus = [domaine for _, domaine in paires]
    predits = [classifier_article(article) for article, _ in paires]
    m = calculer_metriques(attendus, predits)

    print(f"\nArticles évalués : {m['total']}")
    print(f"Bien classés     : {m['justes']} ({pourcentage(m['exactitude']).strip()})")

    print("\nPar domaine :")
    print(f"  {'':<26} {'précision':>10} {'rappel':>9} {'articles':>9}")
    for c in CATEGORIES:
        d = m["par_categorie"][c]
        print(f"  {c:<26} {pourcentage(d['precision']):>10} {pourcentage(d['rappel']):>9} {d['support']:>9}")

    print("\nMatrice de confusion (lignes = ta réponse, colonnes = programme) :")
    print("  " + " " * 26 + "".join(f"{i:>5}" for i in CODES))
    for c in CATEGORIES:
        ligne = "".join(f"{m['matrice'][c][autre]:>5}" for autre in CATEGORIES)
        print(f"  {c:<26}{ligne}")
    print("  (colonnes : " + ", ".join(f"{i}={nom}" for i, nom in CODES.items()) + ")")

    erreurs = [(a, att, pred) for (a, att), pred in zip(paires, predits) if att != pred]
    print(f"\nErreurs ({len(erreurs)}) :")
    for article, attendu, predit in erreurs:
        scores = scores_article(article)
        print(f"  - {article['titre'][:80]}")
        print(f"      attendu : {attendu}  |  prédit : {predit}")
        for nom in (predit, attendu):
            if nom in scores:
                s = scores[nom]
                print(f"      {nom} : score {s['score']}, mots {s['mots'][:6]}")


# --- commandes interactives -----------------------------------------------

def etiqueter(articles, n, graine):
    etiquettes = charger_etiquettes()
    deja = {e["lien"] for e in etiquettes}
    a_faire = [a for a in echantillonner(articles, n, graine) if a["lien"] not in deja]

    print("\nDomaines :  " + "   ".join(f"{i} = {nom}" for i, nom in CODES.items()))
    print("Réponses :  1-5 pour choisir, s pour passer, q pour quitter (progression sauvegardée).")
    print(f"{len(deja)} article(s) déjà étiqueté(s), {len(a_faire)} restant(s).\n")

    for position, article in enumerate(a_faire, start=1):
        print(f"--- Article {position}/{len(a_faire)} " + "-" * 40)
        print(f"Titre : {article['titre']}")
        extrait = article["description"][:400]
        print(f"Description : {extrait + ('…' if len(article['description']) > 400 else '') or '(vide)'}")
        while True:
            try:
                reponse = input("Domaine ? ").strip().lower()
            except EOFError:  # Ctrl+D : on quitte proprement
                reponse = "q"
            if reponse in CODES or reponse in ("s", "q"):
                break
            print("  Réponse non reconnue (1-5, s ou q).")
        if reponse == "q":
            break
        if reponse == "s":
            continue
        etiquettes.append({"lien": article["lien"], "titre": article["titre"], "domaine": CODES[reponse]})
        sauvegarder_etiquettes(etiquettes)
        print()
    print(f"\n{len(etiquettes)} article(s) étiquetés au total dans {FICHIER_ETIQUETTES.name}.")


def mesurer(articles):
    etiquettes = charger_etiquettes()
    if not etiquettes:
        sys.exit("Aucune étiquette : lance d'abord la commande « etiqueter ».")
    paires, introuvables = rapprocher(articles, etiquettes)
    if introuvables:
        print(f"Attention : {len(introuvables)} étiquette(s) sans article correspondant dans ce fichier (ignorées).")
    afficher_rapport(paires)


if __name__ == "__main__":
    import argparse

    analyseur = argparse.ArgumentParser(description="Évaluation de la classification.")
    analyseur.add_argument("commande", choices=["etiqueter", "mesurer"])
    analyseur.add_argument("fichier", type=Path, help="JSON des articles (ex. data/articles_demo.json)")
    analyseur.add_argument("--n", type=int, default=40, help="taille de l'échantillon à étiqueter")
    analyseur.add_argument("--graine", type=int, default=42, help="graine du tirage aléatoire")
    args = analyseur.parse_args()

    tous = preparer_articles(args.fichier)
    if args.commande == "etiqueter":
        etiqueter(tous, args.n, args.graine)
    else:
        mesurer(tous)
