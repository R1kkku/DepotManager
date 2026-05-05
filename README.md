# DepotManager

A graphical desktop application for downloading Steam depots via the Morrenus API and DepotDownloaderMod.

## Requirements

Before running DepotManager, make sure you have the following in the **same folder** as `DepotManager.exe`:

- **DepotDownloaderMod.exe** — the underlying downloader engine
  > Download it from its official release page and place it alongside `DepotManager.exe`.

- **A valid Morrenus API Key** — required to fetch depot manifests
  > Register and obtain your key at [https://manifest.morrenus.xyz](https://manifest.morrenus.xyz)

## Installation

1. Download the latest `DepotManager.exe` from the [Releases](../../releases) page.
2. Download **DepotDownloaderMod** from its official release page.
3. Create a folder and place both `DepotManager.exe` and all DepotDownloaderMod files inside it.
4. Run `DepotManager.exe` — no installation required.

## Usage

### 1. Configure your API Key

- Paste your **Morrenus API Key** in the *API Key* field at the top.
- Click **Save Key** to persist it in `settings.json`.

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
| `api_key` | *(empty)* | Your Morrenus API key |
| `api_base_url` | `https://manifest.morrenus.xyz/api/v1` | API endpoint |
| `exe_name` | `DepotDownloaderMod.exe` | Downloader executable name |
| `max_concurrent_downloads` | `1` | Maximum simultaneous downloads |
| `request_timeout` | `30` | HTTP request timeout in seconds |

You do not need to edit this file manually. All values work out of the box — the only required change is saving your API Key through the application interface.

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
