[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

# Auto_MKBrake

**Auto_MKBrake** accelerates DVD and Blu-ray archiving by combining `MakeMKV` and `HandBrakeCLI` into a concurrent workflow. This allows you to rip a new disc while the previous one encodes in the background, maximising hardware throughput.

## Key Features

* **Concurrent Workflow:** Rips and encodes in parallel. The drive ejects immediately after ripping so you can insert the next disc without waiting for the encoder.
* **Optimised Defaults:** Configured for `nvenc_h265` (.mp4) and 7.1 AAC audio for high compatibility and speed. Settings are adjustable in `config.py`.
* **Smart Priority:** Runs encoding at "Below Normal" priority to prevent resource starvation during disc reads.
* **Resiliency & Cleanup:** Logs errors instead of crashing and deletes raw MKVs only after successful encoding verification.
* **Reprocessing:** Includes `reprocess.py` to detect and batch-encode previously missed or failed raw files.

## Prerequisites

1.  **Python 3.10+**
2.  **MakeMKV:** Installed with a [valid or beta license](https://cable.ayra.ch/makemkv/).
3.  **HandBrakeCLI:** [Download the Command Line Version](https://handbrake.fr/downloads.php).

## Warning

This tool utilises **100%** of available CPU/GPU resources to minimise processing time.

## Installation

1.  Clone this repository or download the files.

## Configuration

Manage all settings via `config.py`.

### 1. Paths & Binaries
* `drive_letter`: Optical drive (e.g., `D:`).
* `min_title_length`: Seconds threshold to filter junk titles (menus/warnings).
* `raw_directory`: Temp storage for raw rips (SSD recommended; ~60GB/disc).
* `encoded_directory`: Final destination.
* `makemkv_path` / `handbrake_path`: Set to `None` for auto-detection or paste the full `.exe` path.

### 2. Video Settings
[HandBrake CLI Reference](https://handbrake.fr/docs/en/1.9.0/cli/command-line-reference.html)

Adjust `video_codec` and `video_quality` to balance speed vs. size.

| Setting | Options | Default | Description |
| :--- | :--- | :--- | :--- |
| **`video_codec`** | `nvenc_h265` | **Yes** | Nvidia GPU. Fast, high efficiency. |
| | `nvenc_h264` | | Nvidia GPU. Highly compatible. |
| | `x265` | | CPU Only. Slowest, smallest files. |
| | `x264` | | CPU Only. Standard compatibility. |
| | `vce_h265` | | AMD Radeon GPU. |
| | `qsv_h265` | | Intel QuickSync. |
| **`video_quality`** | `20` - `28` | `23` | **RF/CQ Value.** Lower = Higher quality (larger file). <br>**Note:** Scale varies by codec: <br>• **x264:** `20`-`23` <br>• **x265:** `24`-`28` <br>• **NVENC:** `20`-`25` |
| **`video_codec_preset`** | `p1` - `p7` | `p5` | **(NVENC)** `p7` (Slowest/Best) to `p1` (Fastest). |
| | `slow` / `fast` | | **(CPU)** `slow`, `medium`, or `fast`. |

### 3. Audio Settings

| Setting | Options | Description |
| :--- | :--- | :--- |
| **`audio_codec`** | `av_aac` | **(Default)** AAC Compression. High compatibility. |
| | `copy` | Passthrough (TrueHD/DTS-HD). Lossless, largest size. |
| | `ac3` | Dolby Digital. Legacy amplifier support. |
| **`audio_mixdown`** | `7point1` | **(Default)** Preserves/Upmixes to 7.1. Safe for all sources. |
| | `5point1` | Standard Surround. |
| | `stereo` | 2.0 Channels. |

## Usage

1.  Run `python main.py` in the project folder.
2.  **Workflow:**
    * Insert disc; script scans and lists valid titles.
    * Enter the target **Track ID** (e.g., `0` for movie, `0,1` for episodes).
    * Script rips to `Raw`, ejects disc, and immediately queues background encoding.
    * Insert next disc immediately.

### Failed Encodes
Use `reprocess.py` to finish partial jobs:
1.  Delete partial files in the encoded folder.
2.  Run `python reprocess.py`.
3.  Script queues any existing MKVs in `Raw` that do not exist in `Encoded`.

## Project Structure

* `main.py`: Entry point; handles user input and queuing.
* `reprocess.py`: Batch encodes existing raw files.
* `config.py`: Singleton Dataclass for settings.
* `utils.py`: Logging and process utilities.
* `disc_ops.py`: MakeMKV interaction logic.
* `encoding.py`: HandBrake worker logic.

## Troubleshooting

* **Missing executable:** Verify paths in `config.py`.
* **Rip Fails:** Check disc condition and `Raw` directory logs for read errors.
* **Missing Audio:** Update GPU drivers or switch to `av_aac` (software) mode.
