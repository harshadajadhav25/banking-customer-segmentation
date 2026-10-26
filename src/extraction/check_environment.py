from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


EXPECTED_FILES = {
    "account.asc",
    "card.asc",
    "client.asc",
    "disp.asc",
    "district.asc",
    "loan.asc",
    "order.asc",
    "trans.asc",
}


def main() -> int:
    load_dotenv()
    raw_directory = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
    found_files = {path.name for path in raw_directory.glob("*.asc")}
    missing_files = sorted(EXPECTED_FILES - found_files)

    print(f"Raw data directory: {raw_directory.resolve()}")
    print(f"Found {len(found_files)} of {len(EXPECTED_FILES)} expected source files.")

    if missing_files:
        print("Missing files:")
        for filename in missing_files:
            print(f"- {filename}")
        return 1

    print("Environment and source file check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

