#  Auto_MKBrake
#  Copyright (C) 2025 [Your Name]
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.


# main.py
import time
import queue
from datetime import datetime
from pathlib import Path

from config import cfg
import utils
import disc_ops
from encoding import EncodeWorker

def parse_selection(selection: str, valid_ids: list) -> list:
    s = selection.lower().replace(" ", "")
    if s == "all": return valid_ids
    if not s: return []
    res = set()
    for part in s.split(','):
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                res.update(range(start, end + 1))
            except ValueError: pass
        elif part.isdigit():
            res.add(int(part))
    return sorted(list(res.intersection(valid_ids)))

def main():
    try:
        mkv_bin = utils.resolve_binary(cfg.makemkv_path, "makemkvcon64")
        hb_bin = utils.resolve_binary(cfg.handbrake_path, "HandBrakeCLI")
    except Exception as e:
        utils.console(f"Setup Error: {e}"); return

    q = queue.Queue()
    # Start the worker threads
    workers = [EncodeWorker(q, hb_bin) for _ in range(cfg.encoder_worker_threads)]
    for w in workers: w.start()

    utils.console(f"AutoRipper Active. Waiting for discs in {cfg.drive_letter}...")

    try:
        while True:
            # --- Polling Loop ---
            try:
                while not disc_ops.is_disc_present(cfg.drive_letter): 
                    time.sleep(2)
            except KeyboardInterrupt: raise
            except Exception: time.sleep(2); continue 
            
            try:
                # --- Disc Detection ---
                disc_lbl = disc_ops.get_disc_volume_label(cfg.drive_letter)
                safe_lbl = utils.sanitize_filename(disc_lbl)
                raw_dir = cfg.raw_directory / safe_lbl
                utils.ensure_directory(raw_dir)
                
                # Create a fresh log file for this session
                log_path = raw_dir / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

                utils.console(f"Disc Found: {disc_lbl}")
                titles = disc_ops.list_disc_titles(mkv_bin, cfg.drive_letter)
                valid_ids = [t["ID"] for t in titles]

                if not valid_ids:
                    utils.console("No valid titles found.")
                    disc_ops.eject_disc(cfg.drive_letter)
                    time.sleep(5); continue

                # --- User Interaction ---
                print(f"\n{'='*40}\n DISC: {disc_lbl}\n{'='*40}")
                print(f" {'ID':<4} | {'Length':<10} | {'Size':<10}")
                print(f" {'-'*4} + {'-'*10} + {'-'*10}")
                for t in titles:
                    print(f" {t['ID']:<4} | {t['Length']:<10} | {t['Size']:<10}")
                print(f"{'='*40}")
                
                sel = input("\nEnter IDs to rip (e.g. 0,1 or 1-4 or all): ")
                chosen = parse_selection(sel, valid_ids)

                # --- Ripping Loop ---
                if chosen:
                    for t_id in chosen:
                        try:
                            mkv = disc_ops.rip_title(mkv_bin, cfg.drive_letter, raw_dir, t_id, log_path)
                            # Pass the file to the encoding queue
                            q.put((mkv, disc_lbl, log_path))
                        except Exception as e:
                            utils.console(f"RIP ERROR on ID {t_id}: {e}")
                            utils.append_log_line(log_path, f"RIP FAIL t{t_id}: {e}")
                    
                    if cfg.eject_on_completion:
                        utils.console("Ripping complete. Ejecting...")
                        disc_ops.eject_disc(cfg.drive_letter)
                else:
                    utils.console("Selection skipped.")
                    disc_ops.eject_disc(cfg.drive_letter)

            except Exception as e:
                utils.console(f"MAIN LOOP ERROR: {e}")
                disc_ops.eject_disc(cfg.drive_letter)
                time.sleep(5)

            # Wait for physical removal
            while disc_ops.is_disc_present(cfg.drive_letter): time.sleep(2)

    except KeyboardInterrupt:
        utils.console("Stopping...")
        for _ in workers: q.put(None)
        for w in workers: w.join()

if __name__ == "__main__":
    main()