# scripts/extract_once.py
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.extract_repo import extract_missing_content

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    load_dotenv()
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    print(f"\n{'='*60}")
    print(f"Content Extraction - Last {hours} hours (batch={batch_size})")
    print(f"{'='*60}\n")

    result = extract_missing_content(hours=hours, batch_size=batch_size)

    print(f"\n{'='*60}")
    print("RESULTS:")
    print(f"  Attempted: {result['attempted']}")
    print(f"  Succeeded: {result['succeeded']} ✓")
    print(f"  Failed:    {result['failed']} ✗")

    if result['attempted'] > 0:
        success_rate = (result['succeeded'] / result['attempted']) * 100
        print(f"  Success rate: {success_rate:.1f}%")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
