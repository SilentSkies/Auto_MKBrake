[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

# Auto_MKBrake

**Auto_MKBrake** is a robust, concurrent pipeline for archiving Blu-ray and DVD media. It orchestrates `MakeMKV` and `HandBrakeCLI` to rip and encode media in parallel, significantly reducing the time required to process a batch of physical discs.

## Key Features

* **Concurrency Pipeline:** The system rips the current disc while background threads encode previously ripped files. This ensures your optical drive is never waiting for an encode to finish.
* **Manual Selection (Anti-Obfuscation):** The script pauses to allow the user to select the specific Title ID. This is the only reliable way to handle discs with "playlist obfuscation" (hundreds of fake playlists), common on Lionsgate releases.
* **Audio Fidelity:** Default configuration preserves **7.1 surround sound**. It upmixes/preserves channels to 7.1 AAC to prevent data loss from downmixing, or can be set to Passthrough for lossless archival.
* **Resource Management:** Encoding threads run at **Below Normal** process priority. This guarantees that the resource-heavy HandBrake process never starves the MakeMKV rip process, preventing read errors.
* **Robust Error Handling:** Worker threads are "immortal". If a specific file fails to encode, the thread logs the error and moves to the next job without crashing the main application.
* **Safe Cleanup:** Raw MKV files are only deleted if the encoded file exists and has a valid file size.

## Prerequisites

1.  **Python 3.10+**
2.  **MakeMKV:** You must have MakeMKV installed and a valid license key (or the [current beta key](https://cable.ayra.ch/makemkv/)) active.
3.  **HandBrakeCLI:** The command-line version of HandBrake.
    * Download: [HandBrake Downloads](https://handbrake.fr/downloads.php) (Select CLI).

## Installation

1.  Clone this repository.

## Configuration

All settings are managed in `config.py` using a Python Dataclass. You do not need to edit the logic files to change settings.

Open `config.py` to adjust:

* **Paths:**
    * `drive_letter`: Your optical drive (e.g., `D:`).
    * `raw_directory`: Temporary storage for large MKV files (SSD recommended).
    * `encoded_directory`: Final destination for compressed MP4 files.
* **Binaries:**
    * If `makemkv_path` or `handbrake_path` are set to `None`, the script looks for them in your Windows System PATH. Otherwise, provide the full path to the `.exe`.
* **Encoding:**
    * `video_codec`: Defaults to `nvenc_h265` (Nvidia GPU). Change to `x265` for CPU-only or `vce_h265` for AMD.
    * `video_quality`: The RF value (Default `23`). Lower is higher quality/larger file.
    * `audio_mixdown`: Defaults to `7point1`.

## Usage

1.  Open a terminal (Command Prompt or PowerShell) in the project folder.
2.  Run the application:
    ```bash
    python main.py
    ```
3.  **The Workflow:**
    * The script waits for a disc.
    * Insert a disc.
    * The script scans the titles and displays a table of ID, Duration, and Size.
    * **Input the ID** you wish to rip (e.g., `0` for the main movie, or `0,1,2` for episodes).
    * The script rips the file to the `Raw` folder.
    * Once ripping is done, the disc ejects.
    * **Simultaneously**, the background worker picks up the raw file and begins encoding it to the `Encoded` folder.
    * Insert the next disc immediately; do not wait for the encode to finish.

## Project Structure

* `main.py`: The entry point. Handles the main loop, user input, and queuing jobs.
* `config.py`: A Singleton Dataclass containing all user settings.
* `utils.py`: Shared utilities for thread-safe logging and process management.
* `disc_ops.py`: Handles interaction with the physical drive and MakeMKV.
* `encoding.py`: Handles the HandBrake worker threads.

## Troubleshooting

* **"Missing executable"**: Ensure the paths in `config.py` point exactly to `makemkvcon64.exe` and `HandBrakeCLI.exe`.
* **Rip Fails**: Check the physical disc for scratches. Check the generated log file in your Raw directory for specific SCSI errors.
* **Audio is missing**: If using `nvenc`, ensure your driver supports the audio codec. The script defaults to `av_aac` (software audio encoding) which is the most compatible.
