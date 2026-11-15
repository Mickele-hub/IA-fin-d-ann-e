"""Préparation des articles pour Ollama et pour la base SQLite (étape 7).

Deux tâches :
  1. construire pour chaque article un texte propre à résumer (texte_pour_llm) ;
  2. renommer les champs comme l'attend la base de la personne 3
     (database/schema.sql et database.py : title, link, published_at, category...).

Correspondance des champs :
    titre -> title          lien      -> link
    description -> description   date -> published_at
    source -> source        categorie -> category
Le champ « summary » n'est pas fourni : c'est la personne 3 qui le remplit avec Ollama.
Le champ « texte_pour_llm » est en plus : la base l'ignore, Ollama l'utilise.
"""

from classification import CATEGORIE_PAR_DEFAUT

# Longueur maximale du texte envoyé à Ollama (caractères). À ajuster avec la
# personne 3 selon le modèle choisi.
LONGUEUR_MAX_TEXTE = 1500

CHAMPS_SORTIE = (
    "title", "description", "published_at", "link", "source", "category", "texte_pour_llm",
)


def couper_texte(texte, longueur_max=LONGUEUR_MAX_TEXTE):
    """Coupe au dernier mot entier, avec « ... », sans dépasser longueur_max."""
    if len(texte) <= longueur_max:
        return texte
    coupe = texte[: longueur_max - 3]
    dernier_espace = coupe.rfind(" ")
    if dernier_espace > 0:
        coupe = coupe[:dernier_espace]
    return coupe.rstrip(" ,;:-") + "..."


def construire_texte_llm(article, longueur_max=LONGUEUR_MAX_TEXTE):
    """Titre puis description, séparés par une ligne vide (titre seul si pas de description)."""
    titre = article.get("titre", "").strip()
    description = article.get("description", "").strip()
    texte = f"{titre}\n\n{description}" if description else titre
    return couper_texte(texte, longueur_max)


def preparer_article(article):
    """Retourne l'article avec les noms de champs de la base de données."""
    return {
        "title": article["titre"],
        "description": article.get("description", ""),
        "published_at": article.get("date", ""),
        "link": article["lien"],
        "source": article.get("source", ""),
        "category": article.get("categorie") or CATEGORIE_PAR_DEFAUT,
        "texte_pour_llm": construire_texte_llm(article),
    }


def preparer_articles(articles):
    return [preparer_article(article) for article in articles]
