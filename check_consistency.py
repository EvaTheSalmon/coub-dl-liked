import os
import sys
import json
import logging
from datetime import datetime

class DirectoryScanner:
    def __init__(self):
        self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
            handlers=[
                logging.FileHandler(f"logs/{datetime.now().strftime('%d-%b-%Y %H_%M_%S')}.log"),
                logging.StreamHandler(sys.stdout),
            ],
        )

    def load_names_from_directory(self, directory: str) -> dict:
        file_names = {}
        for _, _, files in os.walk(directory):
            for file in files:
                file_names.add(file)
        return file_names

    def load_names_from_json(self, json_file: str) -> dict:
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                try:
                    return set(json.load(f))
                except json.JSONDecodeError:
                    return {}
        return {}
        
    def compare_json_and_file_structure(self, json_data: dict, directory_structure_data: dict) -> bool:
        return not bool(json_data - directory_structure_data)
    
    def check_if_file_in_json(self, file_name: str, json_dat: dict) -> bool:
        if file_name in json_data:
            return True
        else:
            return False
    
    def save_names_to_json(self, file_names: dict, json_path: str) -> None:
        with open(json_path, 'w') as f:
            json.dump(file_names, f, indent=4)


if __name__ == "__main__":
    scanner = DirectoryScanner()
    
    directory_structure_data = scanner.load_names_from_directory("videos")
    json_data                = scanner.load_names_from_json("videos_dump.json")

    if scanner.compare_json_and_file_structure(json_data, directory_structure_data):
        logging.info("Data is consistent")
    else:
        scanner.save_names_to_json(directory_structure_data, "videos_dump.json")
        logging.info("Inconsitency found, data was updated")
