"""Tests du module main.py (chaîne complète de traitement).

Lancer depuis la racine du dépôt :
    pytest traitement/tests -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from classification import DOMAINES  # noqa: E402
from main import ecrire_articles, lancer, traiter  # noqa: E402
from nettoyage import charger_articles  # noqa: E402
from preparation import CHAMPS_SORTIE  # noqa: E402

DEMO = Path(__file__).resolve().parents[2] / "data" / "articles_demo.json"
CATEGORIES_VALIDES = set(DOMAINES) | {"Autres"}


def brut(titre, lien, description="", date="2026-11-14T08:00:00Z", source="Blog"):
    return {"titre": titre, "description": description, "date": date, "lien": lien, "source": source}


def lot_sale():
    return [
        brut("<b>Critical vulnerability exploited</b>", "https://exemple.com/a?utm_source=x",
             "<p>Un malware &amp; un exploit.</p>"),
        brut("Critical vulnerability exploited", "http://www.exemple.com/a/", "Version plus complète du texte."),
        brut("", "https://exemple.com/sans-titre"),
        brut("Sans lien valide", "pas-un-lien"),
        brut("New language model beats every benchmark", "https://exemple.com/b", "Un LLM très performant."),
    ]


# --- traiter --------------------------------------------------------------

def test_traiter_statistiques_et_resultat():
    articles, stats = traiter(lot_sale())
    assert stats["entree"] == 5
    assert stats["apres_nettoyage"] == 3      # 2 invalides écartés
    assert stats["apres_doublons"] == 2       # les deux premiers fusionnés
    assert stats["sortie"] == 2 == len(articles)
    assert stats["par_categorie"] == {"Cybersécurité": 1, "Intelligence artificielle": 1}


def test_traiter_garde_la_version_la_plus_complete_et_nettoie():
    articles, _ = traiter(lot_sale())
    cyber = next(a for a in articles if a["category"] == "Cybersécurité")
    assert cyber["description"] == "Version plus complète du texte."
    assert cyber["title"] == "Critical vulnerability exploited"
    assert "utm_" not in cyber["link"]


def test_traiter_liste_vide():
    articles, stats = traiter([])
    assert articles == [] and stats["sortie"] == 0 and stats["par_categorie"] == {}


def test_traiter_entree_non_modifiee():
    entree = lot_sale()
    copie = json.loads(json.dumps(entree))
    traiter(entree)
    assert entree == copie


# --- données réelles ------------------------------------------------------

def test_demo_chaine_complete():
    entree = charger_articles(DEMO)
    articles, stats = traiter(entree)
    assert stats["entree"] == len(entree) == stats["sortie"]
    assert sum(stats["par_categorie"].values()) == len(articles)
    for a in articles:
        assert tuple(a) == CHAMPS_SORTIE
        assert a["category"] in CATEGORIES_VALIDES


def test_demo_traitement_deterministe():
    assert traiter(charger_articles(DEMO)) == traiter(charger_articles(DEMO))


# --- fichiers -------------------------------------------------------------

def test_ecrire_articles_cree_le_dossier_et_relit_le_meme_contenu(tmp_path):
    chemin = tmp_path / "sous" / "dossier" / "sortie.json"
    articles, _ = traiter(lot_sale())
    ecrire_articles(articles, chemin)
    assert json.loads(chemin.read_text(encoding="utf-8")) == articles


def test_lancer_ecrit_le_fichier_de_sortie(tmp_path):
    sortie = tmp_path / "articles_traites.json"
    stats = lancer(DEMO, sortie)
    ecrits = json.loads(sortie.read_text(encoding="utf-8"))
    assert len(ecrits) == stats["sortie"] > 0
    assert ecrits == traiter(charger_articles(DEMO))[0]


def test_sortie_utf8_non_echappe(tmp_path):
    sortie = tmp_path / "s.json"
    ecrire_articles([{"title": "Cybersécurité"}], sortie)
    assert "Cybersécurité" in sortie.read_text(encoding="utf-8")
