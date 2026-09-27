from get_articles import get_news_article_sentiment
from find_risk_score import run_ingestion_pipeline
import subprocess

get_news_article_sentiment(ticker="IBM")
run_ingestion_pipeline()

subprocess.run(["streamlit", "run", "app.py"])