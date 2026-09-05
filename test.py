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



# check if X process is running
def is_running(program_name):
    for process in psutil.process_iter(['name']):
        # seems complicated, but iterates through each open process.
        # checks only for the name of the process
        if process.info['name'] == program_name:
            return True
    return False

# monitor X process to see when it opens and when it closes
# needs a nested dictionary of information
# also needs the 'azure_connection' object to connect to Azure
def monitor_process(program_detail_dict, azure_connection, config_file, manifest_lock):
    ############ initial setup, grabbing all the needed parameters #################
    exec_name = program_detail_dict["process_name"] # grabs the executable name
    local_path_list = [] # list for local paths
    remote_path_list = [] # list for remote paths
    
    for entry in program_detail_dict["local_save_path"]:
        local_path_list.append(entry["local"]) # fill in the lists, nothing too complex
        remote_path_list.append(entry["remote"])

    updated_manifest = {} # updated manifest, after any potential sync with the remote

    while True:
        # waiting for any emulator to open
        while True:
            if is_running(exec_name):
                # pull remote data on startup
                updated_manifest = read_manifest("manifest.json", azure_connection, config_file, manifest_lock)
                break # break the current while true after everything is loading
            time.sleep(5) #just waits 5 seconds before checking again

        # waiting for the emulator to close
        while True:
            if not is_running(exec_name):
                print(exec_name + " was closed.")
                break

            time.sleep(5) # effectively the same code, but to check if it has closed

# function to make sure a certain filepath exists before writing
def create_remote_path(azure_connection, remote_path):
    parts = remote_path.split("/")
    current_path = "" # build up the directories bit by bit

    for part in parts:
        if current_path == "": # only necessary for first part as we don't need the '/'
            current_path = current_path + part
        else:
            current_path = current_path + "/" + part # otherwise simply append each part whilst including the '/'

        print(current_path)
        azure_directory = azure_connection.get_directory_client(current_path) # use to grab a client handle
        try:
            azure_directory.create_directory() # use the client handle to create a path
        except Exception:
            pass

# pushes everything in the "to-monitor" folders to Azure
def push_to_remote(azure_connection, emulator_dictionary):       
    for entry_name, entry_details in emulator_dictionary.items():
        file_path_dict = entry_details["local_save_path"] # each value is a list of dictionaries

        for list_item in file_path_dict: # print every item in the directory 
            loop_through_directory(list_item["local"], list_item["remote"], azure_connection) 

# uploading data to Azure
def upload_data(azure_connection, target_file, to_write):
    file_client = azure_connection.get_file_client(target_file) # connect to the target file 

    with open(to_write, "rb") as write_file:
        file_client.upload_file(write_file)

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

# pulling data from Azure
# to_write is the local file to write the remote data into
def retrieve_data(azure_connection, target_file, local_to_write):
    try:
        file_client = azure_connection.get_file_client(target_file)

        with open(local_to_write, "wb") as source_file: # open a file to write the remote data from
            data = file_client.download_file() # download the file
            data.readinto(source_file) # writes into source_file
        return True
        
    except Exception:
        return False 

def parse_config_file(config_file_path):
    script_dir = Path(__file__).parent # get the directory of the script file
    config_file_path = script_dir / config_file_path # get the full path to the config file

    with open(config_file_path, "r") as config_file:
        config_data = json.load(config_file)
    return config_data

# reads the manifest file, NOTE: manifest_lock is ONLY used for updating the manifest
def read_manifest(manifest_path, azure_connection, config_file, manifest_lock):
        script_dir = Path(__file__).parent # get the directory of the script file
        manifest_file_path = script_dir / manifest_path # get the full path to the config file
        remote_manifest_path = script_dir / "remote_manifest.json"

        ########################## OPENING AND READING REMOTE/LOCAL MANIFEST FILES #############################
        if not (retrieve_data(azure_connection, "manifest.json", remote_manifest_path)): # download the remote manifest into a temporary file 
            remote_manifest_data = {} # empty dictionary if it doesn't exist
        else:
            with open(remote_manifest_path, "r") as remote_manifest_file: # load json if it does exist
                remote_manifest_data = json.load(remote_manifest_file)
            remote_manifest_path.unlink() # delete the temporary file, since we don't want to keep the remote
        
        with open(manifest_file_path, "r") as manifest_file: # load the local remote file
            local_manifest_data = json.load(manifest_file)
        

        for relative_path, current_info in local_manifest_data.items(): # grab info of each local entry
            ################ GRABBING REQUIRED INFORMATION #######################
            remote_base = current_info["remote_base"]
            local_base = dictionary_reverse_lookup(config_file, remote_base) # local base needed for download 
            relative_part = relative_path[len(remote_base) + 1:] # grab the relative part, trim out the excess from relative_path, including the backslash
            full_local_path = local_base + "/" + relative_part # full local path that we pull/push to/from

            ################## IF LOCAL FILE DOESN'T EXIST ON REMOTE ###################
            if relative_path not in remote_manifest_data: # create the missing file
                file_parent = str(Path(relative_path).parent.as_posix()) # don't want a directory for the file
                create_remote_path(azure_connection, file_parent) # not in remote manifest, file should be uploaded 
                upload_data(azure_connection, relative_path, full_local_path)
                continue # skip over the iteration

            # otherwise, the file already exists and we can proceed
            remote_info = remote_manifest_data[relative_path] # enter the dictionary of the related entry
            remote_timestamp = remote_info["timestamp"]
            remote_hash = remote_info["hash"] # grab appropriate information for the remote equivalent
            # this informatin is required for pulling/pushing
           
            if current_info["hash"] != remote_hash: # hash difference, main part
                if current_info["timestamp"] < remote_timestamp: # remote is more recent
                    retrieve_data(azure_connection, relative_path, full_local_path)
                    update_manifest(manifest_lock, relative_path, local_manifest_data, {"timestamp": remote_timestamp, "hash": remote_hash})
                else: # local is more recent 
                    file_parent = str(Path(relative_path).parent.as_posix()) # don't want a directory for the file
                    create_remote_path(azure_connection, file_parent) # just make sure the path exists 
                    upload_data(azure_connection, relative_path, full_local_path)
                    update_manifest(manifest_lock, relative_path, remote_manifest_data, {"timestamp": current_info["timestamp"], "hash": current_info["hash"]})

        return local_manifest_data # return the newly updated local manifest after it is updated


# updates the manifest file with any new hashes
# NOTE: MOSTLY useful when the remote is more recent. When you pull it, the local manifest is now obsolete.
def update_manifest(manifest_lock, key_to_update, manifest_dictionary, new_value): # manifest_lock only allows one thread in this block at once
    with manifest_lock:
        manifest_dictionary[key_to_update] = new_value
# extremely simple function, updates the matching key with the new value
                
def dictionary_reverse_lookup(config_file, remote_base): # find a local path based on remote
    for key, value in config_file.items(): 
        for entry in value["local_save_path"]: # iterate through the list of paths 
            if entry["remote"] == remote_base: 
                    return entry["local"] # return the local value 
    # basically, grab a remote base and return the associated local path base


############################### ACTUAL CODE STARTS HERE ###############################
manifest_lock = Lock() # create a lock object
config_file = parse_config_file("config.json") # read the config file 

connection_string = config_file["connection_string"] # your connection string goes here, private information, do not share it with anyone
share_name = config_file["share_name"]  # name of the Azure File Share
emulator_list = config_file["emulators"] # nested dictionary of emulator data

################################### INITIAL SETUP ######################################
azure_connection = ShareClient.from_connection_string(connection_string, share_name) # connect to azure

# Worth noting: Emulator data is broken into executable name, and then filepaths.

# for dictionary_keys, dictionary_values in emulator_list.items():
#     for entry in dictionary_values["local_save_path"]: # iterate through the list 
#         print(entry["remote"])

read_manifest("manifest.json", azure_connection, emulator_list)


#push_to_remote(azure_connection, emulator_list)

# with ThreadPoolExecutor() as executor:
#     for emulator_name, emulator_details in emulator_list.items():
#         executor.submit(monitor_process, emulator_details, azure_connection)

# azure_connection.close()





