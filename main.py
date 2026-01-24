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
        
        utils.console("Checking MakeMKV license status...")
        disc_ops.verify_license(mkv_bin)
        utils.console("License check passed.")
        
    except Exception as e:
        utils.console(f"Setup Error: {e}"); return

    q = queue.Queue()
    workers = [EncodeWorker(q, hb_bin) for _ in range(cfg.encoder_worker_threads)]
    for w in workers: w.start()

    utils.console(f"Auto_MKBrake Active. Waiting for discs in {cfg.drive_letter}...")

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
                print(f" {'Index':<5} | {'Length':<10} | {'Size':<10}")
                print(f" {'-'*5} + {'-'*10} + {'-'*10}")
                for t in titles:
                    print(f" {t['ID']:<5} | {t['Length']:<10} | {t['Size']:<10}")
                print(f"{'='*40}")
                print(f"Tracks are filtered for your convenience. Minimum length to display {cfg.min_title_length//60} minutes.\n")
                print("""You may find that there is one long track either at the first or last index, that is a total time of all titles on the disc.
                      This is usually an attempt at obfuscation and is difficult to filter out, you should avoid ripping it.""")
                
                sel = input("\nEnter selection to rip (e.g. 0,1 or 1-4 or all): ")
                chosen = parse_selection(sel, valid_ids)

                # --- Ripping Loop ---
                if chosen:
                    for t_index in chosen:
                        try:
                            # Retrieve full info for verbose logging
                            target_title = next(t for t in titles if t['ID'] == t_index)
                            
                            # Pass full info to ripper
                            mkv = disc_ops.rip_title(mkv_bin, cfg.drive_letter, raw_dir, target_title, disc_lbl, log_path)
                            
                            # Pass full info to encoder
                            q.put((mkv, disc_lbl, log_path, target_title))
                        except Exception as e:
                            utils.console(f"RIP ERROR on Track {t_index}: {e}")
                            utils.append_log_line(log_path, f"RIP FAIL Track {t_index}: {e}")
                    
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

            while disc_ops.is_disc_present(cfg.drive_letter): time.sleep(2)

    except KeyboardInterrupt:
        utils.console("Stopping...")
        for _ in workers: q.put(None)
        for w in workers: w.join()

if __name__ == "__main__":
    main()