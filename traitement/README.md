# Module de traitement et classification

Partie « traitement et classification Python » du projet de veille technologique
(rôle de la **personne 2**). Ce module reçoit les articles collectés par n8n, les
nettoie, supprime les doublons, les classe par domaine et les prépare pour le module
Ollama + SQLite.

## Place dans le projet

```
n8n (personne 1)
      │  articles.json
      ▼
traitement/ (personne 2) :  nettoyage ► doublons ► classification ► préparation
      │  articles_traites.json
      ▼
Ollama + SQLite (personne 3)
      ▼
Interface et bulletin (personne 4)
```

## Format d'entrée

Un fichier JSON contenant une liste d'articles produite par le workflow n8n
(`n8n/workflow_n8n_collecte_v3.json`), avec les champs :

| Champ | Contenu |
|---|---|
| `titre` | titre de l'article |
| `description` | résumé fourni par le flux RSS (peut être vide) |
| `date` | date de publication |
| `lien` | URL de l'article |
| `source` | nom de la source (The Hacker News, arXiv cs.AI, ...) |

Un exemple se trouve dans `data/articles_demo.json`.

## Format de sortie

Un fichier JSON (par défaut `data/articles_traites.json`) dont les champs reprennent
les noms de la base de données (`database/schema.sql`) :

| Champ | Contenu |
|---|---|
| `title` | titre nettoyé |
| `description` | description nettoyée (peut être vide) |
| `published_at` | date au format ISO 8601 UTC (ex. `2026-11-14T08:00:00Z`) |
| `link` | URL normalisée (sans paramètres de suivi) |
| `source` | nom de la source |
| `category` | domaine attribué (voir ci-dessous) |
| `texte_pour_llm` | texte à résumer par Ollama : titre, ligne vide, description (titre seul si pas de description), 1500 caractères au maximum |

Le champ `summary` de la base n'est pas fourni : il est rempli par le module Ollama.
Le champ `texte_pour_llm` n'est pas stocké en base, il sert uniquement à générer le résumé.

## Installation

Python 3 est nécessaire (testé avec Python 3.13). Depuis la racine du dépôt :

```
python3 -m venv traitement/venv
source traitement/venv/bin/activate
pip install -r traitement/requirements.txt
```

Dépendances : `beautifulsoup4` (nettoyage du HTML), `python-dateutil` (lecture des dates),
`pytest` (tests).

## Utilisation

Lancer toute la chaîne :

```
python3 traitement/main.py data/articles.json
```

Le résultat est écrit dans `data/articles_traites.json`. Pour choisir un autre fichier de
sortie : `--sortie chemin/vers/fichier.json`. Le programme affiche le nombre d'articles
après chaque étape et la répartition par catégorie.

Chaque étape peut aussi être lancée seule pour l'inspecter :

```
python3 traitement/nettoyage.py data/articles.json
python3 traitement/doublons.py data/articles.json
python3 traitement/classification.py data/articles.json            # répartition par domaine
python3 traitement/classification.py data/articles.json --detail   # article par article
```

## Fonctionnement des étapes

### 1. Nettoyage (`nettoyage.py`)

- Suppression du HTML et décodage des entités (`&amp;`...), normalisation Unicode et des espaces.
- Rejet des articles sans titre ou sans lien valide (`http`/`https`).
- Dates converties en ISO 8601 UTC ; si une date est illisible, la date du traitement est utilisée.
- Liens normalisés : suppression des paramètres de suivi (`utm_...`, `fbclid`...) et des ancres.
- Descriptions tronquées par n8n (à 1000 caractères) recoupées proprement à la dernière phrase complète.
- Retrait de l'en-tête automatique des flux arXiv (`arXiv:... Announce Type: ... Abstract:`).
- Les descriptions vides sont conservées vides.

### 2. Suppression des doublons (`doublons.py`)

Trois niveaux, du plus sûr au plus souple :

1. **même lien** (en ignorant `http`/`https`, `www.`, le `/` final et l'ordre des paramètres) ;
2. **même titre** (sans majuscules, accents ni ponctuation) ;
3. **titres très proches** : similarité d'au moins 85 % **et** l'un des titres contient tous les mots de l'autre.
   Ce choix est prudent : mieux vaut laisser passer un doublon que fusionner deux articles
   différents (par exemple deux titres ne différant que d'un mot).

Entre deux doublons, on garde l'article le plus complet (description la plus longue) puis,
à égalité, le plus ancien. Les titres de moins de 20 caractères ne sont comparés qu'en égalité stricte.

Ce module ne voit qu'un fichier à la fois. Les doublons d'un jour à l'autre sont gérés par la base
de données (colonne `link` unique, insertion avec `INSERT OR IGNORE`).

### 3. Classification (`classification.py`)

Classification **par mots-clés pondérés**, sans modèle d'apprentissage : simple, explicable et
modifiable sans réentraîner quoi que ce soit.

**Domaines** : Cybersécurité, Intelligence artificielle, Cloud et infrastructure, Développement logiciel,
et **Autres** quand aucun domaine ne se détache.

**Critères de décision**

1. Chaque domaine a des mots-clés *forts* (très discriminants, poids 3) et *faibles* (poids 1).
2. Un mot-clé trouvé dans le **titre** compte **double** (x2) ; chaque mot-clé n'est compté qu'une fois.
3. Le score d'un domaine est la somme des points de ses mots-clés trouvés.
4. Le domaine au score le plus élevé gagne.
5. Si le meilleur score est inférieur à **3** (ou à **2** quand la description est vide,
   car seul le titre peut alors parler), l'article est classé **Autres**.
6. En cas d'égalité de score, on retient le domaine qui a le plus de mots forts ; s'il y a encore égalité, **Autres**.
7. La **source n'intervient jamais** : on classe d'après le contenu, pas d'après le site d'origine.

**Syntaxe des mots-clés** (comparés sans accents ni majuscules, un tiret équivaut à un espace) :
`mot` = mot entier (pluriel simple accepté) ; `mot*` = tout mot commençant par `mot`
(par exemple `exploit*` reconnaît `exploited`).

**Mots-clés par domaine**

#### Cybersécurité

- **Mots forts** (poids 3) : `vulnerabilit*`, `exploit*`, `malware`, `ransomware`, `phishing`, `zero day`, `cve`, `breach`, `backdoor*`, `attacker`, `botnet`, `spyware`, `trojan`, `cyber*`, `ddos`, `denial of service`, `remote code execution`, `data leak`, `cybersecurite`, `faille`, `key compromise`, `credential theft`, `supply chain attack`, `sandbox escape`, `privilege escalation`, `rootkit`, `exfiltrat*`, `intrusion`
- **Mots faibles** (poids 1) : `security`, `flaw`, `threat`, `attack`, `password`, `encrypt*`, `authentication`, `patch*`, `hacker`, `hacked`, `leak*`, `unauthorized`, `compromise*`, `certificate`, `secret`, `securite`, `menace`, `stolen`, `steal*`, `spoof*`, `tamper*`, `incident*`

#### Intelligence artificielle

- **Mots forts** (poids 3) : `llm`, `language model`, `machine learning`, `deep learning`, `neural network`, `reinforcement learning`, `foundation model`, `multimodal`, `fine tuning`, `agent*`, `gpt`, `chatgpt`, `claude`, `gemini`, `ollama`, `openai`, `anthropic`, `generative ai`, `artificial intelligence`, `intelligence artificielle`, `pytorch`, `tensorflow`, `computer vision`, `speech recognition`, `diffusion model`, `apprentissage automatique`, `trainium`, `gpu`, `tpu`, `torch*`, `transformers`, `diffusers`, `mistral`, `llama`, `qwen`, `deepseek`, `gemma`, `nemotron`, `asr`, `tts`, `robot learning`, `slm`
- **Mots faibles** (poids 1) : `ai`, `model`, `training`, `inference`, `dataset`, `benchmark`, `prompt`, `hugging face`, `embedding`, `reasoning`, `neural`, `learning`, `modele`, `speech`, `synthetic`

#### Cloud et infrastructure

- **Mots forts** (poids 3) : `aws`, `amazon web services`, `amazon s3`, `ec2`, `lambda`, `azure`, `google cloud`, `kubernetes`, `k8s`, `serverless`, `terraform`, `pulumi`, `dynamodb`, `cloudflare`, `cloudformation`, `ecs`, `eks`, `vpc`, `cloud native`, `data center`, `bedrock`, `aws weekly roundup`, `cloudwatch`
- **Mots faibles** (poids 1) : `cloud`, `infrastructure`, `container*`, `deployment`, `docker`, `devops`, `scalab*`, `managed service`, `hosting`, `nuage`

#### Développement logiciel

- **Mots forts** (poids 3) : `programming`, `sdk`, `api`, `open source`, `github`, `python`, `java`, `javascript`, `typescript`, `rust`, `react`, `golang`, `kotlin`, `compiler`, `refactor*`, `debug*`, `asp.net`, `web development`, `frontend`, `backend`, `full stack`, `programmation`
- **Mots faibles** (poids 1) : `framework`, `code`, `developer`, `library`, `libraries`, `tutorial`, `app`, `software`, `tool`, `git`, `npm`, `developpeur`, `logiciel`

### 4. Préparation (`preparation.py`)

Construit le champ `texte_pour_llm` et renomme les champs selon la base de données
(`titre` → `title`, `lien` → `link`, `date` → `published_at`, `categorie` → `category`).

## Modifier les mots-clés

Les mots-clés sont dans le dictionnaire `DOMAINES` en haut de `classification.py`.
Pour ajouter ou retirer un mot, il suffit de l'éditer dans la liste « forts » ou « faibles »
du domaine voulu, puis de relancer `pytest traitement/tests`. Pour examiner l'effet sur des
articles réels : `python3 traitement/classification.py data/articles.json --detail`.
Un mot-clé ne doit apparaître que dans un seul domaine (un test le vérifie).

## Tests

```
pytest traitement/tests -v
```

Les tests couvrent chaque étape (cas limites, entrée non modifiée, résultats stables),
la chaîne complète sur `data/articles_demo.json`, et la compatibilité des articles produits avec
la table SQLite de la personne 3 (insertion, absence de doublon à la réinsertion).

## Limites connues

- **Mots-clés surtout en anglais**, car les sources le sont. Un article dans une autre langue
  tombe le plus souvent dans « Autres » (sauf si son titre contient des termes techniques anglais).
- **Domaines qui se chevauchent** : un article sur la sécurité d'un agent IA, ou une newsletter AWS qui
  parle de modèles d'IA, peut raisonnablement relever de deux domaines. Un seul domaine est retenu,
  et un ex æquo parfait donne « Autres ».
- **Mots-clés ajustés sur les articles de démonstration** (122 articles de `data/articles_demo.json`) :
  la répartition obtenue est cohérente, mais aucune mesure formelle de précision n'a été réalisée.
  Il est conseillé de relire la répartition sur de nouvelles données (`--detail`) et d'enrichir les
  mots-clés si besoin.
- **Doublons entre jours** : gérés uniquement par le lien exact (contrainte `UNIQUE` de la base).
  La même actualité reprise le lendemain par une autre source, avec un autre lien, n'est pas détectée.
- Les titres proches ne sont fusionnés que de façon prudente (voir plus haut) : quelques quasi-doublons
  peuvent subsister.

## Structure du dossier

```
traitement/
├── main.py              point d'entrée : enchaîne toutes les étapes
├── nettoyage.py         étape 1
├── doublons.py          étape 2
├── classification.py    étape 3 (dictionnaire des mots-clés en tête de fichier)
├── preparation.py       étape 4
├── requirements.txt     dépendances
├── README.md            ce fichier
└── tests/               tests automatiques (pytest)
```
