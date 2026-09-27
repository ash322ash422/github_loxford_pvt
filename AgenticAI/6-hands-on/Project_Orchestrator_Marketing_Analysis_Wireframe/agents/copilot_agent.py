class CopilotAgent:
    """
    AGENT 3 : COPILOT AGENT (decision support)
    --------------------------------------------
    Job: turn a table of KPIs into a plain-English recommendation a
    marketing manager could act on tomorrow morning. This is the
    "AI copilot for decision support" piece of the project.

    Two modes are supported:
      1. RULE-BASED (default) -> always works, no API key needed.
         Good for grading / classroom demos / offline use.
      2. LLM MODE (use_llm=True) -> calls a real Claude model to write
         a more natural executive summary. This is an optional
         extension exercise for students who want to go further.
    """

    def __init__(self, use_llm=False):
        self.use_llm = use_llm

    def run(self, kpi_report):
        bullet_points = self._build_findings(kpi_report)

        if self.use_llm:
            return self._llm_summary(bullet_points)
        return self._rule_based_summary(bullet_points)

    # ---- step 1: turn KPIs into structured findings (rule-based reasoning) ----
    def _build_findings(self, kpi_report):
        lines = []
        for channel, kpi in kpi_report.items():
            notes = []

            if kpi["benchmark_ctr"] and kpi["ctr"] < kpi["benchmark_ctr"]:
                notes.append(
                    f"CTR ({kpi['ctr']:.2%}) is below the industry benchmark ({kpi['benchmark_ctr']:.2%})"
                )
            if kpi["benchmark_cpa"] and kpi["cpa"] > kpi["benchmark_cpa"]:
                notes.append(
                    f"CPA (${kpi['cpa']}) is worse than benchmark (${kpi['benchmark_cpa']})"
                )
            if kpi["roas"] < 1:
                notes.append("this channel is LOSING money (ROAS below 1.0)")
            elif kpi["roas"] >= 3:
                notes.append("this channel is highly profitable (ROAS >= 3.0)")

            if not notes:
                verdict = "MAINTAIN"
                notes_text = "performing in line with expectations"
            elif kpi["roas"] < 1:
                verdict = "REDUCE budget"
                notes_text = "; ".join(notes)
            elif kpi["roas"] >= 3:
                verdict = "INCREASE budget"
                notes_text = "; ".join(notes)
            else:
                verdict = "MONITOR"
                notes_text = "; ".join(notes)

            lines.append(f"- {channel}: {notes_text}. Suggested action: {verdict}.")

        return "\n".join(lines)

    # ---- mode 1: rule-based summary, no API key needed ----
    def _rule_based_summary(self, bullet_points):
        header = "MARKETING CAMPAIGN ANALYSIS - DECISION SUPPORT REPORT\n" + "=" * 55
        return f"{header}\n{bullet_points}\n"

    # ---- mode 2 (optional extension): real LLM call ----
        # ---- mode 2 (optional extension): real LLM call ----
    def _llm_summary(self, bullet_points):
        """
        Sends the rule-based findings to a real OpenAI model and asks it to write a short,
        natural executive summary with a recommendation. Requires the `openai` package and 
        an OPENAI_API_KEY environment variable. Falls back gracefully if either is missing, 
        so the project never crashes for students without a key.
        """
        try:
            import openai
            client = openai.OpenAI() # reads OPENAI_API_KEY from env
            
            prompt = (
                "You are a marketing analytics copilot. Based on these KPI "
                "findings, write a short executive summary (5 sentences max) "
                "with a clear recommendation:\n\n" + bullet_points
            )
            
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[CopilotAgent] LLM call unavailable ({e}). Falling back to rule-based summary.")
            return self._rule_based_summary(bullet_points)
