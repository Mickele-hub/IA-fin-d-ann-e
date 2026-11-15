"""
Adaptateur pour convertir les données du workflow n8n (Personne 1) 
au format attendu par VigieLab (Personne 4)
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import hashlib

# Chemins
N8N_OUTPUT = Path("C:/Users/andri_c/.n8n-files/articles.json")
VIGIELAB_DB = Path("veille.db")

def convert_n8n_to_vigielab_format(n8n_article):
    """Convertit un article du format n8n au format VigieLab"""
    return {
        "sourceId": f"src-{n8n_article['source'].lower().replace(' ', '-')}",
        "sourceName": n8n_article['source'],
        "title": n8n_article['titre'],
        "link": n8n_article['lien'],
        "publishedAt": n8n_article['date'],
        "excerpt": n8n_article.get('description', ''),
        "fallbackDomain": map_source_to_domain(n8n_article['source'])
    }

def map_source_to_domain(source):
    """Mappe la source n8n vers un domaine VigieLab"""
    mapping = {
        "The Hacker News": "Cybersécurité",
        "arXiv cs.AI": "IA",
        "AWS News Blog": "Cloud",
        "Dev.to": "Développement",
        "Hugging Face": "IA"
    }
    return mapping.get(source, "IA")

def compute_content_hash(title):
    """Calcule un hash SHA256 du titre pour déduplication"""
    return hashlib.sha256(title.lower().encode()).hexdigest()

def insert_into_vigielab_db(article):
    """Insère un article dans la base VigieLab"""
    conn = sqlite3.connect(VIGIELAB_DB)
    cursor = conn.cursor()
    
    # Générer un ID unique
    item_id = f"item-{hashlib.md5(article['link'].encode()).hexdigest()[:12]}"
    content_hash = compute_content_hash(article['title'])
    
    # Vérifier si l'article existe déjà
    cursor.execute("SELECT id FROM items WHERE canonical_url = ?", (article['link'],))
    if cursor.fetchone():
        print(f"Article déjà existant: {article['title'][:50]}...")
        conn.close()
        return
    
    # Insérer l'article
    cursor.execute("""
        INSERT INTO items (
            id, title, canonical_url, original_url, content_hash,
            source_id, source_name, published_at, collected_at,
            raw_excerpt, ai_summary, key_points_json, domain,
            opportunity_type, matched_keywords_json, relevance_score,
            ai_engine, is_duplicate
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item_id,
        article['title'],
        article['link'],
        article['link'],
        content_hash,
        article['sourceId'],
        article['sourceName'],
        article['publishedAt'],
        datetime.now().isoformat(),
        article['excerpt'],
        "Résumé généré par Ollama (à compléter)",  # Sera remplacé par l'IA
        "[]",  # key_points vide pour l'instant
        article['fallbackDomain'],
        "Publication technique",
        "[]",  # matched_keywords vide
        10,  # relevance_score par défaut
        "Ollama (qwen3.5:4b)",
        0  # is_duplicate
    ))
    
    conn.commit()
    conn.close()
    print(f"Article inséré: {article['title'][:50]}...")

def main():
    # Lire le fichier n8n
    if not N8N_OUTPUT.exists():
        print(f"Fichier n8n non trouvé: {N8N_OUTPUT}")
        print("Utilisation du fichier de démonstration...")
        n8n_file = Path("../data/articles_demo.json")
    else:
        n8n_file = N8N_OUTPUT
    
    if not n8n_file.exists():
        print(f"Fichier non trouvé: {n8n_file}")
        return
    
    with open(n8n_file, 'r', encoding='utf-8') as f:
        n8n_articles = json.load(f)
    
    print(f"Chargement de {len(n8n_articles)} articles depuis n8n...")
    
    # Convertir et insérer chaque article
    for n8n_article in n8n_articles:
        vigielab_article = convert_n8n_to_vigielab_format(n8n_article)
        insert_into_vigielab_db(vigielab_article)
    
    print("Import terminé !")

if __name__ == "__main__":
    main()
