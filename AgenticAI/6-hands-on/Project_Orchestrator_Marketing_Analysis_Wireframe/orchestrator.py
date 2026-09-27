from agents.data_agent import DataAgent
from agents.analytics_agent import AnalyticsAgent
from agents.copilot_agent import CopilotAgent


class Orchestrator:
    """
    THE ORCHESTRATOR
    -----------------
    This is the "manager" of the agent team. It does not do any data
    work itself -- it only decides WHICH agent runs WHEN, and passes
    the output of one agent as the input to the next.

    Pipeline:
        DataAgent  --->  AnalyticsAgent  --->  CopilotAgent

    It also makes ONE small decision of its own: if every channel is
    losing money, it escalates the urgency of the final report. This
    shows students that orchestration is not just "call things in
    order" -- the orchestrator can branch based on what the agents find.
    """

    def __init__(self, csv_path, use_llm=False):
        self.data_agent = DataAgent(csv_path)
        self.analytics_agent = AnalyticsAgent()
        self.copilot_agent = CopilotAgent(use_llm=use_llm)

    def run(self):
        print("\n--- ORCHESTRATOR: starting pipeline ---\n")

        # Step 1: get the raw data
        data_output = self.data_agent.run()

        # Step 2: turn raw data into KPIs
        kpi_report = self.analytics_agent.run(data_output)

        # Orchestrator-level decision (a bit of branching logic)
        all_losing_money = all(kpi["roas"] < 1 for kpi in kpi_report.values())
        if all_losing_money:
            print("[Orchestrator] ALERT: every channel is losing money! Escalating priority.")

        # Step 3: turn KPIs into a decision-support report
        final_report = self.copilot_agent.run(kpi_report)

        print("\n--- ORCHESTRATOR: pipeline complete ---\n")

        if all_losing_money:
            final_report = "*** URGENT REVIEW NEEDED ***\n\n" + final_report

        return final_report
