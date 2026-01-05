# app/graph/build_graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from app.graph.state import NewsState

def ingest_node(state: NewsState) -> NewsState:
    from app.scrapers import run_scrapers
    from app.services.articles_repo import upsert_articles

    hours = state["window_hours"]
    items = run_scrapers.run(hours=hours)
    ids = upsert_articles(items)
    return {"raw_count": len(items), "article_ids": ids}

def extract_node(state: NewsState) -> NewsState:
    from app.services.extract_repo import extract_missing_content
    stats = extract_missing_content(hours=state["window_hours"], batch_size=80)
    return {
        "extraction_stats": stats,
        "extracted_attempted": stats.get("attempted", 0),
    }

def select_node(state: NewsState) -> NewsState:
    from app.services.select_repo import pick_and_mark
    ids = pick_and_mark(hours=state["window_hours"], per_source=5, final_n=10)
    return {"selected_ids": ids}

def build_app():
    g = StateGraph(NewsState)
    g.add_node("ingest", ingest_node)
    g.add_node("extract", extract_node)
    g.add_node("select", select_node)

    g.add_edge(START, "ingest")
    g.add_edge("ingest", "extract")
    g.add_edge("extract", "select")
    g.add_edge("select", END)

    # InMemorySaver is fine for local dev/testing (not production). :contentReference[oaicite:1]{index=1}
    return g.compile(checkpointer=InMemorySaver())
