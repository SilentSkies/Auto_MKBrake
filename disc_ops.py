import re
import ctypes
import subprocess
import time
from typing import List, Dict
from pathlib import Path

from config import cfg
import utils

# Compiled regex for parsing MakeMKV output
_DURATION_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$")
_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([GMK]i?B)\s*$", re.IGNORECASE)

def verify_license(makemkv_bin: str) -> None:
    """
    Runs a quick drive scan to trigger MakeMKV's license validation.
    Raises RuntimeError if the license is expired or invalid.
    """
    # 'info' with '-r' scans for drives. This is enough to trigger the license check
    # without needing a disc in the tray.
    cmd = [makemkv_bin, "-r", "info"]
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    except Exception as e:
        raise RuntimeError(f"Could not execute MakeMKV for license check: {e}")

    output_combined = (result.stdout or "") + (result.stderr or "")
    
    # Common MakeMKV expiry messages
    if "evaluation period has expired" in output_combined.lower():
        raise RuntimeError("MakeMKV Evaluation Period has EXPIRED. Please update the key.")
    if "key is invalid" in output_combined.lower():
        raise RuntimeError("MakeMKV Registration Key is INVALID.")
    if "version is too old" in output_combined.lower():
        raise RuntimeError("MakeMKV version is too old. Please update the application.")

def get_disc_volume_label(drive_letter: str) -> str:
    """Gets the volume label (e.g., 'WESTWORLD_S1_D1') using Windows API."""
    root = f"{drive_letter}\\"
    volume_name = ctypes.create_unicode_buffer(261)
    try:
        ctypes.windll.kernel32.GetVolumeInformationW( # type: ignore
            ctypes.c_wchar_p(root), volume_name, ctypes.sizeof(volume_name),
            None, None, None, None, 0
        )
        return volume_name.value
    except Exception:
        return ""

def is_disc_present(drive_letter: str) -> bool:
    return bool(get_disc_volume_label(drive_letter))

def eject_disc(drive_letter: str) -> None:
    """Ejects the tray using PowerShell."""
    try:
        subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                r"(New-Object -ComObject Shell.Application).NameSpace(17).ParseName('{}').InvokeVerb('Eject')".format(drive_letter)
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
        )
    except Exception:
        pass

def parse_duration(value: str) -> int:
    """Converts HH:MM:SS string to total seconds."""
    match = _DURATION_RE.fullmatch((value or "").strip())
    if not match: return 0
    return int(match.group(1))*3600 + int(match.group(2))*60 + int(match.group(3) or 0)

def list_disc_titles(makemkv_bin: str, drive_letter: str) -> List[Dict]:
    """
    Scans the disc, filters internally, and returns a CLEAN, SEQUENTIAL list.
    The ID returned here (0, 1, 2...) matches exactly what MakeMKV expects
    when the --minlength flag is used.
    """
    # 1. Scan EVERYTHING (no filter yet) to get raw data
    cmd = [makemkv_bin, "-r", "--cache=1", "info", f"dev:{drive_letter}"]
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    except Exception:
        return []

    if result.returncode != 0: return []

    disc_label = get_disc_volume_label(drive_letter)
    per_title: Dict[int, Dict] = {}

    # 2. Parse raw output
    for line in result.stdout.splitlines():
        if line.startswith("TINFO:"):
            parts = line.split(',', 3)
            if len(parts) < 4: continue
            try:
                # This is the Raw Source ID (e.g. 0, 1, 2, 9...)
                t_source_id = int(parts[0].split(':')[1]) 
                code = int(parts[1])
                val = parts[3].strip('"')
                
                if code == 9: per_title.setdefault(t_source_id, {})["duration"] = val
                elif code == 10: per_title.setdefault(t_source_id, {})["size"] = val
                elif code == 27: per_title.setdefault(t_source_id, {})["filename"] = val
            except ValueError: continue

    # 3. Build the preliminary list
    raw_titles = []
    for t_source_id in sorted(per_title.keys()):
        d = per_title[t_source_id]
        dur = d.get("duration", "")
        size = d.get("size", "")
        filename = d.get("filename", f"t{t_source_id:02d}.mkv") # Use source ID for filename hint
        
        if _SIZE_RE.match(dur) and _DURATION_RE.match(size): dur, size = size, dur
        
        raw_titles.append({
            "RawID": t_source_id,
            "TitleNameHint": f"{utils.sanitize_filename(disc_label)}_{filename}",
            "Length": dur,
            "Size": size,
            "Seconds": parse_duration(dur)
        })

    # 4. FILTER and RE-INDEX
    # This simulates exactly what MakeMKV does when --minlength is passed.
    valid_titles = []
    filtered_index = 0
    
    for t in raw_titles:
        if t["Seconds"] >= cfg.min_title_length:
            # We assign a NEW sequential ID (0, 1, 2...)
            t["ID"] = filtered_index 
            t["TitleName"] = t["TitleNameHint"] # Keep the name derived from original ID
            valid_titles.append(t)
            filtered_index += 1
            
    return valid_titles

def rip_title(mkv_bin: str, drive: str, dest: Path, title_info: Dict, disc_label: str, log: Path) -> Path:
    """
    Rips the specific title using the Raw Source ID to ensure accuracy.
    """
    utils.ensure_directory(dest)
    
    # CHANGE 1: Use the RawID (absolute index) instead of the filtered ID
    t_index = title_info['RawID'] 
    
    # CHANGE 2: Remove "--minlength" so MakeMKV uses the absolute index
    args = [
        "mkv", f"dev:{drive}", str(t_index), str(dest), 
        "--decrypt", 
        "--cache=1024"
        # "--minlength" REMOVED to prevent indexing misalignment
    ]
    
    # Detailed Console Output
    msg = f"Ripping: {disc_label} Track {t_index} ({title_info['Length']} / {title_info['Size']})"
    utils.console(msg)
    utils.append_log_line(log, f"RIP START {msg}")
    
    rc = utils.run_stream_log(mkv_bin, args, log, low_priority=False)
    
    if rc != 0:
        raise RuntimeError(f"MakeMKV exited with code {rc}")
        
    # Scan for the newest file
    mkvs = sorted(dest.glob("*.mkv"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not mkvs: raise FileNotFoundError("Rip finished but file not found")
    return mkvs[0]