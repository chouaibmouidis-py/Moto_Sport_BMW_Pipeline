import argparse
import json
from pathlib import Path

from download import RAW_DIR, SOURCE_FILENAME


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a locally downloaded IMSA source.")
    parser.add_argument("path", nargs="?", type=Path, default=Path(RAW_DIR) / SOURCE_FILENAME)
    args = parser.parse_args()

    with args.path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)

    cars = data["pit_stop_analysis"]
    print("event_name:", data["session"]["event_name"])
    print("session_name:", data["session"]["session_name"])
    print("Number of cars:", len(cars))

    for car in cars:
        if car["manufacturer"] == "BMW":
            print("Team:", car["team"])
            print("Car number:", car["number"])


if __name__ == "__main__":
    main()
