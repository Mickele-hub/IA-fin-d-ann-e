
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from ai.summarization import summarize_article
from database.database import initialize_database, insert_article


def process_articles():
    initialize_database()

    with open(
        "datasets/sample_articles.json",
        "r",
        encoding="utf-8"
    ) as file:
        articles = json.load(file)

    for article in articles:
        print("Traitement :", article["title"])

        summary = summarize_article(
            article["title"],
            article.get("description", "")
        )

        if summary:
            article["summary"] = summary
            insert_article(article)
            print("Article enregistré !")


if __name__ == "__main__":
    process_articles()
