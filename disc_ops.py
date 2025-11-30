# disc_ops.py
import re
import ctypes
import subprocess
import time
from typing import List, Dict
from pathlib import Path

from config import cfg
import utils

# Compiled regex for parsing
_DURATION_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$")
_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([GMK]i?B)\s*$", re.IGNORECASE)

def get_disc_volume_label(drive_letter: str) -> str:
    root = f"{drive_letter}\\"
    volume_name = ctypes.create_unicode_buffer(261)
    try:
        ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root), volume_name, ctypes.sizeof(volume_name),
            None, None, None, None, 0
        )
        return volume_name.value
    except Exception:
        return ""

def is_disc_present(drive_letter: str) -> bool:
    return bool(get_disc_volume_label(drive_letter))

def eject_disc(drive_letter: str) -> None:
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
    match = _DURATION_RE.fullmatch((value or "").strip())
    if not match: return 0
    return int(match.group(1))*3600 + int(match.group(2))*60 + int(match.group(3) or 0)

def list_disc_titles(makemkv_bin: str, drive_letter: str) -> List[Dict]:
    cmd = [makemkv_bin, "-r", "--cache=1", "info", f"dev:{drive_letter}"]
    try:
        # We don't use run_stream_log here because we need to parse the output in memory
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
                t_id = int(parts[0].split(':')[1])
                code = int(parts[1])
                val = parts[3].strip('"')
                if code == 9: per_title.setdefault(t_id, {})["duration"] = val
                elif code == 10: per_title.setdefault(t_id, {})["size"] = val
            except ValueError: continue

    titles = []
    for t_id in sorted(per_title.keys()):
        d = per_title[t_id]
        dur = d.get("duration", "")
        size = d.get("size", "")
        if _SIZE_RE.match(dur) and _DURATION_RE.match(size): dur, size = size, dur
        
        titles.append({
            "ID": t_id,
            "TitleName": f"{utils.sanitize_filename(disc_label)}_t{t_id:02d}",
            "Length": dur,
            "Size": size,
            "Seconds": parse_duration(dur)
        })
    
    # Filter junk (< 5 mins)
    return [t for t in titles if t["Seconds"] > 300]

def rip_title(mkv_bin: str, drive: str, dest: Path, t_id: int, log: Path) -> Path:
    utils.ensure_directory(dest)
    args = ["mkv", f"dev:{drive}", str(t_id), str(dest), "--decrypt", "--cache=1024", "--minlength=300"]
    
    utils.console(f"Ripping: Title {t_id}")
    utils.append_log_line(log, f"RIP START t{t_id}")
    
    # Ripping happens at Normal priority
    rc = utils.run_stream_log(mkv_bin, args, log, low_priority=False)
    
    if rc != 0:
        raise RuntimeError(f"MakeMKV exited with code {rc}")
        
    mkvs = sorted(dest.glob(f"*t{t_id:02d}*.mkv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mkvs: mkvs = sorted(dest.glob("*.mkv"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not mkvs: raise FileNotFoundError("Rip finished but file not found")
    return mkvs[0]