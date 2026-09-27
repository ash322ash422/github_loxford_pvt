import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_NAME = "news_risk.db"

def init_db():
    """Initializes the database and creates the articles table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            date TEXT NOT NULL,
            risk_score REAL NOT NULL
        )
    """ 
    cursor.execute(create_table_sql)
    conn.commit()
    conn.close()

def store_articles(articles_list):
    """
    Stores a list of dictionaries (articles) into the SQLite database using batch insertion.
    Accepts: list of dicts with 'title', 'source', 'date', 'risk_score'
    """
    init_db()  # Ensure table exists

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Define the SQL query clearly outside the data processing loop
    insert_stmt = """
        INSERT INTO articles (title, source, date, risk_score)
        VALUES (?, ?, ?, ?)
    """
    
    # 2. Process all articles into a list of tuples matching the ? placeholders
    batch_data = []
    for art in articles_list:
        date_str = art["date"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(art["date"], datetime) else art["date"]
        
        # Bundle each article into a tuple
        article_tuple = (art["title"], art["source"], date_str, art["risk_score"])
        batch_data.append(article_tuple)
        
    # 3. Execute all insertions simultaneously in one single database call
    cursor.executemany(insert_stmt, batch_data)
    
    conn.commit()
    conn.close()

# --- Script to Seed Mock Data Initially ---
if __name__ == "__main__":
    
    # This block runs ONLY when you execute `python create_database.py` directly to populate your DB
    mock_articles = [
        {"title": "Global Tech Stocks Plunge Amid New Regulatory Scrutiny", 
         "source": "Financial Times", 
         "date": datetime.now() - timedelta(hours=1), 
         "risk_score": 0.8},
        
        {"title": "Central Bank Announces Surprise Rate Cut, Boosting Market Confidence", 
         "source": "Bloomberg", 
         "date": datetime.now() - timedelta(hours=2), 
         "risk_score": 0.3},
        
        {"title": "Supply Chain Disruptions Threaten Holiday Sales Forecasts", 
         "source": "Reuters", 
         "date": datetime.now() - timedelta(hours=3), 
         "risk_score": 0.6},
        
        {"title": "Breakthrough in Renewable Energy Sector Promises Massive Growth", 
         "source": "Eco Times", 
         "date": datetime.now() - timedelta(hours=4), 
         "risk_score": 0.2},
        
        {"title": "Geopolitical Tensions Escalate in Key Trade Region", 
         "source": "Global News", 
         "date": datetime.now() - timedelta(hours=5), 
         "risk_score": 0.9},
        
        {"title": "Major Corporation Reports Record-Breaking Quarterly Earnings", 
         "source": "Wall Street Journal",
         "date": datetime.now() - timedelta(hours=6), 
         "risk_score": 0.1},
    ]
    
    store_articles(mock_articles)
    print("Database initialized and populated with mock articles successfully!")
