
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:4b"


def summarize_article(title, description):
    prompt = f"""
    Tu es un assistant spécialisé dans la veille technologique.

    Résume l'article suivant en français en 3 à 5 phrases.
    Le résumé doit être clair, précis et professionnel.

    Titre : {title}

    Contenu :
    {description}

    Donne uniquement le résumé.
    """

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=180
        )

        response.raise_for_status()

        result = response.json()
        return result["response"].strip()

    except requests.RequestException as error:
        print("Erreur Ollama :", error)
        return None


if __name__ == "__main__":
    title = "Une nouvelle avancée en intelligence artificielle"
    description = """
    Une entreprise annonce une nouvelle technologie
    permettant d'améliorer les performances des modèles IA.
    """

    summary = summarize_article(title, description)
    print("Résumé :", summary)
