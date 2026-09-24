# Command to manually push savedata to the remote
# Not too important for the most part, mostly in the case that the script fails for whatever reason
# NOTE: Relies on the local having an up-to-date manifest file
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

# pushes everything in the "to-monitor" folders to Azure
def push_to_remote(azure_connection, emulator_dictionary):       
    for entry_name, entry_details in emulator_dictionary.items():
        file_path_dict = entry_details["local_save_path"] # each value is a list of dictionaries

        for list_item in file_path_dict: # print every item in the directory 
            loop_through_directory(list_item["local"], list_item["remote"], azure_connection) 

# function to make sure a certain filepath exists before writing
def create_remote_path(azure_connection, remote_path):
    parts = remote_path.split("/")
    current_path = "" # build up the directories bit by bit

    for part in parts:
        if current_path == "": # only necessary for first part as we don't need the '/'
            current_path = current_path + part
        else:
            current_path = current_path + "/" + part # otherwise simply append each part whilst including the '/'

        azure_directory = azure_connection.get_directory_client(current_path) # use to grab a client handle
        try:
            azure_directory.create_directory() # use the client handle to create a path
        except Exception:
            pass

# given all the folder paths from the JSON
# loop through the directories associated with said paths
def loop_through_directory(emulator_path, remote_path, azure_connection):
    folder = Path(emulator_path) # convert the string text to an actual path

    for file in folder.rglob("*"): # just print every item for now
        if file.is_file(): 
            full_remote_path = remote_path + "/" + file.relative_to(emulator_path).as_posix()
            relative_path = file.relative_to(emulator_path) 
            remote_folder_only = remote_path + "/" + relative_path.parent.as_posix() # CRITICAL: excludes the file itself, as that shouldn't be a directory
            # .relative_to() is important here because it filters out only the important paths
            # as_posix() forces the Path object to render with FORWARD slashes, not back slashes.
            create_remote_path(azure_connection, remote_folder_only)
            upload_data(azure_connection, full_remote_path, file) # test uploading the data

# uploading data to Azure
def upload_data(azure_connection, target_file, to_write):
    file_client = azure_connection.get_file_client(target_file) # connect to the target file 

    with open(to_write, "rb") as write_file:
        file_client.upload_file(write_file)

config_file = parse_config_file("config.json") # read the config file 

connection_string = config_file["connection_string"] # your connection string goes here, private information, do not share it with anyone
share_name = config_file["share_name"]  # name of the Azure File Share
emulator_list = config_file["emulators"] # nested dictionary of emulator data

azure_connection = ShareClient.from_connection_string(connection_string, share_name) # connect to azure

for dictionary_keys, dictionary_values in emulator_list.items():
    for entry in dictionary_values["local_save_path"]: # iterate through the list 
        loop_through_directory(entry["local"], entry["remote"], azure_connection)