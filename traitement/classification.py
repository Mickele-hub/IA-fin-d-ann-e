"""Classification des articles par domaine, par mots-clés pondérés (étape 6).

Principe :
  - chaque domaine a des mots-clés « forts » (très discriminants, poids 3) et
    « faibles » (poids 1) ;
  - un mot-clé trouvé dans le titre compte double ;
  - chaque mot-clé n'est compté qu'une fois ;
  - le domaine au score le plus élevé gagne ; en dessous de SCORE_MIN
    (SCORE_MIN_TITRE_SEUL si la description est vide), ou en cas d'égalité
    parfaite, l'article va dans « Autres ».

Pour changer le comportement, il suffit de modifier le dictionnaire DOMAINES
ci-dessous (et les constantes de poids), sans toucher au reste du code.

Syntaxe des mots-clés (comparés sans accents ni majuscules) :
  - « mot »  : mot entier, pluriel simple accepté (flaw -> flaw, flaws) ;
  - « mot* » : tout mot qui commence par « mot » (exploit* -> exploited) ;
  - un tiret équivaut à un espace (zero-day = zero day).

Usage rapide, depuis la racine du dépôt :
    python3 traitement/classification.py data/articles_demo.json
    python3 traitement/classification.py data/articles_demo.json --detail
"""

import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

CATEGORIE_PAR_DEFAUT = "Autres"

POIDS_FORT = 3
POIDS_FAIBLE = 1
FACTEUR_TITRE = 2
SCORE_MIN = 3
# Quand la description est vide (ex. flux Hugging Face), seul le titre peut
# parler : un seul mot faible dans le titre (2 points) suffit alors.
SCORE_MIN_TITRE_SEUL = 2

DOMAINES = {
    "Cybersécurité": {
        "forts": [
            "vulnerabilit*", "exploit*", "malware", "ransomware", "phishing",
            "zero day", "cve", "breach", "backdoor*", "attacker", "botnet",
            "spyware", "trojan", "cyber*", "ddos", "denial of service",
            "remote code execution", "data leak", "cybersecurite", "faille",
            "key compromise", "credential theft", "supply chain attack",
            "sandbox escape", "privilege escalation", "rootkit", "exfiltrat*",
            "intrusion",
        ],
        "faibles": [
            "security", "flaw", "threat", "attack", "password", "encrypt*",
            "authentication", "patch*", "hacker", "hacked", "leak*",
            "unauthorized", "compromise*", "certificate", "secret",
            "securite", "menace", "stolen", "steal*", "spoof*", "tamper*",
            "incident*",
        ],
    },
    "Intelligence artificielle": {
        "forts": [
            "llm", "language model", "machine learning", "deep learning",
            "neural network", "reinforcement learning", "foundation model",
            "multimodal", "fine tuning", "agent*", "gpt", "chatgpt", "claude",
            "gemini", "ollama", "openai", "anthropic", "generative ai",
            "artificial intelligence", "intelligence artificielle", "pytorch",
            "tensorflow", "computer vision", "speech recognition",
            "diffusion model", "apprentissage automatique", "trainium", "gpu",
            "tpu", "torch*", "transformers", "diffusers", "mistral", "llama",
            "qwen", "deepseek", "gemma", "nemotron", "asr", "tts",
            "robot learning", "slm",
        ],
        "faibles": [
            "ai", "model", "training", "inference", "dataset", "benchmark",
            "prompt", "hugging face", "embedding", "reasoning", "neural",
            "learning", "modele", "speech", "synthetic",
        ],
    },
    "Cloud et infrastructure": {
        "forts": [
            "aws", "amazon web services", "amazon s3", "ec2", "lambda",
            "azure", "google cloud", "kubernetes", "k8s", "serverless",
            "terraform", "pulumi", "dynamodb", "cloudflare", "cloudformation",
            "ecs", "eks", "vpc", "cloud native", "data center", "bedrock",
            "aws weekly roundup", "cloudwatch",
        ],
        "faibles": [
            "cloud", "infrastructure", "container*", "deployment",
            "docker", "devops", "scalab*", "managed service", "hosting",
            "nuage",
        ],
    },
    "Développement logiciel": {
        "forts": [
            "programming", "sdk", "api", "open source", "github",
            "python", "java", "javascript", "typescript", "rust", "react",
            "golang", "kotlin", "compiler", "refactor*", "debug*", "asp.net",
            "web development", "frontend", "backend", "full stack",
            "programmation",
        ],
        "faibles": [
            "framework", "code", "developer", "library", "libraries", "tutorial", "app",
            "software", "tool", "git", "npm", "developpeur", "logiciel",
        ],
    },
}


def _normaliser(texte):
    """Minuscules, sans accents, tirets et soulignés remplacés par des espaces."""
    texte = unicodedata.normalize("NFD", str(texte).lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.replace("-", " ").replace("_", " ")
    return re.sub(r"\s+", " ", texte).strip()


def _motif(mot):
    """Compile un mot-clé en expression régulière (voir la syntaxe en tête de fichier)."""
    mot = _normaliser(mot)
    if mot.endswith("*"):
        return re.compile(rf"(?<![a-z0-9]){re.escape(mot[:-1])}[a-z0-9]*")
    return re.compile(rf"(?<![a-z0-9]){re.escape(mot)}(?:s|es)?(?![a-z0-9])")


MOTIFS = {
    domaine: [(mot, poids, _motif(mot))
              for niveau, poids in (("forts", POIDS_FORT), ("faibles", POIDS_FAIBLE))
              for mot in listes[niveau]]
    for domaine, listes in DOMAINES.items()
}


def scores_article(article):
    """Score détaillé par domaine : {domaine: {"score", "forts", "mots"}}."""
    titre = _normaliser(article.get("titre", ""))
    description = _normaliser(article.get("description", ""))
    resultat = {}
    for domaine, motifs in MOTIFS.items():
        score = nb_forts = 0
        trouves = []
        for mot, poids, motif in motifs:
            if motif.search(titre):
                points = poids * FACTEUR_TITRE
            elif motif.search(description):
                points = poids
            else:
                continue
            score += points
            nb_forts += poids == POIDS_FORT
            trouves.append(mot)
        resultat[domaine] = {"score": score, "forts": nb_forts, "mots": trouves}
    return resultat


def classifier_article(article):
    """Retourne le nom du domaine de l'article, ou « Autres »."""
    classement = sorted(
        scores_article(article).items(),
        key=lambda element: (element[1]["score"], element[1]["forts"]),
        reverse=True,
    )
    (meilleur, premier), (_, second) = classement[0], classement[1]
    seuil = SCORE_MIN if article.get("description") else SCORE_MIN_TITRE_SEUL
    if premier["score"] < seuil:
        return CATEGORIE_PAR_DEFAUT
    if (premier["score"], premier["forts"]) == (second["score"], second["forts"]):
        return CATEGORIE_PAR_DEFAUT
    return meilleur


def classifier_articles(articles):
    """Retourne de nouveaux articles avec le champ « categorie » ajouté."""
    return [{**article, "categorie": classifier_article(article)} for article in articles]


if __name__ == "__main__":
    from doublons import supprimer_doublons
    from nettoyage import charger_articles, nettoyer_articles

    arguments = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(arguments) != 1:
        sys.exit("Usage : python3 traitement/classification.py chemin/vers/articles.json [--detail]")
    articles = classifier_articles(
        supprimer_doublons(nettoyer_articles(charger_articles(Path(arguments[0]))))
    )

    print(f"\nRépartition des {len(articles)} articles :")
    for categorie, nombre in Counter(a["categorie"] for a in articles).most_common():
        print(f"  {categorie:<26} {nombre:>4}")

    print("\nPar source :")
    for source in sorted({a["source"] for a in articles}):
        repartition = Counter(a["categorie"] for a in articles if a["source"] == source)
        details = ", ".join(f"{c} {n}" for c, n in repartition.most_common())
        print(f"  {source:<16} {details}")

    if "--detail" in sys.argv:
        print("\nDétail (catégorie | source | titre) :")
        for a in articles:
            print(f"  {a['categorie']:<26} | {a['source']:<16} | {a['titre'][:70]}")
    else:
        autres = [a for a in articles if a["categorie"] == CATEGORIE_PAR_DEFAUT]
        print(f"\nArticles classés « {CATEGORIE_PAR_DEFAUT} » (à examiner pour améliorer les mots-clés) :")
        for a in autres[:15]:
            print(f"  - [{a['source']}] {a['titre'][:80]}")
        if len(autres) > 15:
            print(f"  ... et {len(autres) - 15} autres (voir --detail)")
