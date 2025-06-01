import sqlite3

CHEMIN_BDD = "le_chemin_du_repertoire_de_votre_bdd_sqlite/stats_youtube.sqlite"

with sqlite3.connect(CHEMIN_BDD) as conn:
    cur = conn.cursor()
    # Création de la table des commentaires
    cur.execute("""
        CREATE TABLE IF NOT EXISTS youtube_stats (
            date           TEXT,
            likes_video    INTEGER,
            vues_video     INTEGER,
            commentaire    TEXT,
            auteur         TEXT,
            UNIQUE(date, commentaire, auteur)
        );
    """)
    # Création de la table de l’historique
    cur.execute("""
        CREATE TABLE IF NOT EXISTS youtube_historique (
            date             TEXT PRIMARY KEY,
            likes_video      INTEGER,
            vues_video       INTEGER,
            nb_commentaires  INTEGER
        );
    """)
    conn.commit()
print("Base SQLite initialisée avec succès.")
