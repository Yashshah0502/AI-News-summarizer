# scripts/cleanup_once.py
from dotenv import load_dotenv
from app.services.cleanup_repo import cleanup_older_than

def main():
    load_dotenv()
    print(cleanup_older_than(18))

if __name__ == "__main__":
    main()
