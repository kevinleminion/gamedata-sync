# this file is for testing the functionality of certain features before they are appended to the main script file
from pathlib import Path # turns a directory into an object you can iterate through
from concurrent.futures import ThreadPoolExecutor # allows for the use of threads, so you can call functions non-sequentially
import hashlib # allows you to hash files, nothing major
import psutil # mandatory for checking for open processes
import time # for simple timer functionality
from threading import Lock # so only one thread can write code at a time
from azure.storage.fileshare import ShareClient # allow writing to an Azure File Share
import json # allow for the creation of json files
import argparse # allows the parsing of command line parameters

save_path = Path("C:/Users/shado/Downloads")
manifest_lock = Lock() # create a lock object

def update_manifest(emulator, new_hash): # only allows one thread in this block at once
    with manifest_lock:
        manifest = read_manifest_file()
        manifest[emulator] = new_hash
        write_manifest_file(manifest)

# determine the save_path based on emulator
# not too complex, only required to differentiate between emulators
def determine_save_path(emulator_file_path):
    if "Dolphin" in emulator_file_path:
        return Path("C:/Users/shado/Documents/Dolphin Emulator/Wii")
    elif "pcsx2" in emulator_file_path:
        return Path("C:/Users/shado/Documents/PCSX2/cheats")
    else:
        return save_path

# check if X process is running
def is_running(program_name):
    for process in psutil.process_iter(['name']):
        # seems complicated, but iterates through each open process.
        # checks only for the name of the process
        if process.info['name'] == program_name:
            return True
    return False

# monitor X process to see when it opens and when it closes
# needs a folder name to see which Azure folder to reach into
# also needs the 'share' object to connect to Azure
def monitor_process(program_name, folder_name, share):
    while True:
        # waiting for any emulator to open
        while True:
            if is_running(program_name):
                try:
                    directory_folder = share.get_directory_client(folder_name) # connect to the folder
                    directory_folder.create_directory() # create the folder if it doesn't exist
                except Exception as e: # folder already exists
                    pass

                retrieve_data(share, folder_name + "/data.txt", save_path / "data.txt") # retrieve the data from Azure
                print(program_name + " was opened.")
                print("Retrieved remote data from " + folder_name + ".")
                break
                

            time.sleep(5) #just waits 5 seconds before checking again

        # waiting for the emulator to close
        while True:
            if not is_running(program_name):
                print(program_name + " was closed.")
                break

            time.sleep(5) # effectively the same code, but to check if it has closed

# uploading data to Azure
def upload_data(azure_connection, target_file, to_write):
    file_client = azure_connection.get_file_client(target_file) # connect to the target file 

    with open(to_write, "rb") as write_file:
        file_client.upload_file(write_file)

# pulling data from Azure
# to_write is the local file to write the remote data into
def retrieve_data(azure_connection, target_file, local_to_write):
    file_client = azure_connection.get_file_client(target_file)

    with open(local_to_write, "wb") as source_file: # open a file to write the remote data from
        data = file_client.download_file() # download the file
        data.readinto(source_file) # writes into source_file
        return source_file

def parse_config_file(config_file_path):
    script_dir = Path(__file__).parent # get the directory of the script file
    config_file_path = script_dir / config_file_path # get the full path to the config file

    with open(config_file_path, "r") as config_file:
        config_data = json.load(config_file)
    return config_data


############################### ACTUAL CODE STARTS HERE ###############################

config_file = parse_config_file("config.json") # read the config file 

connection_string = config_file["connection_string"] # your connection string goes here, private information, do not share it with anyone
share_name = config_file["share_name"]  # name of the Azure File Share
emulator_data = config_file["emulator_data"] # nested dictionary of emulator data

share = ShareClient.from_connection_string(connection_string, share_name) # connect to azure

directory = share.get_directory_client("")  # "" means the root of the share
for item in directory.list_directories_and_files():
    print(item) # print out everything in the directory (should be empty for now)

file_client = share.get_file_client("test.txt") # what the file is called remotely 

with open("data.txt", "wb") as source_file: # open a file to write the remote data from
    data = file_client.download_file() # download the file
    data.readinto(source_file) # writes into source_file

with open("data.txt", "rb") as source_file:
    print(source_file.read())

# with open("data.txt", "rb") as source_file: # simple write
#     file_client.upload_file(source_file)

# print("upload complete")
# share.close()


emulators = {"Dolphin.exe": "dolphin", 
             "pcsx2-qt.exe": "pcsx2"}

# with ThreadPoolExecutor() as executor:
#     for emulator, folder_name in emulators.items():
#         executor.submit(monitor_process, emulator, folder_name, share)



