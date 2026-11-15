"""
Test de l'intégration Ollama qwen3.5:4b avec VigieLab
"""
import requests
import sqlite3
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:4b"
DB_PATH = Path("veille.db")

def test_ollama_connection():
    """Teste la connexion à Ollama"""
    print("Test de connexion à Ollama...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✓ Ollama connecté. Modèles disponibles: {[m['name'] for m in models]}")
            qwen_available = any("qwen3.5" in m["name"] for m in models)
            if qwen_available:
                print(f"✓ Modèle qwen3.5:4b trouvé")
            else:
                print(f"✗ Modèle qwen3.5:4b NON trouvé")
            return qwen_available
        else:
            print(f"✗ Erreur Ollama: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Impossible de connecter à Ollama: {e}")
        return False

def test_ollama_summary():
    """Teste la génération de résumé avec qwen3.5:4b"""
    print("\nTest de génération de résumé...")
    prompt = """
    Tu es un assistant spécialisé dans la veille technologique.
    Résume l'article suivant en français en 3 à 5 phrases.
    Le résumé doit être clair, précis et professionnel.

    Titre: Une nouvelle avancée en intelligence artificielle
    Contenu: Une entreprise annonce une nouvelle technologie permettant d'améliorer les performances des modèles IA.

    Donne uniquement le résumé.
    """
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        result = response.json()
        summary = result["response"].strip()
        print(f"✓ Résumé généré avec succès:")
        print(f"  {summary}")
        return True
    except Exception as e:
        print(f"✗ Erreur lors de la génération: {e}")
        return False

def check_vigielab_articles():
    """Vérifie les articles dans la base VigieLab"""
    print("\nVérification des articles dans VigieLab...")
    if not DB_PATH.exists():
        print(f"✗ Base de données non trouvée: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM items")
    count = cursor.fetchone()[0]
    print(f"✓ {count} articles dans la base")
    
    cursor.execute("SELECT title, ai_summary, ai_engine FROM items LIMIT 3")
    articles = cursor.fetchall()
    print("\nExemples d'articles:")
    for title, summary, engine in articles:
        print(f"  - {title[:60]}...")
        print(f"    IA: {engine}")
        print(f"    Résumé: {summary[:80] if summary else '(vide)'}...")
        print()
    
    conn.close()
    return True

def main():
    print("=" * 60)
    print("TEST D'INTÉGRATION OLLAMA + VIGIELAB")
    print("=" * 60)
    
    # Test 1: Connexion Ollama
    ollama_ok = test_ollama_connection()
    
    # Test 2: Génération de résumé
    if ollama_ok:
        summary_ok = test_ollama_summary()
    else:
        summary_ok = False
    
    # Test 3: Articles VigieLab
    articles_ok = check_vigielab_articles()
    
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)
    print(f"Connexion Ollama: {'✓ OK' if ollama_ok else '✗ ÉCHEC'}")
    print(f"Génération résumé: {'✓ OK' if summary_ok else '✗ ÉCHEC'}")
    print(f"Articles VigieLab: {'✓ OK' if articles_ok else '✗ ÉCHEC'}")
    
    if ollama_ok and summary_ok and articles_ok:
        print("\n✓ TOUS LES TESTS RÉUSSIS - Intégration fonctionnelle !")
    else:
        print("\n✗ CERTAINS TESTS ONT ÉCHOUÉ - Vérifiez la configuration")

if __name__ == "__main__":
    main()
