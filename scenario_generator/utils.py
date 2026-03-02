# load JSON from Flatland Drawing Tool
import json


def load_json(name: str) -> dict:
    with open(name + '.json' if not name.endswith(".json") else name, 'r') as f:
        data = json.load(f)
    return data


# get consecutive line names by numbering
def get_new_name(name: str, i: int) -> str:
    prefix, suffix = name.rsplit('.', 1)
    new_name = f'{prefix}.{int(suffix) + i}'
    return new_name
