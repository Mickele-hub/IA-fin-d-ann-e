# Plateforme de veille intelligente et de détection d'opportunités

Application de veille technologique qui collecte automatiquement des articles depuis des flux RSS, les analyse avec de l'intelligence artificielle locale (Ollama), les classifie par domaine, et les présente dans une interface web interactive.

## 🎯 Objectif

Créer une plateforme complète de veille technologique permettant de :
- Collecter automatiquement des articles depuis plusieurs sources RSS
- Générer des résumés avec une IA locale privée (Ollama)
- Classifier les articles par domaine (IA, Cybersécurité, Cloud, Développement, etc.)
- Détecter des opportunités (appels à projets, partenariats, alertes sécurité)
- Présenter les résultats dans une interface web moderne avec filtres et exports

## 👥 Équipe et rôles

### Personne 1 – Collecte des données (n8n)
**Responsabilités :**
- Configuration de 5 sources RSS (CERT-FR, Inria, arXiv, CNCF, ANR)
- Création d'un workflow n8n automatisé pour la collecte
- Normalisation des données (titre, description, date, lien, source)
- Export des données en JSON

**Dossier :** `n8n/`
**Fichiers clés :**
- `workflow_n8n_collecte_v3.json` - Workflow n8n
- `README.md` - Documentation du workflow
- `data/articles_demo.json` - Données de démonstration

---

### Personne 2 – Traitement et classification (Intégré dans VigieLab)
**Responsabilités :**
- Nettoyage des données collectées
- Suppression des doublons
- Classification par domaine
- Définition des mots-clés et critères de classification

**Implémentation :** Intégré dans `vigielab/server/pipeline.ts` avec des règles heuristiques automatiques.

---

### Personne 3 – Intelligence artificielle et stockage (Ollama + SQLite)
**Responsabilités :**
- Installation et configuration d'Ollama
- Choix du modèle local adapté (`qwen3.5:4b`)
- Génération des résumés des publications
- Conception de la base de données SQLite
- Enregistrement des articles, catégories et résumés

**Dossiers :** `ai/`, `database/`
**Fichiers clés :**
- `ai/summarization.py` - Module de résumé avec Ollama
- `ai/process_articles.py` - Orchestration du traitement
- `database/schema.sql` - Schéma de base de données
- `database/database.py` - Gestion de la base SQLite

**Configuration Ollama :**
- Modèle : `qwen3.5:4b` (3.3 GB)
- Endpoint : `http://localhost:11434`
- Timeout : 300 secondes

---

### Personne 4 – Interface et intégration (VigieLab - TypeScript/React)
**Responsabilités :**
- Conception du tableau de bord
- Affichage des articles collectés avec filtres
- Affichage des résumés générés par l'IA
- Création de bulletins de veille HTML/PDF
- Intégration de tous les modules

**Dossier :** `vigielab/`
**Fichiers clés :**
- `server.ts` - Serveur Express.js avec API REST
- `server/ai.ts` - Logique d'analyse IA (Ollama + fallback)
- `server/db.ts` - Schéma de base de données SQLite
- `server/pipeline.ts` - Pipeline de collecte et traitement
- `src/` - Interface React avec TailwindCSS

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Sources RSS    │
│  (CERT-FR,      │
│   Inria, arXiv) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  n8n Workflow   │
│  (Personne 1)   │
│  Collecte &     │
│  Normalisation  │
└────────┬────────┘
         │ JSON (titre, description, date, lien, source)
         ▼
┌─────────────────┐
│  Adaptateur     │
│  n8n → VigieLab │
│  Conversion     │
│  format         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  VigieLab DB    │
│  (SQLite)       │
│  Stockage       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Ollama AI      │
│  (Personne 3)   │
│  Résumés        │
│  qwen3.5:4b     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Interface      │
│  React/TS       │
│  (Personne 4)   │
│  Tableau de     │
│  bord & Filtres │
└─────────────────┘
```

## 🚀 Installation et démarrage

### Prérequis
- Node.js (v18+)
- Python 3.8+
- Ollama installé avec le modèle `qwen3.5:4b`
- n8n (optionnel pour la collecte)

### 1. Installer Ollama et le modèle
```bash
# Installer Ollama
# https://ollama.com/download

# Télécharger le modèle
ollama pull qwen3.5:4b
```

### 2. Démarrer VigieLab
```bash
cd vigielab
npm install
npm run dev
```

L'interface sera accessible sur http://localhost:3000

### 3. Importer les données n8n
```bash
cd vigielab
python adapter_n8n_to_vigielab.py
```

### 4. Tester l'intégration Ollama
```bash
cd vigielab
python test_ollama_integration.py
python test_vigielab_api.py
```

## 📁 Structure du projet

```
IA-fin-d-ann-e/
├── n8n/                    # Workflow de collecte (Personne 1)
│   ├── workflow_n8n_collecte_v3.json
│   ├── README.md
│   └── data/
│       └── articles_demo.json
├── vigielab/               # Interface et intégration (Personne 4)
│   ├── server.ts
│   ├── server/
│   │   ├── ai.ts          # Analyse IA (Ollama)
│   │   ├── db.ts          # Base de données
│   │   ├── pipeline.ts    # Pipeline de traitement
│   │   └── snapshotData.ts
│   ├── src/               # Interface React
│   ├── package.json
│   └── veille.db          # Base SQLite (générée)
├── ai/                     # Module IA (Personne 3)
│   ├── summarization.py
│   └── process_articles.py
├── database/               # Base de données (Personne 3)
│   ├── schema.sql
│   └── database.py
├── datasets/               # Données de test
│   └── sample_articles.json
└── README.md
```

## 🔧 Configuration

### Ollama
- **Modèle :** `qwen3.5:4b`
- **Endpoint :** `http://localhost:11434`
- **Timeout :** 300 secondes (configuré dans `server/ai.ts`)

### Base de données
- **Type :** SQLite
- **Fichier :** `vigielab/veille.db`
- **Schéma :** Défini dans `server/db.ts`

### Sources RSS
1. CERT-FR (Cybersécurité)
2. Inria (Recherche)
3. arXiv cs.AI (IA)
4. CNCF Blog (Cloud)
5. ANR (Appels à projets)

## ✨ Fonctionnalités

### Collecte automatique
- 5 sources RSS configurées
- Collecte programmée (mode snapshot ou automatique)
- Normalisation des données

### Analyse IA locale
- Résumés générés par Ollama `qwen3.5:4b`
- Classification automatique par domaine
- Détection d'opportunités (appels à projets, partenariats)
- Score de pertinence

### Stockage structuré
- Base SQLite avec schéma complet
- Tables : items, sources, keywords, users, bulletins
- Déduplication par hash de contenu
- Historique des collectes

### Interface utilisateur
- Tableau de bord React moderne
- Filtres par domaine, source, type d'opportunité
- Affichage des résumés IA
- Export de bulletins de veille
- Authentification des utilisateurs

### API REST
- Endpoints pour articles, sources, mots-clés
- Régénération de résumés
- Export pour n8n et Python
- Gestion des utilisateurs

## 🛠️ Technologies utilisées

| Composant | Technologie |
|-----------|-------------|
| Collecte | n8n (Node.js) |
| IA | Ollama (qwen3.5:4b) |
| Base de données | SQLite |
| Backend | TypeScript, Express.js |
| Frontend | React, TailwindCSS, Lucide Icons |
| Build | Vite, tsx |
| Déploiement | Local (localhost:3000) |

## 📝 Scripts utilitaires

### `adapter_n8n_to_vigielab.py`
Convertit les données du workflow n8n au format VigieLab et les importe dans la base de données.

### `test_ollama_integration.py`
Teste la connexion à Ollama et la génération de résumés.

### `test_vigielab_api.py`
Teste l'API VigieLab pour la régénération de résumés avec Ollama.

### `force_ollama_settings.py`
Force les settings de VigieLab pour utiliser Ollama par défaut.

## 🎓 Points forts du projet

1. **IA locale et privée** : Pas de dépendance à des API cloud externes
2. **Architecture modulaire** : Chaque module est indépendant et testable
3. **Interface moderne** : UX soignée avec React et TailwindCSS
4. **Scalabilité** : Ajout facile de nouvelles sources RSS
5. **Personnalisation** : Configuration des mots-clés et domaines

## 📊 Harmonisation

Le projet a été harmonisé pour intégrer les contributions de chaque personne :
- **Personne 1** : Données n8n converties et importées dans VigieLab
- **Personne 3** : Ollama `qwen3.5:4b` configuré comme moteur IA par défaut
- **Personne 4** : VigieLab sert de plateforme unifiée pour l'interface et l'intégration

Les modules Python originaux (Personne 3) sont conservés pour référence mais VigieLab remplace maintenant toutes les fonctions de manière intégrée.

## 🔐 Identifiants par défaut

- **Email :** claire.moreau@vigielab.fr
- **Mot de passe :** VigieLab2026!

## 📄 Licence

Ce projet est réalisé dans le cadre d'un projet académique.
