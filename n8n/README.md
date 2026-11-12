# Module de collecte automatique (n8n)

> **Projet 7 : Plateforme de veille intelligente et de détection d'opportunités**
> Rôle couvert : **Personne 1, collecte des données**

Ce module collecte chaque jour des publications depuis des flux RSS publics, les nettoie, les normalise et les écrit dans un fichier `articles.json`. Ce fichier est la **porte d'entrée** du reste de la plateforme : le module Python de traitement et de classification (Personne 2) le lit, puis les résumés Ollama et la base SQLite (Personne 3) et le tableau de bord (Personne 4) en dépendent.

---

## Sommaire

1. [Vue d'ensemble](#1-vue-densemble)
2. [Contenu du dossier](#2-contenu-du-dossier)
3. [Sources RSS utilisées](#3-sources-rss-utilisées)
4. [Format des données (contrat d'interface)](#4-format-des-données-contrat-dinterface)
5. [Installation et lancement](#5-installation-et-lancement)
6. [Importer et configurer le workflow](#6-importer-et-configurer-le-workflow)
7. [Fonctionnement détaillé du workflow](#7-fonctionnement-détaillé-du-workflow)
8. [Résultats mesurés](#8-résultats-mesurés)
9. [Utiliser les données dans Python](#9-utiliser-les-données-dans-python)
10. [Démonstration reproductible hors ligne](#10-démonstration-reproductible-hors-ligne)
11. [Traçabilité](#11-traçabilité)
12. [Problèmes connus et solutions](#12-problèmes-connus-et-solutions)
13. [Limites et pistes d'amélioration](#13-limites-et-pistes-damélioration)
14. [Conformité avec le cadre du projet](#14-conformité-avec-le-cadre-du-projet)
15. [Documentation de référence](#15-documentation-de-référence)

---

## 1. Vue d'ensemble

```
                                          ┌─> RSS - The Hacker News ─┐
Lancement manuel ──┐                      ├─> RSS - arXiv cs.AI ─────┤
                   ├────────────────────> ├─> RSS - AWS News Blog ───┼─> Fusion ─> Normalisation ─> Conversion JSON ─> articles.json
Planification 8h ──┘                      ├─> RSS - Dev.to ──────────┤
                                          └─> RSS - Hugging Face ────┘
```

En résumé :
- le workflow démarre automatiquement chaque jour à **8h**, ou à la main pour un test ;
- il lit **5 flux RSS** en parallèle ;
- il fusionne les articles, supprime les doublons exacts et ne garde que les **30 plus récents par source** ;
- il convertit chaque article au **format commun** décrit plus bas ;
- il écrit le résultat dans `articles.json`.

## 2. Contenu du dossier

```
n8n/
├── README.md                      Ce document
└── workflow_n8n_collecte_v3.json  Le workflow n8n, à importer
data/
└── articles_demo.json             Jeu de données enregistré (démonstration hors ligne)
```

| Fichier | Rôle |
|---|---|
| `workflow_n8n_collecte_v3.json` | Export complet du workflow. Il s'importe dans n8n en un clic (voir section 6). |
| `articles_demo.json` | Capture figée d'une vraie collecte. Elle permet de travailler et de présenter une démo sans internet. |

## 3. Sources RSS utilisées

| Source | Domaine couvert | Adresse du flux |
|---|---|---|
| The Hacker News | Cybersécurité | `https://feeds.feedburner.com/TheHackersNews` |
| arXiv cs.AI | IA (publications scientifiques) | `https://rss.arxiv.org/rss/cs.AI` |
| AWS News Blog | Cloud | `https://aws.amazon.com/blogs/aws/feed/` |
| Dev.to | Développement | `https://dev.to/feed` |
| Hugging Face | IA, modèles ouverts | `https://huggingface.co/blog/feed.xml` |

Ce sont des flux RSS **publics**, publiés pour être lus par des programmes. Les conditions d'utilisation propres à chaque site n'ont pas fait l'objet d'une vérification détaillée.

## 4. Format des données (contrat d'interface)

Chaque article du fichier `articles.json` a exactement ces cinq champs :

```json
{
  "titre": "Titre de l'article",
  "description": "Résumé court en texte brut, sans HTML (1000 caractères maximum)",
  "date": "2026-11-11T08:00:00.000Z",
  "lien": "https://exemple.com/article",
  "source": "The Hacker News"
}
```

| Champ | Type | Détail |
|---|---|---|
| `titre` | texte | Titre nettoyé du HTML. |
| `description` | texte | Texte brut, tronqué à 1000 caractères. Peut être vide. |
| `date` | texte | Format ISO 8601 en UTC. |
| `lien` | texte | URL d'origine de l'article. Sert d'identifiant unique. |
| `source` | texte | Une de : `The Hacker News`, `arXiv cs.AI`, `AWS News Blog`, `Dev.to`, `Hugging Face`. |

Le fichier est un **tableau JSON** (une liste d'objets), encodé en UTF-8.

> **Important pour l'équipe** : si ce format doit changer, prévenez la Personne 1 afin de modifier le workflow en conséquence.

## 5. Installation et lancement

### Prérequis
- **Node.js**, version LTS : https://nodejs.org
- Aucun autre logiciel : n8n se lance avec `npx`, sans installation séparée.

### Lancer n8n

Dans un terminal :

```bash
npx n8n
```

Au premier lancement, n8n est téléchargé (quelques minutes). Ouvrir ensuite http://localhost:5678 dans le navigateur et créer un compte local. **Le terminal doit rester ouvert** tant que n8n est utilisé.

Version utilisée : n8n Community Edition, auto-hébergée en local sous Windows.
Une version récente est nécessaire : le nœud *Merge* à 5 entrées demande n8n 1.49 ou plus.

## 6. Importer et configurer le workflow

1. Dans n8n, créer un nouveau workflow.
2. Menu **⋯ → Import from file**, puis choisir `workflow_n8n_collecte_v3.json`.
3. Créer le dossier de sortie (Windows, PowerShell) :
   ```powershell
   mkdir $env:USERPROFILE\.n8n-files
   ```
4. Ouvrir le dernier nœud **Ecrire articles.json** et remplacer `VOTRE_NOM` dans le champ **File Path and Name** par le nom d'utilisateur Windows :
   ```
   C:\Users\<VOTRE_NOM>\.n8n-files\articles.json
   ```
5. Cliquer sur **Execute workflow** pour un test manuel. Tous les nœuds doivent passer au vert.
6. Cliquer sur **Publish** pour activer la collecte quotidienne.

Où se trouve le résultat :

| Fichier | Emplacement |
|---|---|
| Sortie du workflow | `C:\Users\<NOM>\.n8n-files\articles.json` |
| Jeu de secours versionné | `data/articles_demo.json` dans le dépôt |

> n8n restreint l'écriture de fichiers au dossier `.n8n-files` de l'utilisateur. Un chemin ailleurs sur le disque peut être refusé.

> **Fuseau horaire** : l'heure « 8h » dépend du fuseau configuré dans n8n (réglage du workflow ou de l'instance). À vérifier dans les paramètres du workflow si l'heure d'exécution est décalée.

> **Planification** : le workflow ne s'exécute que si le PC est allumé et que n8n est lancé.

## 7. Fonctionnement détaillé du workflow

Le workflow contient 11 nœuds.

### 7.1 Déclencheurs

| Nœud | Type | Rôle |
|---|---|---|
| Lancement manuel | Manual Trigger | Permet de tester le workflow à la demande. |
| Planification quotidienne 8h | Schedule Trigger | Lance la collecte tous les jours à 8h (intervalle de 1 jour). Le workflow doit être *publié* pour que la planification soit active. |

Les deux déclencheurs sont reliés aux mêmes 5 nœuds RSS.

### 7.2 Lecture des flux

Cinq nœuds **RSS Read** (un par source) lisent les flux en parallèle. Chacun est réglé en mode « continuer en cas d'erreur » : si un site est indisponible, les quatre autres sources sont quand même collectées.

### 7.3 Fusion

Le nœud **Merge** (mode *append*, 5 entrées) regroupe les articles des 5 sources en une seule liste.

### 7.4 Normalisation (nœud Code, JavaScript)

Le nœud **Normaliser les champs** applique les opérations suivantes, dans cet ordre :

1. **Nettoyage** : suppression des balises HTML et des entités (`&amp;`, `&nbsp;`...) dans le titre et la description.
2. **Filtrage** : rejet des articles sans titre ou sans lien.
3. **Détection de la source** : le nom de domaine du lien est comparé à une table (`thehackernews.com`, `arxiv.org`, `aws.amazon.com`, `dev.to`, `huggingface.co`).
4. **Date** : conversion au format ISO 8601 (date du jour si la date du flux est invalide).
5. **Description** : texte brut limité à 1000 caractères.
6. **Déduplication exacte** : un article dont le lien a déjà été vu est supprimé.
7. **Limitation** : tri par date décroissante, puis conservation des **30 articles les plus récents par source**.

Pour ajouter une source, il suffit d'ajouter un nœud RSS, de le relier au Merge (entrée supplémentaire) et d'ajouter son domaine dans la table `SOURCES` du nœud Code. La limite se règle avec la constante `MAX_PAR_SOURCE`.

### 7.5 Export

- **Convert to File** : transforme l'ensemble des articles en un fichier JSON unique.
- **Read/Write Files from Disk** : écrit `articles.json` sur le disque.

## 8. Résultats mesurés

Test réalisé le 11 novembre 2026 :

| Source | Articles lus | Articles conservés |
|---|---|---|
| The Hacker News | 50 | 30 |
| arXiv cs.AI | 381 | 30 |
| AWS News Blog | 20 | 20 |
| Dev.to | 12 | 12 |
| Hugging Face | 903 | 30 |
| **Total** | **1366** | **122** |

- Taux de réduction : environ **91 %** (1 − 122/1366).
- Les 5 flux étaient disponibles lors du test (5 sur 5).
- Les volumes dépendent du contenu des flux le jour de la collecte et varient donc d'un jour à l'autre.

La limite de 30 articles par source vise à ne garder que des publications récentes et à limiter la charge de calcul du module de résumé IA (Ollama).

> La déduplication faite ici ne concerne que les doublons **exacts** (même lien). La détection des quasi-doublons (même sujet, titres proches ou sources différentes) relève du module Python de la Personne 2.

## 9. Utiliser les données dans Python

```python
import json

with open("data/articles_demo.json", encoding="utf-8") as f:
    articles = json.load(f)

print(len(articles), "articles")
print(articles[0]["titre"], "-", articles[0]["source"])
```

Avec pandas :

```python
import pandas as pd

df = pd.read_json("data/articles_demo.json")
df["date"] = pd.to_datetime(df["date"])
print(df["source"].value_counts())
```

## 10. Démonstration reproductible hors ligne

Le projet impose une démonstration possible même si les sources externes sont momentanément indisponibles.

- `data/articles_demo.json` est une **capture figée** d'une vraie collecte.
- Pour une démo sans internet, les modules suivants lisent ce fichier à la place de la sortie du workflow.
- Ce fichier ne doit pas être modifié : c'est la référence commune de l'équipe, qui rend les résultats comparables et reproductibles.

## 11. Traçabilité

n8n conserve l'historique de chaque exécution : date, durée, statut et données traitées par chaque nœud. Il est consultable dans l'onglet **Executions** du workflow. En cas d'erreur, le nœud concerné est signalé en rouge avec son message d'erreur.

## 12. Problèmes connus et solutions

| Symptôme | Cause | Solution |
|---|---|---|
| Nœud **Ecrire articles.json** en rouge : « The file or directory does not exist » | Le chemin est celui de Linux ou le dossier n'existe pas | Créer `.n8n-files` et mettre un chemin Windows complet (section 6). |
| Toutes les sources valent `Inconnue` et seulement 30 articles sortent | Version précédente du workflow : la fonction `new URL()` n'est pas disponible dans le nœud Code de n8n | Utiliser `workflow_n8n_collecte_v3.json`, qui extrait le domaine avec une expression régulière. |
| Un flux RSS est rouge | Site indisponible ou adresse modifiée | Les autres sources continuent. Vérifier l'adresse du flux dans le navigateur. |
| La collecte de 8h ne se lance pas | Workflow non publié, PC éteint ou n8n fermé | Cliquer sur **Publish**, garder n8n lancé. Vérifier aussi le fuseau horaire. |
| Le nœud Merge n'a pas 5 entrées | n8n trop ancien | Mettre à jour n8n. |

## 13. Limites et pistes d'amélioration

- La collecte dépend d'un PC allumé. Un déploiement sur serveur ou en conteneur Docker permettrait une exécution permanente.
- Le volume est limité par source (30 articles) sans filtre de pertinence : le filtrage par thèmes est assuré en aval par le module Python.
- Le workflow écrase `articles.json` à chaque exécution. Un historique daté des fichiers permettrait de comparer les collectes dans le temps.
- Les flux peuvent changer d'adresse ou de structure sans préavis.

## 14. Conformité avec le cadre du projet

| Exigence | Réponse du module |
|---|---|
| Logiciels et API payants interdits | n8n Community Edition (gratuite), flux RSS publics, aucun abonnement. |
| Exécution locale | Tout tourne sur l'ordinateur de l'étudiant. |
| 3 à 5 sources publiques, idéalement RSS | 5 sources RSS. |
| Collecte planifiée via n8n | Schedule Trigger quotidien à 8h. |
| Conservation des informations obtenues | Fichier `articles.json`. |
| Démonstration reproductible | Jeu de données `data/articles_demo.json`. |
| Workflow traçable | Historique des exécutions de n8n. |

n8n Community Edition est distribuée sous licence *fair-code*, qui comporte des restrictions pour un usage commercial. Elle convient au cadre pédagogique du projet.

## 15. Documentation de référence

Documentation officielle de n8n (page d'accueil : https://docs.n8n.io/) :

| Sujet | Lien |
|---|---|
| Nœud RSS Read | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.rssfeedread/ |
| Nœud Schedule Trigger | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/ |
| Nœud Merge | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.merge/ |
| Nœud Code | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.code/ |
| Nœud Convert to File | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.converttofile/ |
| Nœud Read/Write Files from Disk | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.readwritefile/ |

Autres liens :
- n8n : https://n8n.io/
- Node.js : https://nodejs.org
- Kit officiel n8n + Ollama + Qdrant + PostgreSQL (facultatif) : https://github.com/n8n-io/self-hosted-ai-starter-kit
