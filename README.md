[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

# Auto_MKBrake

**Auto_MKBrake** is a helper tool to speed up archiving your DVDs and Blu-rays. It combines `MakeMKV` and `HandBrakeCLI` into a single workflow that lets you rip a new disc while your computer is still busy encoding the previous one.

## Key Features

* **Rip & Encode Simultaneously:** You don't have to wait for HandBrake to finish. As soon as the disc is ripped, it ejects, and the encoding starts in the background so you can pop in the next disc immediately.
* **Manual Track Selection:** Some discs hide the real movie inside hundreds of fake playlists to trick automation. This script pauses to let you pick the correct Title ID once you see the list of tracks it is usually obvious which is the correct title.
* **Defaults** By default, this script encodes video using `nvenc_265` creating a `.mp4` file for the best platform compatibility using one of the fastest, modern codecs. It preserves 7.1 surround sound (converting to AAC) and  to ensure no channels are lost during downmixing. All of these settings are configurable through `config.py`.
* **Smart Priority:** Encoding runs at a "Below Normal" system priority. This ensures your computer prioritises reading the disc first, which prevents read errors during the rip.
* **Resilient:** If a specific file fails to encode, the script simply logs the error and moves on to the next job rather than stopping everything.
* **Auto Cleanup:** The raw MKV file is deleted only after the script confirms the new compressed file has been created successfully.
* **Reprocessing:** If the script does fail the `reprocessor.py` script can detect mkv files and restart the encoder.

## Prerequisites

1.  **Python 3.10+**
2.  **MakeMKV:** You will need [MakeMKV installed](https://www.makemkv.com/) with a valid license (or the [current beta key](https://cable.ayra.ch/makemkv/)).
3.  **HandBrakeCLI:** The command-line version of HandBrake.
    * Download: [HandBrake Downloads](https://handbrake.fr/downloads.php) (Select Command Line Version).

## Warning
This application is CPU and GPU intensive. As soon as encoding starts it will consume *ALL* of the available resources to complete the task in as short a time as possible.

## Installation

1.  Clone this repository (or download the files to a folder).

## Configuration

All settings are managed in `config.py`. You do not need to edit any other files to change settings.

### 1. Paths & Binaries
* `drive_letter`: Your optical drive (e.g., `D:`).
* `raw_directory`: Temporary storage for the raw rips (MKV files can be up to 60GB, if you intend to rip more at once ensure you have the free space for this).
* `encoded_directory`: Destination for the encoded files.
* `makemkv_path` / `handbrake_path`: Set these to `None` to auto-detect. If the script cannot find them, paste the full path to the `.exe` (e.g., `r"C:\Program Files\HandBrake\HandBrakeCLI.exe"`).

### 2. Video Settings
[Comprehensive list of CLI parameters](https://handbrake.fr/docs/en/1.9.0/cli/command-line-reference.html)

Adjust `video_codec` and `video_quality` to balance speed vs. storage size.

| Setting | Options | Default | Description |
| :--- | :--- | :--- |
| **`video_codec`** | `nvenc_h265` | Yes | Nvidia GPU. Fast, high efficiency. |
| | `nvenc_h264` | | Nvidia GPU. Older format, highly compatible. |
| | `x265` | | CPU Only. Slow, but creates the smallest files. |
| | `x264` | | CPU Only. Industry standard compatibility. |
| | `vce_h265` | | AMD Radeon GPU encoding. |
| | `qsv_h265` | | Intel QuickSync (integrated graphics) encoding. |
| **`video_quality`** | `20` - `28` | `23` | **RF/CQ Value.** Controls quality. <br>**Note:** The scale changes depending on the codec selected. <br>• **x264:** `20`-`23` is standard. <br>• **x265:** `24`-`28` <br>• **NVENC:** `20`-`25` `23` is a good middle ground. <br>Lower number = Higher quality (larger file). <br>This is largely down to personal preference. |
| **`video_codec_preset`** | `p1` - `p7` | `p5` | **(For NVENC)** `p7` is slowest/best, `p1` is fastest/worst. Default is `p5`. |
| | `slow` / `fast` | **(For CPU)** Use `slow`, `medium`, or `fast`. |

### 3. Audio Settings
Adjust `audio_codec` and `audio_mixdown` to choose between archival perfection or space saving.

| Setting | Options | Description |
| :--- | :--- | :--- |
| **`audio_codec`** | `av_aac` | **(Default)** Best compatibility. Compress to AAC. |
| | `copy` | **Passthrough.** Bit-for-bit clone of the Bluray audio (TrueHD/DTS-HD). Largest size. |
| | `ac3` | Dolby Digital. Good for older optical-cable amplifiers. |
| **`audio_mixdown`** | `7point1` | **(Default)** Preserves/Upmixes to 7.1 channels. Safe for all sources. |
| | `5point1` | Standard Surround. Merges side/rear channels. |
| | `stereo` | 2.0 Channels. Best for TV speakers/phones. |

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

4. **reprocess.py**
   
    If the script goes wrong at any point and you are left with a partly processed encoded file you can use `reprocess.py` to finish up.
    * Delete any part encoded files and folder created by the previous script.
    * Run `python reprocess.py`
    * The script scans the raw folder for any mkv files and checks the encoded folder to see if they already exist.
    * If they don't, it then queues the jobs up to be reprocessed by Handbrake according to the same seetings as in `config.py`.
    * If there are multiple files it will process them simultaneously.


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
