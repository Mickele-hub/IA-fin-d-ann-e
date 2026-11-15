"""Tests du module preparation.py.

Lancer depuis la racine du dépôt :
    pytest traitement/tests -v
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from classification import classifier_articles  # noqa: E402
from doublons import supprimer_doublons  # noqa: E402
from nettoyage import charger_articles, nettoyer_articles  # noqa: E402
from preparation import (  # noqa: E402
    CHAMPS_SORTIE,
    LONGUEUR_MAX_TEXTE,
    construire_texte_llm,
    couper_texte,
    preparer_article,
    preparer_articles,
)

DEMO = Path(__file__).resolve().parents[2] / "data" / "articles_demo.json"

# Copie du schéma de la personne 3 (database/schema.sql) et de la requête de
# database.py. À mettre à jour ici si elle modifie sa table.
SCHEMA_BASE = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    link TEXT UNIQUE NOT NULL,
    source TEXT,
    published_at TEXT,
    category TEXT,
    summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""
REQUETE_INSERTION = """
INSERT OR IGNORE INTO articles
(title, description, link, source, published_at, category, summary)
VALUES (?, ?, ?, ?, ?, ?, ?)
"""


def insert_article(connexion, article):
    """Même logique que insert_article de database.py (personne 3)."""
    connexion.execute(REQUETE_INSERTION, (
        article["title"],
        article.get("description", ""),
        article["link"],
        article.get("source", ""),
        article.get("published_at", ""),
        article.get("category", ""),
        article.get("summary", ""),
    ))


def article(**champs):
    base = {
        "titre": "Un titre", "description": "Une description.",
        "date": "2026-11-14T08:00:00Z", "lien": "https://exemple.com/a",
        "source": "Blog", "categorie": "Cybersécurité",
    }
    base.update(champs)
    return base


# --- couper_texte ---------------------------------------------------------

def test_texte_court_inchange():
    assert couper_texte("Un texte.", 100) == "Un texte."


def test_texte_long_coupe_au_dernier_mot():
    resultat = couper_texte("mot " * 100, 50)
    assert len(resultat) <= 50
    assert resultat.endswith("mot...")


# --- construire_texte_llm -------------------------------------------------

def test_texte_llm_titre_puis_description():
    assert construire_texte_llm(article()) == "Un titre\n\nUne description."


def test_texte_llm_titre_seul_si_description_vide():
    assert construire_texte_llm(article(description="")) == "Un titre"


def test_texte_llm_limite_de_longueur_et_titre_conserve():
    resultat = construire_texte_llm(article(description="phrase " * 1000))
    assert len(resultat) <= LONGUEUR_MAX_TEXTE
    assert resultat.startswith("Un titre\n\n")
    assert resultat.endswith("...")


# --- preparer_article -----------------------------------------------------

def test_champs_renommes_comme_la_base():
    prepare = preparer_article(article())
    assert tuple(prepare) == CHAMPS_SORTIE
    assert prepare["title"] == "Un titre"
    assert prepare["link"] == "https://exemple.com/a"
    assert prepare["published_at"] == "2026-11-14T08:00:00Z"
    assert prepare["category"] == "Cybersécurité"
    assert "summary" not in prepare


def test_categorie_absente_devient_autres():
    sans_categorie = article()
    del sans_categorie["categorie"]
    assert preparer_article(sans_categorie)["category"] == "Autres"


def test_entree_non_modifiee():
    entree = [article()]
    copie = json.loads(json.dumps(entree))
    preparer_articles(entree)
    assert entree == copie


def test_sortie_serialisable_en_json():
    assert json.loads(json.dumps(preparer_articles([article()]), ensure_ascii=False))


# --- compatibilité avec la base SQLite de la personne 3 -------------------

def base_vide():
    connexion = sqlite3.connect(":memory:")
    connexion.executescript(SCHEMA_BASE)
    return connexion


def demo_prete():
    propres = supprimer_doublons(nettoyer_articles(charger_articles(DEMO)))
    return preparer_articles(classifier_articles(propres))


def test_base_tous_les_articles_de_la_demo_sont_inseres():
    articles = demo_prete()
    connexion = base_vide()
    for a in articles:
        insert_article(connexion, a)
    assert connexion.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == len(articles)


def test_base_reinsertion_ne_cree_pas_de_doublon():
    articles = demo_prete()
    connexion = base_vide()
    for _ in range(2):
        for a in articles:
            insert_article(connexion, a)
    assert connexion.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == len(articles)


def test_base_valeurs_stockees_conformes():
    connexion = base_vide()
    insert_article(connexion, preparer_article(article()))
    ligne = connexion.execute(
        "SELECT title, link, published_at, category, summary FROM articles"
    ).fetchone()
    assert ligne == ("Un titre", "https://exemple.com/a", "2026-11-14T08:00:00Z", "Cybersécurité", "")


def test_demo_aucun_champ_obligatoire_vide():
    for a in demo_prete():
        assert a["title"] and a["link"] and a["category"] and a["texte_pour_llm"]
        assert len(a["texte_pour_llm"]) <= LONGUEUR_MAX_TEXTE
