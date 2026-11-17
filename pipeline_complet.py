"""
Pipeline complet du projet : n8n -> traitement -> ai -> database
Connecte tous les modules Python (Personnes 1, 2, 3)
"""
import sys
import subprocess
from pathlib import Path

# Ajouter les dossiers au path
sys.path.append(str(Path(__file__).parent))

from ai.process_articles import process_articles

def pipeline_complet(fichier_entree="data/articles_demo.json"):
    """Exécute le pipeline complet de traitement"""
    print("=" * 60)
    print("PIPELINE COMPLET DU PROJET")
    print("=" * 60)
    
    # Étape 1 : Traitement (Personne 2)
    print("\n[Étape 1] Traitement et classification (Personne 2)")
    print("-" * 60)
    result = subprocess.run(
        [sys.executable, "traitement/main.py", fichier_entree],
        cwd=str(Path(__file__).parent),
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("Erreur lors du traitement:", result.stderr)
        return
    
    # Étape 2 : IA et stockage (Personne 3)
    print("\n[Étape 2] Résumé IA et stockage (Personne 3)")
    print("-" * 60)
    
    # Modifier process_articles pour lire articles_traites.json
    import json
    from ai.summarization import summarize_article
    from database.database import initialize_database, insert_article
    
    initialize_database()
    
    with open("data/articles_traites.json", "r", encoding="utf-8") as f:
        articles = json.load(f)
    
    # Pour le test, ne traiter que les 3 premiers articles
    articles = articles[:3]
    
    for article in articles:
        print(f"Traitement : {article['title'][:60]}...")
        
        # Utiliser texte_pour_llm si disponible, sinon description
        texte = article.get("texte_pour_llm", article.get("description", ""))
        
        summary = summarize_article(article["title"], texte)
        
        if summary:
            article["summary"] = summary
            # Ajouter les champs manquants pour la base
            article["category"] = article.get("category", "Autres")
            article["published_at"] = article.get("published_at", "")
            article["source"] = article.get("source", "")
            insert_article(article)
            print("✓ Article enregistré")
    
    print("\n" + "=" * 60)
    print("PIPELINE TERMINÉ")
    print("=" * 60)

if __name__ == "__main__":
    pipeline_complet()
