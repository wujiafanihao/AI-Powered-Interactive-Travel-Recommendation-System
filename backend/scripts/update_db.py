import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "travel.db")

def update():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS spot_comments (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        spot_id         INTEGER NOT NULL,
        rating          REAL    NOT NULL CHECK(rating >= 1 AND rating <= 5),
        content         TEXT    NOT NULL,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (spot_id) REFERENCES spots(id)
    );
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_spot ON spot_comments(spot_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_user ON spot_comments(user_id);")
    
    conn.commit()
    conn.close()
    print("Database updated successfully!")

if __name__ == "__main__":
    update()
