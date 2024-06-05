import os
import sys
import json
import logging

from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.FileHandler(f"logs/{datetime.now().strftime('%d-%b-%Y %H_%M_%S')}.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


def scan_directory(directory: str) -> list:
    file_names = []
    for _, _, files in os.walk(directory):
        for file in files:            
            file_names.add(file)
    return file_names


def save_names_to_json(file_names: list, json_file: str):
    with open(json_file, 'w') as f:
        json.dump(file_names, f, indent=4)


def load_names_from_json(json_file: str) -> dict:
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def main() -> None:
    directory = "videos"
    json_file = "file_names.json"

    current_names = scan_directory(directory)

    if not check_consistency_file_name_list(current_names, "file_names.json"):
        save_names_to_json(current_names, json_file)
        logging.info(f"Inconsistency found. Data was updated")
    logging.info(f"All files consistent.")

if __name__ == "__main__":
    main()


def check_if_duplicate(file_name: str, name_list: dict) -> bool:
    if file_name in name_list:
        return True
    else:
        return False
    

def check_consistency_file_name_list(current_names: list, json_file: str) -> bool:
    """Checks if all files in video folder present in file"""

    saved_names = load_names_from_json(json_file)

    for file_name in current_names.items():
        if file_name not in saved_names:
            return False
    return True