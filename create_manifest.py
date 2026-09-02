from pathlib import Path
import json
import hashlib
import os

# function for reading the config json ported over
def parse_config_file(config_file_path):
    script_dir = Path(__file__).parent # get the directory of the script file
    config_file_path = script_dir / config_file_path # get the full path to the config file

    with open(config_file_path, "r") as config_file:
        config_data = json.load(config_file)
    return config_data

def iterate_through_local(file_path, remote_base):
    directory = Path(file_path)
    return_dict = {} # returns a dictionary 

    for file in directory.rglob("*"):
        if file.is_file():
            with open(file, "rb") as file_to_hash:
                file_data = file_to_hash.read()

            relative_path = file.relative_to(directory).as_posix()
            full_remote_path = remote_base + "/" + relative_path # full path on the remote

            timestamp = os.path.getmtime(file)
            file_hash = hashlib.sha256(file_data).hexdigest()

            return_dict[full_remote_path] = {
                "timestamp": timestamp,
                "hash": file_hash,
            }

    return return_dict

config_data = parse_config_file("config.json") # grabbing the needed data
emulator_data = config_data["emulators"]

manifest_dictionary = {} # dictionary for the manifest

for emulator_name, emulator_values in emulator_data.items():
    for entry in emulator_values["local_save_path"]:
        manifest_dictionary.update(iterate_through_local(entry["local"], entry["remote"])) # add a key pair value for each entry

with open("manifest.json", "w") as file:
    json.dump(manifest_dictionary, file, indent = 4) # turn the dictionary into a json
    # indent = 4 makes it easier to read

