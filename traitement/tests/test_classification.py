"""Tests du module classification.py.

Lancer depuis la racine du dépôt :
    pytest traitement/tests -v
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from classification import (  # noqa: E402
    CATEGORIE_PAR_DEFAUT,
    DOMAINES,
    classifier_article,
    classifier_articles,
    scores_article,
)
from doublons import supprimer_doublons  # noqa: E402
from nettoyage import charger_articles, nettoyer_articles  # noqa: E402

DEMO = Path(__file__).resolve().parents[2] / "data" / "articles_demo.json"

CYBER = "Cybersécurité"
IA = "Intelligence artificielle"
CLOUD = "Cloud et infrastructure"
DEV = "Développement logiciel"


def art(titre="Some news", description="x", **autres):
    return {"titre": titre, "description": description, **autres}


# --- configuration --------------------------------------------------------

def test_noms_des_domaines():
    assert set(DOMAINES) == {CYBER, IA, CLOUD, DEV}
    assert CATEGORIE_PAR_DEFAUT == "Autres"


def test_aucun_mot_cle_en_double_dans_un_domaine_ou_entre_domaines():
    tous = [mot for liste in DOMAINES.values() for niveau in ("forts", "faibles") for mot in liste[niveau]]
    doublons = [mot for mot, n in Counter(tous).items() if n > 1]
    assert doublons == []


# --- un exemple par domaine -----------------------------------------------

def test_cybersecurite():
    assert classifier_article(art("Critical vulnerability exploited in the wild")) == CYBER


def test_intelligence_artificielle():
    assert classifier_article(art("New language model beats benchmarks", "The LLM was trained on text.")) == IA


def test_cloud():
    assert classifier_article(art("AWS Lambda adds a new runtime", "Available in all regions.")) == CLOUD


def test_developpement():
    assert classifier_article(art("Python 4 released with a new compiler", "For every developer.")) == DEV


def test_sujet_sans_rapport_va_dans_autres():
    assert classifier_article(art("Recette de crêpes bretonnes", "Farine, oeufs et lait.")) == "Autres"


# --- scores, seuils et départage ------------------------------------------

def test_un_mot_du_titre_compte_double():
    dans_titre = scores_article(art("Malware", "x"))[CYBER]["score"]
    dans_description = scores_article(art("Some news", "malware"))[CYBER]["score"]
    assert dans_titre == 2 * dans_description == 6


def test_un_mot_repete_nest_compte_quune_fois():
    assert scores_article(art("Some news", "malware malware malware"))[CYBER]["score"] == 3


def test_score_trop_faible_donne_autres():
    assert classifier_article(art("Some news", "A word about security.")) == "Autres"


def test_description_vide_seuil_reduit():
    assert classifier_article(art("A flaw", "")) == CYBER
    assert classifier_article(art("Unrelated words here", "")) == "Autres"


def test_egalite_parfaite_donne_autres():
    article = art("Some news", "ai model training security flaw threat")
    scores = scores_article(article)
    assert scores[IA]["score"] == scores[CYBER]["score"] == 3
    assert classifier_article(article) == "Autres"


def test_egalite_de_score_departagee_par_les_mots_forts():
    article = art("Some news", "malware ai model training")
    scores = scores_article(article)
    assert scores[CYBER]["score"] == scores[IA]["score"] == 3
    assert classifier_article(article) == CYBER


# --- façon de reconnaître les mots ----------------------------------------

def test_pluriels_prefixes_et_tirets():
    mots = scores_article(art("Vulnerabilities exploited in a Zero-Day attack"))[CYBER]["mots"]
    assert {"vulnerabilit*", "exploit*", "zero day"} <= set(mots)


def test_javascript_ne_declenche_pas_java():
    mots = scores_article(art("JavaScript tips"))[DEV]["mots"]
    assert "javascript" in mots and "java" not in mots


def test_agency_ne_declenche_pas_agent():
    assert scores_article(art("A government agency report"))[IA]["mots"] == []


def test_mots_entiers_seulement():
    assert scores_article(art("He said the main plan was to maintain it"))[IA]["mots"] == []


def test_accents_ignores():
    scores = scores_article(art("Intelligence artificielle et vulnérabilité"))
    assert "intelligence artificielle" in scores[IA]["mots"]
    assert "vulnerabilit*" in scores[CYBER]["mots"]


def test_majuscules_ignorees():
    assert classifier_article(art("RANSOMWARE ATTACK ON HOSPITAL")) == CYBER


def test_champs_absents_ne_plantent_pas():
    assert classifier_article({}) == "Autres"


# --- classifier_articles --------------------------------------------------

def test_classifier_articles_ajoute_categorie_sans_toucher_au_reste():
    entree = [art("Critical vulnerability exploited", lien="https://exemple.com/a", source="Blog")]
    sortie = classifier_articles(entree)
    assert sortie[0]["categorie"] == CYBER
    assert sortie[0]["lien"] == "https://exemple.com/a" and sortie[0]["source"] == "Blog"
    assert "categorie" not in entree[0]


# --- données réelles (garde-fous, pas une mesure de précision) -------------

def classer_demo():
    propres = supprimer_doublons(nettoyer_articles(charger_articles(DEMO)))
    return propres, classifier_articles(propres)


def test_demo_toutes_les_categories_valides():
    propres, classes = classer_demo()
    valides = set(DOMAINES) | {"Autres"}
    assert len(classes) == len(propres)
    assert all(a["categorie"] in valides for a in classes)


def test_demo_peu_darticles_dans_autres():
    _, classes = classer_demo()
    autres = sum(a["categorie"] == "Autres" for a in classes)
    assert autres / len(classes) < 0.20


def part(classes, source, categorie):
    de_la_source = [a for a in classes if a["source"] == source]
    return sum(a["categorie"] == categorie for a in de_la_source) / len(de_la_source)


def test_demo_les_sources_tombent_surtout_dans_leur_domaine_naturel():
    _, classes = classer_demo()
    assert part(classes, "The Hacker News", CYBER) >= 0.6
    assert part(classes, "arXiv cs.AI", IA) >= 0.7
    assert part(classes, "AWS News Blog", CLOUD) >= 0.6
    assert part(classes, "Hugging Face", IA) >= 0.6


def test_demo_classification_stable():
    propres, classes = classer_demo()
    assert classifier_articles(propres) == classes
