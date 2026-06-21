from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Send

from app.agents.graph import _route_after_human_review, build_graph
from app.agents.schemas import ResearchPlan, Subtask, SubtaskType


def test_graph_compiles_with_in_memory_checkpointer():
    graph = build_graph(checkpointer=InMemorySaver())
    node_names = set(graph.get_graph().nodes.keys())
    assert {
        "supervisor",
        "human_review",
        "web_search_agent",
        "pdf_agent",
        "code_exec_agent",
        "fact_check_subtask_agent",
        "synthesis_agent",
        "fact_check_pass",
        "citation_formatter",
    }.issubset(node_names)


def test_route_after_human_review_not_approved_loops_to_supervisor():
    state = {"plan_approved": False, "plan": ResearchPlan(objective="x", subtasks=[])}
    assert _route_after_human_review(state) == "supervisor"


def test_route_after_human_review_approved_fans_out_one_send_per_subtask():
    plan = ResearchPlan(
        objective="x",
        subtasks=[
            Subtask(id="t1", type=SubtaskType.WEB_SEARCH, description="search something", input_data=""),
            Subtask(id="t2", type=SubtaskType.CODE_EXEC, description="compute something", input_data=""),
        ],
    )
    state = {"plan_approved": True, "plan": plan, "session_id": "sess-123"}
    result = _route_after_human_review(state)

    assert len(result) == 2
    assert all(isinstance(s, Send) for s in result)
    assert result[0].node == "web_search_agent"
    assert result[1].node == "code_exec_agent"
    assert result[0].arg["session_id"] == "sess-123"
    assert result[0].arg["subtask"]["id"] == "t1"
