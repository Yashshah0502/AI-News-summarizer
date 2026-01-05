# scripts/run_graph.py
import sys
from dotenv import load_dotenv
from app.graph.build_graph import build_app

def main():
    load_dotenv()
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    app = build_app()
    out = app.invoke(
        {"window_hours": hours},
        config={"configurable": {"thread_id": f"news-{hours}h"}},  # checkpoints stored per thread :contentReference[oaicite:2]{index=2}
    )
    print(out)

if __name__ == "__main__":
    main()
