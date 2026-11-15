"""Tests du module nettoyage.py.

Lancer depuis la racine du dépôt :
    pytest traitement/tests -v
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nettoyage import (  # noqa: E402
    charger_articles,
    nettoyer_article,
    nettoyer_articles,
    nettoyer_texte,
    normaliser_date,
    normaliser_lien,
    reparer_description,
)

DEMO = Path(__file__).resolve().parents[2] / "data" / "articles_demo.json"
FORMAT_DATE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
MAINTENANT = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)


def article(**champs):
    base = {
        "titre": "Un titre",
        "description": "Une description.",
        "date": "2026-11-14T08:00:00.000Z",
        "lien": "https://exemple.com/a",
        "source": "Blog",
    }
    base.update(champs)
    return base


# --- nettoyer_texte -------------------------------------------------------

def test_texte_retire_html_et_entites():
    brut = "<p>Du <a href='x'>texte</a>&nbsp;ici &amp; l&agrave;</p>"
    assert nettoyer_texte(brut) == "Du texte ici & là"


def test_texte_reduit_les_espaces():
    assert nettoyer_texte("  un   texte \n\t avec   espaces  ") == "un texte avec espaces"


def test_texte_non_chaine_donne_vide():
    assert nettoyer_texte(None) == ""
    assert nettoyer_texte(42) == ""


def test_texte_garde_les_comparaisons():
    assert nettoyer_texte("si a < b alors c") == "si a < b alors c"


# --- normaliser_lien ------------------------------------------------------

def test_lien_retire_tracking_et_ancre():
    lien = "https://exemple.com/a?utm_source=x&id=3&fbclid=abc#haut"
    assert normaliser_lien(lien) == "https://exemple.com/a?id=3"


def test_lien_sans_parametres_reste_identique():
    assert normaliser_lien("https://exemple.com/a/b") == "https://exemple.com/a/b"


def test_lien_invalide_donne_none():
    for mauvais in ["", "ftp://exemple.com", "pas un lien", None, 12]:
        assert normaliser_lien(mauvais) is None


# --- normaliser_date ------------------------------------------------------

def test_date_iso_utc():
    assert normaliser_date("2026-11-14T08:00:00.000Z", MAINTENANT) == "2026-11-14T08:00:00Z"


def test_date_avec_fuseau_convertie_en_utc():
    assert normaliser_date("Sat, 14 Nov 2026 08:00:00 +0300", MAINTENANT) == "2026-11-14T05:00:00Z"


def test_date_sans_fuseau_consideree_utc():
    assert normaliser_date("2026-11-14 08:00:00", MAINTENANT) == "2026-11-14T08:00:00Z"


def test_date_illisible_remplacee_par_maintenant():
    assert normaliser_date("n'importe quoi", MAINTENANT) == "2026-11-15T12:00:00Z"
    assert normaliser_date(None, MAINTENANT) == "2026-11-15T12:00:00Z"


# --- reparer_description --------------------------------------------------

def test_description_courte_inchangee():
    assert reparer_description("Courte description.") == "Courte description."
    assert reparer_description("") == ""


def test_description_tronquee_recoupee_a_la_derniere_phrase():
    phrase = "Ceci est une phrase complete. "
    brut = (phrase * 40)[:1000]
    resultat = reparer_description(brut)
    assert len(resultat) < len(brut)
    assert resultat.endswith(".")
    assert resultat == (phrase * 40)[: len(resultat)]


def test_description_tronquee_sans_ponctuation_finit_par_points():
    brut = ("mot " * 300)[:999]
    resultat = reparer_description(brut)
    assert resultat.endswith("mot...")
    assert len(resultat) <= 1000
    assert not resultat[:-3].endswith(" ")


def test_description_longue_mais_complete_inchangee():
    brut = ("Une phrase de remplissage. " * 40).strip()
    assert len(brut) > 990
    assert reparer_description(brut) == brut


# --- nettoyer_article / nettoyer_articles ---------------------------------

def test_article_valide_garde_les_cinq_champs():
    resultat = nettoyer_article(article(titre="<b>Hello &amp; bienvenue</b>"), MAINTENANT)
    assert set(resultat) == {"titre", "description", "date", "lien", "source"}
    assert resultat["titre"] == "Hello & bienvenue"


def test_article_sans_titre_ou_sans_lien_rejete():
    assert nettoyer_article(article(titre=""), MAINTENANT) is None
    assert nettoyer_article(article(titre="<p> </p>"), MAINTENANT) is None
    assert nettoyer_article(article(lien=""), MAINTENANT) is None
    assert nettoyer_article(article(lien="ftp://exemple.com"), MAINTENANT) is None


def test_article_non_dictionnaire_rejete():
    assert nettoyer_article("texte", MAINTENANT) is None
    assert nettoyer_article(None, MAINTENANT) is None


def test_source_absente_devient_inconnue():
    sans_source = article()
    del sans_source["source"]
    assert nettoyer_article(sans_source, MAINTENANT)["source"] == "Inconnue"


def test_description_absente_donne_chaine_vide():
    sans_description = article()
    del sans_description["description"]
    assert nettoyer_article(sans_description, MAINTENANT)["description"] == ""


def test_liste_ecarte_uniquement_les_invalides():
    entree = [article(), article(titre=""), "bizarre", article(lien="https://exemple.com/b")]
    sortie = nettoyer_articles(entree)
    assert len(sortie) == 2


def test_nettoyage_ne_modifie_pas_lentree():
    entree = [article(titre="<b>Titre</b>")]
    nettoyer_articles(entree)
    assert entree[0]["titre"] == "<b>Titre</b>"


# --- données réelles ------------------------------------------------------

def test_demo_tous_les_articles_conserves_et_propres():
    entree = charger_articles(DEMO)
    sortie = nettoyer_articles(entree)
    assert len(entree) > 0
    assert len(sortie) == len(entree)
    for a in sortie:
        assert set(a) == {"titre", "description", "date", "lien", "source"}
        assert a["titre"] and a["lien"].startswith("http") and a["source"]
        assert FORMAT_DATE.fullmatch(a["date"])
        assert not re.search(r"<[a-zA-Z/]", a["titre"] + a["description"])
        assert len(a["description"]) <= 1000


def test_demo_descriptions_tronquees_recoupees_proprement():
    entree = charger_articles(DEMO)
    sortie = nettoyer_articles(entree)
    for brut, propre in zip(entree, sortie):
        if len(brut["description"]) >= 990 and not brut["description"].endswith((".", "!", "?")):
            assert propre["description"].endswith((".", "!", "?"))


def test_demo_nettoyage_idempotent():
    premiere_passe = nettoyer_articles(charger_articles(DEMO))
    assert nettoyer_articles(premiere_passe) == premiere_passe
