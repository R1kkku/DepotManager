# DepotManager

A modular graphical desktop application for downloading Steam depots via multiple manifest sources with [DepotDownloaderMod](https://github.com/SteamAutoCracks/DepotDownloaderMod).

## Project Structure

The source code has been refactored from a monolithic script into a clean, modular Python package:

```txt
Source/
├── DepotManager/              # Modular application (current)
│   ├── __init__.py
│   ├── main.py                # Entry point & logging setup
│   ├── gui.py                 # Tkinter user interface
│   ├── api_client.py          # Async HTTP client (aiohttp)
│   ├── downloader.py          # Download orchestration & subprocess management
│   ├── parser.py              # Lua key extraction & manifest scanning
│   ├── config.py              # Settings, constants & path resolution
│   └── icon.ico
│
├── DepotManager_Monolitic/    # Legacy single-file version
│   └── main.py
│
├── DepotDownloaderMod/        # External download engine (bundled)
│   └── ...
│
└── requirements.txt
```

## Release Bundle Structure

Official releases are distributed as a bundle with two physically separated components:

```txt
DepotManager_v1.2.0/
├── README.txt
├── DepotManager/
│   └── DepotManager.exe       # GUI application (PyInstaller standalone)
└── DepotDownloaderMod/
    └── DepotDownloaderMod.exe # Download engine + runtime DLLs
```

**Do not move files out of their folders.** `DepotManager.exe` locates `DepotDownloaderMod.exe` using a relative path (`../DepotDownloaderMod/DepotDownloaderMod.exe`). Keep the folder structure intact.

## Requirements

Before running DepotManager, make sure the release bundle structure shown above is preserved.

- **DepotDownloaderMod** — the underlying downloader engine  
  > Downloaded from the official release page and placed inside `DepotDownloaderMod/`.  
  > Repository: [SteamAutoCracks/DepotDownloaderMod](https://github.com/SteamAutoCracks/DepotDownloaderMod)

- **An API Key** — required to fetch depot manifests  
  DepotManager supports two independent sources; you need a key for at least one:
  - **Morrenus's API** (HubcapManifest)
  - **Ryuu's API**
  
  You can store keys for both and switch between them inside the app.

## Installation

1. Extract the release bundle (`DepotManager_v1.2.0/`) anywhere on your PC.
2. Ensure `DepotManager/` and `DepotDownloaderMod/` remain side-by-side.
3. Run `DepotManager/DepotManager.exe` — no installation required.

## Usage

### 1. Configure your API Key

- Select your preferred source from the **Source** dropdown (*Morrenus's API* or *Ryuu's API*).
- Paste the corresponding API key in the *API Key* field.
- Click **Save Key** to persist it in `settings.json`.

> You can store keys for both sources. Simply switch the **Source** dropdown and save a key for each one.

### 2. Fetch depots for a game

- Enter a valid **Steam AppID** in the *Enter AppID* field.
- Click **Fetch Manifest** — the app will contact the selected source and display all available depots.

### 3. Select depots to download

- Each depot is listed with its **ID**, **status** (READY / INCOMPLETE), **decryption key**, and **manifest file**.
- Click the checkbox column on each row to select depots, or use **Select All** / **Deselect All**.

### 4. Start the download

- Click **START DOWNLOAD**.
- Output from DepotDownloaderMod will appear in the console area in real time.
- Click **STOP** at any time to cancel all running downloads.

## Configuration (`settings.json`)

The following settings are stored in `settings.json`, located inside the `DepotManager/` folder. The file is created automatically the first time you save your API Key:

| Key | Default | Description |
| --- | --- | --- |
| `api_key_morrenus` | *(empty)* | API key for Morrenus's API |
| `api_key_ryuu` | *(empty)* | API key for Ryuu's API |
| `selected_source` | `morrenus` | Active API source (`morrenus` or `ryuu`) |
| `api_base_url_morrenus` | `https://hubcapmanifest.com/api/v1` | Morrenus API endpoint |
| `api_base_url_ryuu` | `https://generator.ryuu.lol/secure_download` | Ryuu API endpoint |
| `exe_name` | `../DepotDownloaderMod/DepotDownloaderMod.exe` | Relative path to the downloader executable |
| `max_concurrent_downloads` | `1` | Maximum simultaneous downloads |
| `request_timeout` | `30` | HTTP request timeout in seconds |

You do not need to edit this file manually. All values work out of the box — the only required change is saving your API Key(s) through the application interface. You can store keys for both sources and switch between them at any time using the **Source** dropdown.

## Logging

A `depot_manager.log` file is created in the `DepotManager/` working directory and contains detailed debug and error information.

## Notes

- A temporary `keys.txt` file is created during downloads and automatically deleted when the application closes.
- Manifest files are copied temporarily to the working directory and deleted after each download completes.
- **ATTENTION** - When updating to a new version, it is advisable to delete old `settings.json` to get a clean, up-to-date configuration. Before doing so, **note down your API keys** from the *API Key* field (or open `settings.json` and copy the values of `api_key_morrenus` and/or `api_key_ryuu`), then re-enter them after the first launch.

## Running from Source (Python)

If you want to run the modular application with Python instead of the compiled executable:

```bash
cd Source
pip install -r requirements.txt
python -m DepotManager.main
```

Or use the launcher script:

```bash
python run_depot_manager.py
```
