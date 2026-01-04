# scripts/select_top.py
import sys
from dotenv import load_dotenv
from app.services.select_repo import pick_and_mark

def main():
    load_dotenv()
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    ids = pick_and_mark(hours=hours, per_source=5, final_n=10)
    print(f"selected={len(ids)} ids={ids}")

if __name__ == "__main__":
    main()
