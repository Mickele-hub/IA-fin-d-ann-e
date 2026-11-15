"""
Test de l'API VigieLab pour régénérer un résumé avec Ollama
"""
import requests
import json

API_URL = "http://localhost:3000"

def test_api_collect():
    """Lance une collecte via l'API VigieLab"""
    print("Test de collecte via API VigieLab...")
    
    # Récupérer un article pour tester
    response = requests.get(f"{API_URL}/api/items?limit=1")
    if response.status_code != 200:
        print(f"✗ Erreur récupération articles: {response.status_code}")
        return False
    
    data = response.json()
    items = data.get("items", [])
    if not items:
        print("✗ Aucun article trouvé")
        return False
    
    item = items[0]
    item_id = item["id"]
    print(f"Article trouvé: {item['title'][:60]}...")
    print(f"ID: {item_id}")
    print(f"Moteur IA actuel: {item.get('aiEngine', 'N/A')}")
    
    # Régénérer le résumé avec Ollama
    print(f"\nRégénération du résumé avec Ollama...")
    response = requests.post(f"{API_URL}/api/items/{item_id}/resummarize")
    
    if response.status_code != 200:
        print(f"✗ Erreur régénération: {response.status_code}")
        print(f"  {response.text}")
        return False
    
    result = response.json()
    updated_item = result.get("item", {})
    print(f"✓ Résumé régénéré avec succès")
    print(f"  Nouveau moteur IA: {updated_item.get('aiEngine', 'N/A')}")
    print(f"  Nouveau résumé: {updated_item.get('aiSummary', '')[:100]}...")
    
    return True

def main():
    print("=" * 60)
    print("TEST API VIGIELAB - RÉGÉNÉRATION AVEC OLLAMA")
    print("=" * 60)
    
    success = test_api_collect()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ TEST RÉUSSI - VigieLab utilise bien Ollama")
    else:
        print("✗ TEST ÉCHOUÉ - Vérifiez que le serveur tourne")

if __name__ == "__main__":
    main()
