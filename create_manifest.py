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

def iterate_through_local(file_path):
    directory = Path(file_path)
    return_list = [] # returns a list 

    for file in directory.rglob("*"):
        if file.is_file():
            with open(file, "rb") as file_to_hash:
                file_data = file_to_hash.read()
    
            relative_path = str(file.relative_to(directory).as_posix()) # get the relative path, NEEDS to be a string
            timestamp = os.path.getmtime(file) # timestamp the file
            file_hash = hashlib.sha256(file_data).hexdigest() # hash the file, then turn it into a string

            entry = {relative_path: [timestamp, file_hash]} # make a dictionary 
            return_list.append(entry)

    return return_list

config_data = parse_config_file("config.json") # grabbing the needed data
emulator_data = config_data["emulators"]

manifest_dictionary = {"data_entries": []} # initial dictionary to create the manifest

for emulator_name, emulator_values in emulator_data.items():
    for entry in emulator_values["local_save_path"]:
        manifest_dictionary["data_entries"].extend(iterate_through_local(entry["local"])) # extend to add each individual list item 

with open("manifest.json", "w") as file:
    json.dump(manifest_dictionary, file, indent = 4) # turn the dictionary into a json
    # indent = 4 makes it easier to read

