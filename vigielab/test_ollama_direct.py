"""
Test direct d'Ollama avec timeout long
"""
import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:4b"

prompt = """
Tu es un analyste de veille technologique. Résume cette publication en français en 2 phrases maximum.
Titre: CERTFR-2026-AVI-1042 : Vulnérabilité critique dans les passerelles VPN
Extrait: Une vulnérabilité de type exécution de code arbitraire à distance (CVSS 9.8) affecte plusieurs implémentations.

Réponds uniquement avec le résumé, sans autre texte.
"""

print(f"Test Ollama avec modèle {MODEL}...")
start = time.time()

try:
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False},
        timeout=300  # 5 minutes
    )
    elapsed = time.time() - start
    print(f"Réponse reçue en {elapsed:.2f}s")
    
    if response.status_code == 200:
        result = response.json()
        summary = result["response"].strip()
        print(f"✓ Succès ! Résumé: {summary}")
    else:
        print(f"✗ Erreur HTTP: {response.status_code}")
        print(response.text)
except Exception as e:
    elapsed = time.time() - start
    print(f"✗ Erreur après {elapsed:.2f}s: {e}")
