import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

def get_news_article_sentiment(ticker, num_articles=4):
    
    # params = {
    #     "function": "NEWS_SENTIMENT",
    #     "tickers": ticker,
    #     "apikey": API_KEY
    # }

    # response = requests.get(
    #     "https://www.alphavantage.co/query",
    #     params=params
    # )

    # response.raise_for_status()
    # data = response.json()
    # articles = []

    # for article in data.get("feed", [])[:num_articles]:
    #     articles.append({
    #         "title": article.get("title"),
    #         "published": article.get("time_published"),
    #         "summary": article.get("summary"),
    #         "url": article.get("url"),
    #         "sentiment": article.get("overall_sentiment_score")
    #     })

    # return pd.DataFrame(articles)
    
    # Comment out this part to avoid making API calls during testing, and read from the CSV instead
    df = pd.read_csv("ibm_news_article_sentiment.csv")
    return df


# df = get_news_article_sentiment("IBM")
# print(df)
# df.to_csv("ibm_news_article_sentiment.csv", index=False)

if __name__ == "__main__":
    df = get_news_article_sentiment("IBM")
    print(df)