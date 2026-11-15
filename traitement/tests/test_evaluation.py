"""Tests du module evaluation.py (les fonctions pures, pas l'étiquetage interactif).

Lancer depuis la racine du dépôt :
    pytest traitement/tests -v
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from classification import classifier_article  # noqa: E402
from evaluation import (  # noqa: E402
    CATEGORIES,
    CODES,
    calculer_metriques,
    charger_etiquettes,
    echantillonner,
    preparer_articles,
    rapprocher,
    sauvegarder_etiquettes,
)

DEMO = Path(__file__).resolve().parents[2] / "data" / "articles_demo.json"
CYBER, IA, CLOUD, DEV, AUTRES = CATEGORIES


def faux_articles():
    return [
        {"titre": f"Article {i}", "lien": f"https://exemple.com/{s}/{i}", "source": s}
        for s in ("A", "B", "C") for i in range(10)
    ]


# --- codes ----------------------------------------------------------------

def test_codes_numerotes_de_1_a_5_dans_lordre_des_domaines():
    assert list(CODES) == ["1", "2", "3", "4", "5"]
    assert CODES["1"] == CYBER and CODES["5"] == AUTRES


# --- échantillon ----------------------------------------------------------

def test_echantillon_reparti_a_egalite_entre_les_sources():
    echantillon = echantillonner(faux_articles(), n=9, graine=1)
    assert Counter(a["source"] for a in echantillon) == {"A": 3, "B": 3, "C": 3}


def test_echantillon_reproductible_avec_la_meme_graine():
    assert echantillonner(faux_articles(), 9, 7) == echantillonner(faux_articles(), 9, 7)


def test_echantillon_change_avec_une_autre_graine():
    assert echantillonner(faux_articles(), 9, 1) != echantillonner(faux_articles(), 9, 2)


def test_echantillon_sans_doublon_et_borne_par_la_taille_des_sources():
    echantillon = echantillonner(faux_articles()[:12], n=30, graine=3)
    liens = [a["lien"] for a in echantillon]
    assert len(liens) == len(set(liens))
    assert len(echantillon) <= 12


def test_echantillon_liste_vide():
    assert echantillonner([], 40, 42) == []


# --- métriques ------------------------------------------------------------

def test_metriques_tout_juste():
    attendus = [CYBER, IA, CLOUD, AUTRES]
    m = calculer_metriques(attendus, list(attendus))
    assert m["exactitude"] == 1.0 and m["justes"] == 4
    assert m["par_categorie"][CYBER]["precision"] == 1.0


def test_metriques_cas_connu():
    attendus = [IA, IA, IA, CYBER, CYBER]
    predits = [IA, IA, CYBER, CYBER, AUTRES]
    m = calculer_metriques(attendus, predits)
    assert m["exactitude"] == 3 / 5
    assert m["par_categorie"][IA]["precision"] == 1.0
    assert m["par_categorie"][IA]["rappel"] == 2 / 3
    assert m["par_categorie"][CYBER]["precision"] == 1 / 2
    assert m["par_categorie"][CYBER]["rappel"] == 1 / 2
    assert m["matrice"][IA][CYBER] == 1 and m["matrice"][CYBER][AUTRES] == 1


def test_metriques_categorie_absente_donne_none():
    m = calculer_metriques([IA], [IA])
    assert m["par_categorie"][CLOUD]["precision"] is None
    assert m["par_categorie"][CLOUD]["rappel"] is None
    assert m["par_categorie"][CLOUD]["support"] == 0


def test_metriques_liste_vide():
    assert calculer_metriques([], [])["exactitude"] is None


# --- étiquettes -----------------------------------------------------------

def test_etiquettes_sauvegardees_puis_rechargees(tmp_path):
    fichier = tmp_path / "etiquettes.json"
    etiquettes = [{"lien": "https://exemple.com/a", "titre": "Été", "domaine": CYBER}]
    sauvegarder_etiquettes(etiquettes, fichier)
    assert charger_etiquettes(fichier) == etiquettes


def test_fichier_etiquettes_absent_donne_liste_vide(tmp_path):
    assert charger_etiquettes(tmp_path / "inexistant.json") == []


def test_rapprocher_par_lien_et_signale_les_introuvables():
    articles = [{"titre": "A", "lien": "https://exemple.com/a"}]
    etiquettes = [
        {"lien": "https://exemple.com/a", "domaine": IA},
        {"lien": "https://exemple.com/zzz", "domaine": IA},
    ]
    paires, introuvables = rapprocher(articles, etiquettes)
    assert paires == [(articles[0], IA)]
    assert len(introuvables) == 1


# --- données réelles ------------------------------------------------------

def test_demo_echantillon_de_40_articles_distincts():
    echantillon = echantillonner(preparer_articles(DEMO), n=40, graine=42)
    assert len(echantillon) == 40
    assert len({a["lien"] for a in echantillon}) == 40


def test_demo_etiquettes_identiques_aux_predictions_donnent_100_pourcent():
    echantillon = echantillonner(preparer_articles(DEMO), n=40, graine=42)
    attendus = [classifier_article(a) for a in echantillon]
    assert calculer_metriques(attendus, attendus)["exactitude"] == 1.0
