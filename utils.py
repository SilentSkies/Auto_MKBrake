# utils.py
import sys
import shutil
import threading
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Global lock ensures the console and log files don't get garbled
_LOG_LOCK = threading.Lock()
_INVALID_FILENAME_CHARS = re.compile(r'[^A-Za-z0-9._ \-]')

def current_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")

def console(message: str) -> None:
    """Thread-safe console printing."""
    with _LOG_LOCK:
        print(f"[{current_timestamp()}] {message}", flush=True)

def append_log_line(log_path: Path, message: str) -> None:
    """Thread-safe file appending."""
    with _LOG_LOCK:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"[{current_timestamp()}] {message}\n")
        except OSError:
            pass 

def ensure_directory(path_like: Path) -> None:
    path_like.mkdir(parents=True, exist_ok=True)

def sanitize_filename(name: str) -> str:
    return _INVALID_FILENAME_CHARS.sub("_", name)

def resolve_binary(path_cfg: Optional[str], binary_name: str) -> str:
    if path_cfg and Path(path_cfg).exists():
        return path_cfg
    system_path = shutil.which(binary_name)
    if system_path:
        return system_path
    raise FileNotFoundError(f"Missing executable: {binary_name}")

def run_stream_log(executable: str, args: List[str], log_path: Path, low_priority: bool = False) -> int:
    """
    Runs a subprocess and pipes output to a log file.
    Includes logic to set process priority to 'Below Normal' for encoding.
    """
    creation_flags = 0
    if low_priority and sys.platform == "win32":
        # Windows: BELOW_NORMAL_PRIORITY_CLASS (0x00004000)
        creation_flags = 0x00004000 

    with _LOG_LOCK:
        log_file_bin = log_path.open("ab")

    try:
        return subprocess.run(
            [executable] + args, 
            stdout=log_file_bin, 
            stderr=subprocess.STDOUT, 
            check=False,
            creationflags=creation_flags 
        ).returncode
    except Exception as e:
        try:
            log_file_bin.write(f"\nCRITICAL SUBPROCESS ERROR: {e}\n".encode())
        except: pass
        return 1
    finally:
        try:
            log_file_bin.close()
        except: pass