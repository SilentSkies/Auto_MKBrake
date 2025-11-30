from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class Configuration:
    # --- System & Hardware ---
    drive_letter: str = "D:"
    # Use raw strings (r"...") for Windows paths
    raw_directory: Path = Path(r"C:\Raw")
    encoded_directory: Path = Path(r"G:\Encoded")
    
    # Minimum length in seconds. 
    # 300 = 5 minutes (Recommended to filter junk)
    # 120 = 2 minutes (Use if you want special features)
    min_title_length: int = 480

    # --- Binaries (None = Auto-detect) ---
    makemkv_path: Optional[str] = r"C:\Program Files (x86)\MakeMKV\makemkvcon64.exe"
    handbrake_path: Optional[str] = r"C:\Program Files\HandBrake\HandBrakeCLI.exe"

    # --- Worker Behaviour ---
    encoder_worker_threads: int = 4   
    eject_on_completion: bool = True  
    keep_raw_files: bool = False      

    # --- Video Settings ---
    video_codec: str = "nvenc_h265"   # Nvidia GPU. Use "x265" for CPU.
    video_quality: str = "23"         # RF Value
    video_codec_preset: str = "p5"    # NVENC Preset

    # --- Audio Settings ---
    audio_codec: str = "av_aac"
    audio_quality: str = "0.6"        
    audio_mixdown: str = "7point1"

# Create a singleton instance to be imported by other modules
cfg = Configuration()