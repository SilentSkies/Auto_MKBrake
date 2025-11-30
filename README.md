[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

# Auto_MKBrake

**Auto_MKBrake** is a helper tool to speed up archiving your DVDs and Blu-rays. It combines `MakeMKV` and `HandBrakeCLI` into a single workflow that lets you rip a new disc while your computer is still busy encoding the previous one.

## Key Features

* **Rip & Encode Simultaneously:** You don't have to wait for HandBrake to finish. As soon as the disc is ripped, it ejects, and the encoding starts in the background so you can pop in the next disc immediately.
* **Manual Track Selection:** Some discs (especially from Lionsgate) hide the real movie inside hundreds of fake playlists to trick automation. This script pauses to let you pick the correct Title ID, ensuring you don't waste time ripping the wrong file.
* **Audio Safety:** By default, this script preserves 7.1 surround sound (converting to AAC) to ensure no channels are lost during downmixing. You can also switch this to "Passthrough" to keep the original audio exactly as it is on the disc.
* **Smart Priority:** Encoding runs at a "Below Normal" system priority. This ensures your computer prioritises reading the disc first, which helps prevent read errors during the rip.
* **Resilient:** If a specific file fails to encode, the script simply logs the error and moves on to the next job rather than stopping everything.
* **Auto Cleanup:** The massive raw MKV file is deleted only after the script confirms the new compressed file has been created successfully.

## Prerequisites

1.  **Python 3.10+**
2.  **MakeMKV:** You will need MakeMKV installed with a valid license (or the [current beta key](https://cable.ayra.ch/makemkv/)).
3.  **HandBrakeCLI:** The command-line version of HandBrake.
    * Download: [HandBrake Downloads](https://handbrake.fr/downloads.php) (Select CLI).

## Installation

1.  Clone this repository (or download the files to a folder).
2.  Ensure you have the 5 source files: `main.py`, `config.py`, `utils.py`, `disc_ops.py`, `encoding.py`.

## Configuration

All settings are inside `config.py`. You don't need to touch the main code to change your preferences.

Open `config.py` to adjust:

* **Paths:**
    * `drive_letter`: Your optical drive (e.g., `D:`).
    * `raw_directory`: Temporary folder for the large raw rips (SSD recommended).
    * `encoded_directory`: Where you want the final files to go.
* **Binaries:**
    * If you leave `makemkv_path` or `handbrake_path` as `None`, the script tries to find them automatically. If that fails, paste the full path to the `.exe` here.
* **Encoding:**
    * `video_codec`: Defaults to `nvenc_h265` (Nvidia GPU). Change to `x265` for CPU-only or `vce_h265` for AMD cards.
    * `video_quality`: The RF value (Default `23`). Lower numbers mean higher quality but larger file sizes.
    * `audio_mixdown`: Defaults to `7point1`.

## Usage

1.  Open a terminal (Command Prompt or PowerShell) in the project folder.
2.  Run the script:
    ```bash
    python main.py
    ```
3.  **How it works:**
    * The script waits for you to insert a disc.
    * It scans the disc and shows you a list of titles (ID, Length, and Size).
    * **Type the ID** you want to rip (e.g., `0` for the movie, or `0,1,2` for episodes).
    * The script rips the file to the `Raw` folder.
    * Once the rip is done, the disc ejects.
    * **Simultaneously**, a background worker grabs that raw file and starts encoding it.
    * Insert the next disc straight away.

## Project Structure

* `main.py`: The main entry point that runs the show.
* `config.py`: Where all your settings live.
* `utils.py`: Handles logging and background processes.
* `disc_ops.py`: Handles the MakeMKV ripping logic.
* `encoding.py`: Handles the HandBrake encoding logic.

## Troubleshooting

* **"Missing executable"**: Check `config.py`. You might need to paste the full path to `makemkvcon64.exe` or `HandBrakeCLI.exe` if they aren't in your system PATH.
* **Rip Fails**: Check the disc for scratches or smudges. Check the log file in your Raw directory to see if the drive reported read errors.
* **Audio is missing**: If using `nvenc`, make sure your drivers are up to date. The default `av_aac` is the safest option for compatibility.
