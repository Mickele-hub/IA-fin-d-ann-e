
import sqlite3

DB_PATH = "database/veille.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    connection = get_connection()

    with open("database/schema.sql", "r", encoding="utf-8") as file:
        schema = file.read()

    connection.executescript(schema)
    connection.commit()
    connection.close()


def insert_article(article):
    connection = get_connection()

    query = """
    INSERT OR IGNORE INTO articles
    (title, description, link, source,
     published_at, category, summary)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    connection.execute(query, (
        article["title"],
        article.get("description", ""),
        article["link"],
        article.get("source", ""),
        article.get("published_at", ""),
        article.get("category", ""),
        article.get("summary", "")
    ))

    connection.commit()
    connection.close()


def get_all_articles():
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    cursor = connection.execute(
        "SELECT * FROM articles ORDER BY published_at DESC"
    )

    articles = [dict(row) for row in cursor.fetchall()]
    connection.close()

    return articles


if __name__ == "__main__":
    initialize_database()
    print("Base de données initialisée !")
