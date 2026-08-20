# this file is for testing the functionality of certain features before they are appended to the main script file
from pathlib import Path # turns a directory into an object you can iterate through
from concurrent.futures import ThreadPoolExecutor # allows for the use of threads, so you can call functions non-sequentially
import hashlib # allows you to hash files, nothing major
import psutil # mandatory for checking for open processes
import time # for simple timer functionality
from threading import Lock # so only one thread can write code at a time
from azure.storage.fileshare import ShareClient # allow writing to an Azure File Share

save_path = Path("C:/Users/shado/Downloads")
manifest_lock = Lock() # create a lock object

def update_manifest(emulator, new_hash): # only allows one thread in this block at once
    with manifest_lock:
        manifest = read_manifest_file()
        manifest[emulator] = new_hash
        write_manifest_file(manifest)

def is_running(program_name):
    for process in psutil.process_iter(['name']):
        # seems complicated, but iterates through each open process.
        # checks only for the name of the process
        if process.info['name'] == program_name:
            return True
    return False

def monitor_process(program_name):
    while True:
        # waiting for any emulator to open
        while True:
            if is_running(program_name):
                print(program_name + " is running.")
                break

            time.sleep(5) #just waits 5 seconds before checking again

        # waiting for the emulator to close
        while True:
            if not is_running(program_name):
                print(program_name + " was closed.")
                break

            time.sleep(5) # effectively the same code, but to check if it has closed

connection_string = ""
share_name = "storeddata"  # whatever you named it

share = ShareClient.from_connection_string(connection_string, share_name) # connect to azure

directory = share.get_directory_client("")  # "" means the root of the share
for item in directory.list_directories_and_files():
    print(item) # print out everything in the directory (should be empty for now)

file_client = share.get_file_client("test.txt") # what the file is called remotely 

with open("data.txt", "rb") as source_file:
    file_client.upload_file(source_file) # write this to the remote file with the same name

print("upload complete")
share.close()


emulators = ["Dolphin.exe", "pcsx2-qt.exe"]

# with ThreadPoolExecutor() as executor:
#     for emulator in emulators:
#         executor.submit(monitor_process, emulator)



