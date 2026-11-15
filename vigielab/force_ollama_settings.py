"""
Force VigieLab settings to use Ollama qwen3.5:4b
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("veille.db")

def update_settings():
    """Met à jour les settings pour forcer l'utilisation d'Ollama"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Afficher les settings actuels
    print("Settings actuels:")
    cursor.execute("SELECT key, value FROM settings")
    for key, value in cursor.fetchall():
        print(f"  {key}: {value}")
    
    # Mettre à jour les settings
    updates = {
        "ollamaEndpoint": "http://localhost:11434",
        "ollamaModel": "qwen3.5:4b",
        "preferLocalOllama": "true"
    }
    
    print("\nMise à jour des settings...")
    for key, value in updates.items():
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (key, value))
        print(f"  {key} = {value}")
    
    conn.commit()
    
    # Vérifier les nouveaux settings
    print("\nNouveaux settings:")
    cursor.execute("SELECT key, value FROM settings")
    for key, value in cursor.fetchall():
        print(f"  {key}: {value}")
    
    conn.close()
    print("\n✓ Settings mis à jour avec succès")

if __name__ == "__main__":
    update_settings()
