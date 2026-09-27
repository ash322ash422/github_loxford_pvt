import sqlite3
import pandas as pd

DB_NAME = "business.db"

def run_query(sql_query):

    try:

        conn = sqlite3.connect(DB_NAME)

        df = pd.read_sql_query(sql_query, conn)

        conn.close()

        return df

    except Exception as e:

        return str(e)