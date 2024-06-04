import os
import sys
import xxhash
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


def compute_file_hash(file_path:str) -> str:
    hash_obj = xxhash.xxh64()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def scan_directory(directory:str) -> dict:
    file_hashes = {}
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_hashes[file_path] = compute_file_hash(file_path)
    return file_hashes


def save_hashes_to_json(file_hashes, json_file):
    with open(json_file, 'w') as f:
        json.dump(file_hashes, f, indent=4)


def save_hashes_to_json(file_hashes, json_file):
    with open(json_file, 'w') as f:
        json.dump(file_hashes, f, indent=4)


def load_hashes_from_json(json_file: str) -> dict:
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def check_consistency(directory: str, json_file: str) -> bool:
    current_hashes = scan_directory(directory)
    saved_hashes = load_hashes_from_json(json_file)
    
    for file_name, file_hash in current_hashes.items():
        if file_name not in saved_hashes or saved_hashes[file_name] != file_hash:
            return False
    return True


def overwrite_hashes_if_inconsistent(directory: str, json_file: str) -> None:
    current_hashes = scan_directory(directory)
    save_hashes_to_json(current_hashes, json_file)


def main() -> None:
    directory = "videos"
    json_file = "file_hashes.json"
    
    if not check_consistency(directory, json_file):
        overwrite_hashes_if_inconsistent(directory, json_file)
        logging.info(f"Inconsistency found. Data was updated")
    logging.info(f"All files consistent.")


if __name__ == "__main__":
    main()