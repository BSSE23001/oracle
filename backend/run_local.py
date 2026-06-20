"""
Local test harness for the ORACLE agent graph, run a full research
session from the terminal, including the human-in-the-loop plan review,
without needing the FastAPI layer at all.

Usage:
    cd backend
    source .venv/bin/activate
    python run_local.py "What are the latest approaches to LLM agent evaluation?"

If you omit the query argument you'll be prompted for one interactively.
"""

from __future__ import annotations

import sys
import uuid

from langgraph.types import Command
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from app.agents.graph import get_process_graph
from app.agents.state import initial_state
from app.config import configure_langsmith_env, settings
from app.core.logging_config import configure_logging

console = Console()


def render_plan(plan: dict) -> None:
    table = Table(title="Proposed Research Plan", show_lines=True)
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Type", style="magenta")
    table.add_column("Description")
    table.add_column("Input", style="dim")
    for subtask in plan["subtasks"]:
        table.add_row(
            subtask["id"],
            subtask["type"],
            subtask["description"],
            subtask.get("input_data", "") or "—",
        )
    console.print(
        Panel(
            f"[bold]Objective:[/bold] {plan['objective']}",
            title="Research Plan",
            expand=False,
        )
    )
    console.print(table)


def render_report(report: dict) -> None:
    console.print()
    console.print(Panel(f"[bold]{report['title']}[/bold]", style="green"))
    console.print(Markdown(f"**Summary:** {report['summary']}"))
    console.print(f"[bold]Confidence score:[/bold] {report['confidence_score']:.2f}\n")

    for section in report["sections"]:
        cites = ", ".join(f"[{c}]" for c in section["citation_ids"]) or "(no citations)"
        console.print(
            Panel(Markdown(section["content"]), title=f"{section['heading']}  {cites}")
        )

    if report["citations"]:
        console.print("\n[bold]Citations[/bold]")
        for c in report["citations"]:
            title = c.get("title") or "(untitled)"
            link = c.get("doi") and f"https://doi.org/{c['doi']}" or c.get("url") or ""
            console.print(f"  [{c['id']}] {title} {link}")


def main() -> None:
    configure_logging()
    configure_langsmith_env()

    query = " ".join(sys.argv[1:]).strip() or Prompt.ask("[bold]Research query[/bold]")
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    console.print(f"\n[dim]session_id = {session_id}[/dim]")
    console.print("[bold]Building agent graph...[/bold]")
    graph = get_process_graph()

    console.print("[bold]Running Supervisor agent...[/bold]")
    result = graph.invoke(initial_state(query, session_id), config=config)

    # The supervisor -> human_review loop: keep showing the (possibly
    # revised) plan and asking for approval/feedback until approved.
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        render_plan(payload["plan"])

        approved = Confirm.ask("Approve this plan and run the agents?", default=True)
        decision = {"approved": approved}
        if not approved:
            decision["feedback"] = Prompt.ask("What should change about the plan?")
            console.print("[bold]Revising plan...[/bold]")
        else:
            console.print("[bold]Dispatching specialist agents in parallel...[/bold]")

        result = graph.invoke(Command(resume=decision), config=config)

    console.print("[bold]Synthesizing report and fact-checking...[/bold]")
    report = result.get("report")
    if report is None:
        console.print(
            "[red]No report was produced — check the logs above for errors.[/red]"
        )
        return

    render_report(report.model_dump() if hasattr(report, "model_dump") else report)

    if settings.langsmith_tracing:
        console.print(
            f"\n[dim]Full trace: https://smith.langchain.com/o/-/projects/p/{settings.langsmith_project}[/dim]"
        )


if __name__ == "__main__":
    main()
