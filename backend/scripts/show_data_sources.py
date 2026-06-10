from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ingestion.source_registry import DATA_SOURCES


def main():
    print("AWA Intelligence Platform data sources")
    print("--------------------------------------")

    for source in DATA_SOURCES:
        print("Source:", source["display_name"])
        print("Internal name:", source["source_name"])
        print("Type:", source["source_type"])
        print("Base URL:", source["base_url"])
        print("Access method:", source["access_method"])
        print("Priority:", source["priority"])
        print("Record types:")

        for record_type in source["record_types"]:
            print(" -", record_type)

        print("Notes:", source["notes"])
        print("--------------------------------------")


if __name__ == "__main__":
    main()