# this file is for testing the functionality of certain features before they are appended to the main script file
from pathlib import Path # turns a directory into an object you can iterate through
from concurrent.futures import ThreadPoolExecutor # allows for the use of threads, so you can call functions non-sequentially
import hashlib # allows you to hash files, nothing major
import psutil # mandatory for checking for open processes
import time # for simple timer functionality

save_path = Path("C:/Users/shado/Downloads")

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
                print(program_name)
                break

            time.sleep(5) #just waits 5 seconds before checking again

        # waiting for the emulator to close
        while True:
            if not is_running(program_name):
                print(program_name)
                break

            time.sleep(5) # effectively the same code, but to check if it has closed


emulators = ["Dolphin.exe", "pcsx2-qt.exe"]

with ThreadPoolExecutor() as executor:
    executor.map(monitor_process, emulators) # use threading to run the function simultaneously on all elements



