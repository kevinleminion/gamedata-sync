# Emulator Save Sync

A background tool that watches for emulators (Dolphin, PCSX2, etc.) starting and stopping, and keeps their save data synchronized across multiple devices using Azure File Storage. It pulls the latest saves when an emulator opens, and pushes any changes back up when it closes.

## How it works, briefly

- A shared Azure File Share acts as the central store for save data.
- Each device keeps a local `manifest.json` — a record of every tracked save file's content hash and last-modified time.
- On emulator open: the tool compares your local manifest against the one stored on Azure, and pulls down anything that's changed remotely.
- On emulator close: it rehashes your local files, and pushes anything that's changed locally back up to Azure.
- Comparisons are done by content hash, not just filename or timestamp, so a file is only synced when its actual contents differ.

## Requirements

- **Python 3.x**, installed and available from your terminal (`python --version` should work)
- **An Azure account** with a Storage Account and a File Share created inside it (Azure's free tier / Azure for Students is enough for this)
- The following Python packages, installed via pip:

```
pip install azure-storage-file-share psutil plyer
```

Everything else the scripts use (`pathlib`, `json`, `hashlib`, `threading`, `subprocess`, `socket`, etc.) is part of Python's standard library — no extra install needed.

## Project files

| File | Purpose |
|---|---|
| `data_sync.py` | The main tool. Run this to start watching your emulators and syncing automatically. |
| `create_manifest.py` | Scans your configured save folders and (re)builds `manifest.json` from what's actually on disk. Run once during setup, and it's also called automatically by `data_sync.py` whenever an emulator closes. |
| `config.json` | **You create this.** Holds your Azure connection details and which folders to sync. See below — this is the part most likely to trip you up. |
| `config.example.json` | A template showing the expected shape of `config.json`, with placeholder values. Safe to look at, not meant to be used directly. |
| `manifest.json` | Generated automatically by `create_manifest.py`. You shouldn't need to edit this by hand. |
| `manual_pull.py` | Emergency/setup tool: force-downloads everything currently on Azure, ignoring the manifest entirely. Mainly useful when setting up a brand-new device. |
| `manual_push.py` | Emergency tool: force-uploads everything from your local folders, ignoring the manifest entirely. |
| `run_sync.bat` | A small launcher so `data_sync.py` can be run automatically when Windows starts. |

## First-time setup

1. **Install Python** if you haven't already, making sure to check "Add Python to PATH" during installation.
2. **Install the required packages** (see the command above).
3. **Create an Azure Storage Account and File Share** in the Azure Portal, if you don't already have one.
4. **Get your connection string**: in the Portal, open your Storage Account → *Access keys* → *Show* next to either key → copy the full connection string.
5. **Create `config.json`** — see the detailed section below. This is the step worth reading carefully.
6. **Run `create_manifest.py` once**, standalone, to generate your first local `manifest.json`:
   ```
   python create_manifest.py
   ```
7. **Run the tool:**
   ```
   python data_sync.py
   ```
   Leave it running in the background. It will print a message when it detects an emulator opening or closing.

## Creating `config.json` (the important part)

Copy `config.example.json`, rename the copy to `config.json`, and fill in your real values. **Never commit `config.json` to Git** — it contains your Azure connection string, which is a real secret. (`config.json` should already be listed in `.gitignore`.)

Here's a complete, realistic example, based on an actual working setup:

```json
{
    "connection_string": "DefaultEndpointsProtocol=https;AccountName=yourstorageaccount;AccountKey=yourkeyhere;EndpointSuffix=core.windows.net",
    "share_name": "storeddata",
    "emulators": {
        "dolphin": {
            "process_name": "Dolphin.exe",
            "local_save_path": [
                { "local": "C:/Users/yourname/AppData/Roaming/Dolphin Emulator/GC", "remote": "dolphin/gc" },
                { "local": "C:/Users/yourname/AppData/Roaming/Dolphin Emulator/Wii/title/00010004", "remote": "dolphin/wii/00010004" }
            ]
        },
        "pcsx2": {
            "process_name": "pcsx2-qt.exe",
            "local_save_path": [
                { "local": "C:/PCSX2/memcards", "remote": "pcsx2/memcards" },
                { "local": "C:/PCSX2/sstates", "remote": "pcsx2/sstates" }
            ]
        }
    }
}
```

**What each field means:**

- **`connection_string`** — the secret you copied from the Azure Portal. Grants full access to your storage account, so treat it like a password.
- **`share_name`** — the name of the File Share you created inside your storage account (not the storage account's own name).
- **`emulators`** — one entry per emulator you want synced.
  - The key (`"dolphin"`, `"pcsx2"`) is just a label for your own reference — it can be anything, it isn't checked against anything else.
  - **`process_name`** must exactly match how the emulator's process appears in Windows Task Manager, including capitalization (check the *Details* tab in Task Manager while the emulator is running if you're unsure).
  - **`local_save_path`** is a *list*, because a single emulator often needs more than one folder synced (for example, Dolphin keeps GameCube and Wii saves in separate folders). Each entry needs:
    - **`local`** — the full path to that folder **on this specific device**. This will very likely be different on every device you set this up on (different usernames, different drive letters) — don't just copy this value between devices without checking it.
    - **`remote`** — where that folder's contents should live on Azure. Pick anything, as long as it's unique across your whole config — no two entries, even under different emulators, should share the same `remote` value, or their files could collide.

**Finding your emulator's actual save folder:** most emulators have a menu option like *File → Open User Folder* that opens the exact folder they're using — this is more reliable than guessing a path. From there, look for the specific subfolder(s) that hold actual save data (not settings, themes, or cache) — this can take a bit of digging depending on the emulator, since save data isn't always in an obviously-named folder.

## Setting up an additional device

Because `local_save_path` values are specific to each device, you can't just copy `config.json` from one machine to another unchanged.

1. Install Python and the required packages on the new device (see *Requirements* above).
2. Copy over `config.json`, `data_sync.py`, `create_manifest.py`, and `manual_pull.py` — but **edit `config.json`'s `local` paths** to match where things actually live on this device.
3. **Do not copy `manifest.json` from your other device** — it describes the *other* device's state, not this one.
4. Run `manual_pull.py` once to download everything currently on Azure into this device's local folders:
   ```
   python manual_pull.py
   ```
5. Run `create_manifest.py` to build a manifest that reflects what was just downloaded:
   ```
   python create_manifest.py
   ```
6. From here on, run `data_sync.py` normally.

## Running automatically on startup

1. Open `run_sync.bat` in a text editor and update the path so it points to your actual copy of `data_sync.py` on this device.
2. Press `Win + R`, type `shell:startup`, press Enter.
3. Create a shortcut to `run_sync.bat` inside that folder.
4. Log out and back in to confirm it starts correctly on its own.

## Emergency / manual tools

- **`manual_pull.py`** — ignores the manifest entirely and force-downloads every file currently on Azure for every configured folder. Useful if something's gone wrong and you just want to reset a device to match what's on Azure, or when bootstrapping a new device.
- **`manual_push.py`** — the reverse: force-uploads every local file, ignoring the manifest. After using either of these, it's worth running `create_manifest.py` again so your manifest matches reality going forward.

## Known limitations

- If two devices happen to sync at almost exactly the same moment, there's a small window where one device's changes could be missed by the other. For personal, one-at-a-time use, this is unlikely to come up in practice.
- Closing any single emulator regenerates the manifest for *all* configured emulators, not just the one that closed. This is a deliberate simplicity trade-off — the extra work is small at normal save-file sizes.
- There's no conflict-resolution prompt — if both a local and remote copy of a file have changed since the last sync, the newer timestamp wins automatically.
