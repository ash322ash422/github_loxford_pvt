import os
from datetime import datetime
from pydantic import BaseModel, Field
from openai import OpenAI
from database import store_articles
from dotenv import load_dotenv

# 1. Initialize the official OpenAI Client
# It automatically picks up the OPENAI_API_KEY environment variable
load_dotenv()  # Load environment variables from .env file
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# 2. Define the exact JSON structure we want OpenAI to return
class NewsRiskAnalysis(BaseModel):
    risk_score: float = Field(
        description="A risk score between 0.0 (completely safe/positive) \
            and 1.0 (extreme threat/highly negative) based on the headline."
    )

def fetch_live_market_news():
    """
    Simulates fetching fresh headlines from a live financial news source.
    """
    return [
        {"title": "Global Tech Stocks Plunge Amid New Regulatory Scrutiny", "source": "Financial Times"},
        {"title": "Central Bank Announces Surprise Rate Cut, Boosting Market Confidence", "source": "Bloomberg"},
        {"title": "Supply Chain Disruptions Threaten Holiday Sales Forecasts", "source": "Reuters"},
        {"title": "Breakthrough in Renewable Energy Sector Promises Massive Growth", "source": "Eco Times"},
        {"title": "Geopolitical Tensions Escalate in Key Trade Region", "source": "Global News"},
        {"title": "Major Corporation Reports Record-Breaking Quarterly Earnings", "source": "Wall Street Journal"}
    ]

def calculate_openai_risk(headline):
    """
    Sends the headline to OpenAI using Structured Outputs.
    Guarantees a clean float returned with 0 MB local storage required.
    """
    try:
        # We use gpt-4o-mini because it is incredibly fast, cheap, and precise
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial risk analyst. Analyze the provided headline and determine its risk score. 0.0 represents highly positive market news (low risk). 0.5 is neutral. 1.0 represents catastrophic or highly negative news (extreme risk)."
                },
                {"role": "user", "content": headline}
            ],
            response_format=NewsRiskAnalysis, # Enforces the exact Pydantic schema structure
        )
        
        # Extract the structured response object
        analysis = response.choices[0].message.parsed
        return round(analysis.risk_score, 2)

    except Exception as e:
        print(f"❌ OpenAI API Error for '{headline[:20]}...': {e}")
        return 0.5  # Neutral fallback score on connection failure

def run_ingestion_pipeline():
    """
    Orchestrates the OpenAI cloud ETL workflow: Fetch -> LLM Parsing -> SQLite Batch Store.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        print("🔴 ERROR: OPENAI_API_KEY environment variable is missing. Please set it before running.")
        return

    print("🚀 Initializing live news ingestion pipeline via OpenAI API...")
    raw_news = fetch_live_market_news()
    processed_articles = []
    
    for item in raw_news:
        print(f"🧠 Querying OpenAI for headline: '{item['title'][:40]}...'")
        computed_risk = calculate_openai_risk(item["title"])
        print(f"   -> Computed Risk Score: {computed_risk}")
        
        processed_articles.append({
            "title": item["title"],
            "source": item["source"],
            "date": datetime.now(),
            "risk_score": computed_risk
        })
    
    print("processed_articles:", processed_articles) # Debug print to verify the structure before database insertion 
    # Batch insert into your SQLite database
    store_articles(processed_articles)
    print(f"\n✅ Successfully processed and stored {len(processed_articles)} articles into SQLite database.")

if __name__ == "__main__":
    run_ingestion_pipeline()
