# DepotManager

A graphical desktop application for downloading Steam depots via multiple manifest sources with DepotDownloaderMod.

## Requirements

Before running DepotManager, make sure you have the following in the **same folder** as `DepotManager.exe`:

- **DepotDownloaderMod.exe** — the underlying downloader engine  
  > Download all its files from the official release page and place them alongside `DepotManager.exe`.

- **An API Key** — required to fetch depot manifests  
  DepotManager supports two independent sources; you need a key for at least one:
  - **Morrenus's API** —
  - **Ryuu's API** —
  
  >You can store keys for both and switch between them inside the app.

## Installation

1. Download the latest `DepotManager.exe` from the [Releases](../../releases) page.
2. Download **DepotDownloaderMod** from its official release page.
3. Create a folder and place both `DepotManager.exe` and all DepotDownloaderMod files inside it.
4. Run `DepotManager.exe` — no installation required.

## Usage

### 1. Configure your API Key

- Select your preferred source from the **Source** dropdown (*Morrenus's API* or *Ryuu's API*).
- Paste the corresponding API key in the *API Key* field.
- Click **Save Key** to persist it in `settings.json`.

> You can store keys for both sources. Simply switch the **Source** dropdown and save a key for each one.

### 2. Fetch depots for a game

- Enter a valid **Steam AppID** in the *Enter AppID* field.
- Click **Fetch Manifest** — the app will contact the Morrenus API and display all available depots.

### 3. Select depots to download

- Each depot is listed with its **ID**, **status** (✅ READY / ⚠️ INCOMPLETE), **decryption key**, and **manifest file**.
- Click the checkbox column (☐/☑) on each row to select depots, or use **☑ All** / **☐ None**.

### 4. Start the download

- Click **▶ START DOWNLOAD**.
- Output from DepotDownloaderMod will appear in the console area in real time.
- Click **🛑 STOP** at any time to cancel all running downloads.

## Configuration (`settings.json`)

The following settings are stored in `settings.json`, located in the same folder as the executable. The file is created automatically the first time you save your API Key:

| Key | Default | Description |
| ----- | --------- | ------------- |
| `api_key_morrenus` | *(empty)* | API key for Morrenus's API |
| `api_key_ryuu` | *(empty)* | API key for Ryuu's API |
| `selected_source` | `morrenus` | Active API source (`morrenus` or `ryuu`) |
| `api_base_url` | `https://manifest.morrenus.xyz/api/v1` | Morrenus API endpoint |
| `exe_name` | `DepotDownloaderMod.exe` | Downloader executable name |
| `max_concurrent_downloads` | `1` | Maximum simultaneous downloads |
| `request_timeout` | `30` | HTTP request timeout in seconds |

You do not need to edit this file manually. All values work out of the box — the only required change is saving your API Key(s) through the application interface. You can store keys for both sources and switch between them at any time using the **Source** dropdown.

## Logging

A `depot_manager.log` file is created in the working directory and contains detailed debug and error information.

## Notes

- A temporary `keys.txt` file is created during downloads and automatically deleted when the application closes.
- Manifest files are copied temporarily to the working directory and deleted after each download completes.

## Dependencies (If you want to run it with python)

**Install dependencies:**
   Use the `requirements.txt` file to install all necessary libraries (such as `aiohttp`):

```bash
pip install -r requirements.txt
```
