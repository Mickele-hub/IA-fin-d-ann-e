"""Tests du module doublons.py.

Lancer depuis la racine du dépôt :
    pytest traitement/tests -v
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from doublons import (  # noqa: E402
    cle_lien,
    cle_titre,
    meilleur_article,
    supprimer_doublons,
    titres_proches,
)
from nettoyage import charger_articles, nettoyer_articles  # noqa: E402

DEMO = Path(__file__).resolve().parents[2] / "data" / "articles_demo.json"


def article(titre="Un titre assez long pour le test", lien="https://exemple.com/a",
            description="Une description.", date="2026-11-14T08:00:00Z", source="Blog"):
    return {"titre": titre, "description": description, "date": date, "lien": lien, "source": source}


# --- clés de comparaison --------------------------------------------------

def test_cle_lien_ignore_schema_www_et_slash_final():
    reference = cle_lien("https://exemple.com/a/b")
    assert cle_lien("http://exemple.com/a/b") == reference
    assert cle_lien("https://www.exemple.com/a/b/") == reference
    assert cle_lien("https://EXEMPLE.com/a/b#haut") == reference


def test_cle_lien_distingue_des_pages_differentes():
    assert cle_lien("https://exemple.com/a") != cle_lien("https://exemple.com/b")
    assert cle_lien("https://exemple.com/a?id=1") != cle_lien("https://exemple.com/a?id=2")


def test_cle_lien_ordre_des_parametres_sans_importance():
    assert cle_lien("https://exemple.com/a?x=1&y=2") == cle_lien("https://exemple.com/a?y=2&x=1")


def test_cle_titre_ignore_casse_accents_et_ponctuation():
    assert cle_titre("  Été : l'IA, plus RAPIDE !  ") == "ete l ia plus rapide"


# --- titres proches -------------------------------------------------------

def test_titres_proches_avec_suffixe():
    a = cle_titre("Critical Zero-Day Flaw Exploited in Chrome Browser")
    b = cle_titre("Critical Zero Day Flaw Exploited in Chrome Browser, Google Warns")
    assert titres_proches(a, b)


def test_titres_proches_avec_mot_ajoute():
    a = cle_titre("Amazon S3 adds new storage class for archives")
    b = cle_titre("Amazon S3 adds a new storage class for archives")
    assert titres_proches(a, b)


def test_titres_differents_dun_seul_mot_ne_sont_pas_fusionnes():
    a = cle_titre("Learning to rank with graph neural networks")
    b = cle_titre("Learning to cluster with graph neural networks")
    assert not titres_proches(a, b)


def test_titres_courts_compares_en_egalite_stricte_seulement():
    assert not titres_proches(cle_titre("Rust 1.80 released"), cle_titre("Rust 1.81 released"))


# --- meilleur_article -----------------------------------------------------

def test_meilleur_garde_la_description_la_plus_longue():
    court, long_ = article(description="Court."), article(description="Une description bien plus longue.")
    assert meilleur_article(court, long_) is long_
    assert meilleur_article(long_, court) is long_


def test_meilleur_a_egalite_garde_le_plus_ancien():
    ancien, recent = article(date="2026-11-10T08:00:00Z"), article(date="2026-11-14T08:00:00Z")
    assert meilleur_article(recent, ancien) is ancien


def test_meilleur_a_egalite_totale_garde_le_premier():
    a, b = article(), article()
    assert meilleur_article(a, b) is a


# --- supprimer_doublons ---------------------------------------------------

def test_liste_vide():
    assert supprimer_doublons([]) == []


def test_articles_differents_tous_conserves():
    entree = [
        article(titre="Premier article sur la cybersecurite", lien="https://exemple.com/1"),
        article(titre="Deuxieme article sur le cloud computing", lien="https://exemple.com/2"),
    ]
    assert supprimer_doublons(entree) == entree


def test_meme_lien_une_seule_copie():
    entree = [
        article(titre="Titre numero un de test", lien="https://exemple.com/a"),
        article(titre="Titre complètement différent", lien="http://www.exemple.com/a/"),
    ]
    assert len(supprimer_doublons(entree)) == 1


def test_meme_titre_sources_differentes():
    entree = [
        article(titre="Une faille critique découverte !", lien="https://un.com/x", source="Un"),
        article(titre="une faille critique decouverte", lien="https://deux.com/y", source="Deux"),
    ]
    assert len(supprimer_doublons(entree)) == 1


def test_titres_proches_fusionnes():
    entree = [
        article(titre="OpenAI Releases New Reasoning Model for Developers", lien="https://un.com/x"),
        article(titre="OpenAI releases new reasoning model for developers today", lien="https://deux.com/y"),
    ]
    assert len(supprimer_doublons(entree)) == 1


def test_garde_la_version_la_plus_complete_a_la_place_du_premier():
    entree = [
        article(lien="https://exemple.com/a", description="", source="Vide"),
        article(lien="https://exemple.com/a", description="Version complète.", source="Pleine"),
    ]
    sortie = supprimer_doublons(entree)
    assert len(sortie) == 1
    assert sortie[0]["source"] == "Pleine"


def test_ordre_dapparition_conserve():
    entree = [
        article(titre="Article A à propos du réseau", lien="https://exemple.com/a"),
        article(titre="Article B à propos du stockage", lien="https://exemple.com/b"),
        article(titre="Article A à propos du réseau", lien="https://autre.com/a"),
        article(titre="Article C à propos du système", lien="https://exemple.com/c"),
    ]
    sortie = supprimer_doublons(entree)
    assert [a["titre"] for a in sortie] == [
        "Article A à propos du réseau",
        "Article B à propos du stockage",
        "Article C à propos du système",
    ]


def test_triple_doublon_une_seule_copie():
    entree = [article(lien=f"https://exemple.com/{i}") for i in range(3)]
    assert len(supprimer_doublons(entree)) == 1


def test_lentree_nest_pas_modifiee():
    entree = [article(), article(lien="https://autre.com/a")]
    copie = copy.deepcopy(entree)
    supprimer_doublons(entree)
    assert entree == copie


def test_idempotent():
    entree = [article(), article(lien="https://autre.com/a"), article(titre="Autre sujet totalement distinct", lien="https://exemple.com/z")]
    une_fois = supprimer_doublons(entree)
    assert supprimer_doublons(une_fois) == une_fois


# --- données réelles ------------------------------------------------------

def test_demo_aucun_article_perdu_car_pas_de_doublon():
    propres = nettoyer_articles(charger_articles(DEMO))
    assert supprimer_doublons(propres) == propres


def test_demo_avec_doublons_ajoutes_retrouve_la_taille_dorigine():
    propres = nettoyer_articles(charger_articles(DEMO))
    ajoutes = []
    for i, a in enumerate(propres[:10]):
        copie = copy.deepcopy(a)
        if i % 3 == 0:    # même lien, forme différente
            copie["lien"] = copie["lien"].replace("https://", "http://www.", 1)
        elif i % 3 == 1:  # même titre, autre source et autre lien
            copie["titre"] = copie["titre"].upper()
            copie["lien"] = f"https://miroir.example.org/{i}"
        else:             # même titre avec un suffixe
            copie["titre"] = copie["titre"] + " - par la rédaction"
            copie["lien"] = f"https://miroir.example.org/{i}"
        ajoutes.append(copie)
    sortie = supprimer_doublons(propres + ajoutes)
    assert len(sortie) == len(propres)
