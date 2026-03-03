# load JSON from Flatland Drawing Tool
import json


def load_json(name: str) -> dict:
    with open(name + '.json' if not name.endswith(".json") else name, 'r') as f:
        data = json.load(f)
    return data
