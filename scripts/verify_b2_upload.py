import os
import sys
from pathlib import Path
import tempfile
import json

# Ensure project root is on sys.path so `storage` package can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from storage.b2 import upload_file


def main():
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as handle:
        handle.write("MatchCast B2 verification payload")
        temp_path = handle.name

    try:
        print("Attempting B2 upload...")
        result = upload_file(temp_path, "verify-b2-test", "verify.txt")
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(f"B2 upload failed: {exc}")
        raise
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    main()
