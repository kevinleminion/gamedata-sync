# this file is for testing the functionality of certain features before they are appended to the main script file
from pathlib import Path # turns a directory into an object you can iterate through
import hashlib # allows you to hash files, nothing major
import psutil # mandatory for checking for open processes

def is_running(program_name):
    for process in psutil.process_iter(['name']):
        # seems complicated, but iterates through each open process.
        # checks only for the name of the process
        if process.info['name'] == program_name:
            return True
    return False

save_path = Path("C:/Users/shado/Downloads")

if is_running("pcsx2-qt.exe"):
    print("PCSX2 is running!")
else:
    print("PCSX2 is not running.")

