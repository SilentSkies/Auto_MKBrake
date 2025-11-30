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
    Scans the disc and returns a list of valid titles.
    Returns the Sequential Index (0, 1, 2...) as 'ID'.
    """
    cmd = [makemkv_bin, "-r", "--cache=1", "info", f"dev:{drive_letter}"]
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    except Exception:
        return []

    if result.returncode != 0: return []

    disc_label = get_disc_volume_label(drive_letter)
    per_title: Dict[int, Dict] = {}

    for line in result.stdout.splitlines():
        if line.startswith("TINFO:"):
            parts = line.split(',', 3)
            if len(parts) < 4: continue
            try:
                t_source_id = int(parts[0].split(':')[1]) 
                code = int(parts[1])
                val = parts[3].strip('"')
                
                if code == 9: per_title.setdefault(t_source_id, {})["duration"] = val
                elif code == 10: per_title.setdefault(t_source_id, {})["size"] = val
            except ValueError: continue

    titles = []
    
    # Sort by Source ID to determine the Sequential Index
    for index, t_source_id in enumerate(sorted(per_title.keys())):
        d = per_title[t_source_id]
        dur = d.get("duration", "")
        size = d.get("size", "")
        
        if _SIZE_RE.match(dur) and _DURATION_RE.match(size): dur, size = size, dur
        
        titles.append({
            "ID": index,     
            "TitleName": f"{utils.sanitize_filename(disc_label)}_t{index:02d}",
            "Length": dur,
            "Size": size,
            "Seconds": parse_duration(dur)
        })
    
    return [t for t in titles if t["Seconds"] > cfg.min_title_length]

def rip_title(mkv_bin: str, drive: str, dest: Path, title_info: Dict, disc_label: str, log: Path) -> Path:
    """
    Rips the specific title.
    Now accepts the full title_info dictionary for verbose logging.
    """
    utils.ensure_directory(dest)
    t_index = title_info['ID']
    
    args = [
        "mkv", f"dev:{drive}", str(t_index), str(dest), 
        "--decrypt", 
        "--cache=1024", 
        f"--minlength={cfg.min_title_length}"
    ]
    
    # Detailed Console Output
    msg = f"Ripping: {disc_label} Track {t_index} ({title_info['Length']} / {title_info['Size']})"
    utils.console(msg)
    utils.append_log_line(log, f"RIP START {msg}")
    
    # Normal priority for ripping
    rc = utils.run_stream_log(mkv_bin, args, log, low_priority=False)
    
    if rc != 0:
        raise RuntimeError(f"MakeMKV exited with code {rc}")
        
    mkvs = sorted(dest.glob(f"*t{t_index:02d}*.mkv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mkvs: mkvs = sorted(dest.glob("*.mkv"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not mkvs: raise FileNotFoundError("Rip finished but file not found")
    return mkvs[0]