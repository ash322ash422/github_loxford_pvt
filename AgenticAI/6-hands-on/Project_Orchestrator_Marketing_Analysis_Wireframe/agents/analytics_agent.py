from collections import defaultdict


class AnalyticsAgent:
    """
    AGENT 2 : ANALYTICS AGENT
    --------------------------
    Job: turn raw rows of numbers into the KPIs a marketer actually cares
    about, grouped by channel, and stack them up against the industry
    benchmarks the DataAgent fetched.

    KPIs computed:
        CTR  (Click Through Rate)   = clicks / impressions
        CPC  (Cost Per Click)       = spend / clicks
        CPA  (Cost Per Acquisition) = spend / conversions
        ROAS (Return On Ad Spend)   = revenue / spend

    This is the "analytics workflow" piece of the project: a pure
    data-transformation step with no side effects and no external calls.
    """

    def run(self, data_agent_output):
        rows = data_agent_output["campaign_data"]
        benchmarks = data_agent_output["benchmarks"]

        totals = defaultdict(lambda: {
            "impressions": 0, "clicks": 0, "spend": 0.0,
            "conversions": 0, "revenue": 0.0,
        })

        for r in rows:
            t = totals[r["channel"]]
            t["impressions"] += r["impressions"]
            t["clicks"] += r["clicks"]
            t["spend"] += r["spend"]
            t["conversions"] += r["conversions"]
            t["revenue"] += r["revenue"]

        report = {}
        for channel, t in totals.items():
            ctr = t["clicks"] / t["impressions"] if t["impressions"] else 0
            cpc = t["spend"] / t["clicks"] if t["clicks"] else 0
            cpa = t["spend"] / t["conversions"] if t["conversions"] else 0
            roas = t["revenue"] / t["spend"] if t["spend"] else 0

            bench = benchmarks.get(channel, {})
            report[channel] = {
                "ctr": round(ctr, 4),
                "cpc": round(cpc, 2),
                "cpa": round(cpa, 2),
                "roas": round(roas, 2),
                "spend": round(t["spend"], 2),
                "revenue": round(t["revenue"], 2),
                "benchmark_ctr": bench.get("ctr"),
                "benchmark_cpa": bench.get("cpa"),
            }

        print(f"[AnalyticsAgent] Computed KPIs for {len(report)} channels")
        return report
