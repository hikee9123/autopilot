import json


def read_json_file(file_path):
    json_object = {}

    with open(file_path, 'r') as file:
        json_str = file.read()

    if not json_str:
        return json_object

    try:
        json_object = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Failed to parse the JSON document: {file_path}")
        print(e)
    
    return json_object

