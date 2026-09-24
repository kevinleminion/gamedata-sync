# Command to manually grab savedata from the remote
# Not too important for the most part, mostly in the case that the script fails for whatever reason
# NOTE: Relies on the remote being up to date
from pathlib import Path
from azure.storage.fileshare import ShareClient
import json

# turns a config into a working dictionary
def parse_config_file(config_file_path):
    script_dir = Path(__file__).parent # get the directory of the script file
    config_file_path = script_dir / config_file_path # get the full path to the config file

    with open(config_file_path, "r") as config_file:
        config_data = json.load(config_file)
    return config_data

# functions ported over from main script
def retrieve_data(azure_connection, target_file, local_to_write):
    try:
        file_client = azure_connection.get_file_client(target_file)

        with open(local_to_write, "wb") as source_file: # open a file to write the remote data from
            data = file_client.download_file() # download the file
            data.readinto(source_file) # writes into source_file
        return True
        
    except Exception:
        return False 

# function to go through each folder on the remote
def iterate_through_remote(azure_connection, remote_path, local_path):
    # needs to take the current path to determine where to write the file
    directory_handle = azure_connection.get_directory_client(remote_path) # start at the root of the directory

    for entry in directory_handle.list_directories_and_files():
        if entry["is_directory"]:
            Path(local_path + "/" + entry["name"]).mkdir(parents = True, exist_ok = True) # create the matching path on the local device
            iterate_through_remote(azure_connection, remote_path + "/" + entry["name"], local_path + "/" + entry["name"])
            # important to also include a local directory to write to
        else:
            retrieve_data(azure_connection, remote_path + "/" + entry["name"], local_path + "/" + entry["name"])

config_file = parse_config_file("config.json") # read the config file 

connection_string = config_file["connection_string"] # your connection string goes here, private information, do not share it with anyone
share_name = config_file["share_name"]  # name of the Azure File Share
emulator_list = config_file["emulators"] # nested dictionary of emulator data

azure_connection = ShareClient.from_connection_string(connection_string, share_name) # connect to azure

for dictionary_keys, dictionary_values in emulator_list.items():
    for entry in dictionary_values["local_save_path"]: # iterate through the list 
        iterate_through_remote(azure_connection, entry["remote"], entry["local"])
