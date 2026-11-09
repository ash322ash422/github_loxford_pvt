import csv

class DataAgent:
    """
    AGENT 1 : DATA AGENT
    ---------------------
    Job: collect raw information from TWO different sources and package
    it up for the next agent. This is the "combining APIs and databases"
    part of the project.

        1. A "database"  -> a CSV file of daily campaign performance
        2. An "API"       -> a mock external service returning industry
                             benchmark numbers (what a "good" CTR/CPA looks
                             like for each channel)

    In a real company, source #1 might be a SQL database and source #2
    might be a live call to Google Ads / Meta's API. We fake both here
    so the project runs instantly with no accounts or API keys.
    """

    def __init__(self, csv_path):
        self.csv_path = csv_path

    # ---- talks to the "database" ----
    def fetch_campaign_data(self):
        rows = []
        with open(self.csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({
                    "date": row["date"],
                    "channel": row["channel"],
                    "campaign": row["campaign"],
                    "impressions": int(row["impressions"]),
                    "clicks": int(row["clicks"]),
                    "spend": float(row["spend"]),
                    "conversions": int(row["conversions"]),
                    "revenue": float(row["revenue"]),
                })
        return rows

    # ---- talks to the "API" ----
    def fetch_industry_benchmarks(self):
        """
        Pretend external API. A real version might be:
            requests.get("https://api.adbenchmarks.com/v1/ctr").json()
        We hardcode realistic numbers so the project needs no internet
        access or API key to run.
        """
        return {
            "Google Search": {"ctr": 0.035, "cpa": 18.0},
            "Facebook":      {"ctr": 0.020, "cpa": 22.0},
            "Instagram":     {"ctr": 0.015, "cpa": 25.0},
        }

    def run(self):
        print("[DataAgent] Reading campaign data from database (CSV)...")
        campaign_data = self.fetch_campaign_data()
        print(f"[DataAgent]   -> loaded {len(campaign_data)} rows")

        print("[DataAgent] Calling external benchmark API...")
        benchmarks = self.fetch_industry_benchmarks()
        print(f"[DataAgent]   -> retrieved benchmarks for {len(benchmarks)} channels")

        return {"campaign_data": campaign_data, "benchmarks": benchmarks}
