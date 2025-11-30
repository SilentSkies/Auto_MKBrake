# process_raw_backlog.py
import queue
import time
from pathlib import Path
from datetime import datetime

# Import from your existing project files
from config import cfg
import utils
from encoding import EncodeWorker

def main():
    # 1. Verify Binaries
    try:
        hb_bin = utils.resolve_binary(cfg.handbrake_path, "HandBrakeCLI")
    except Exception as e:
        utils.console(f"Setup Error: {e}")
        return

    # 2. Check if GPU is actually enabled (Safety check based on your issue)
    if "nvenc" not in cfg.video_codec and "vce" not in cfg.video_codec:
        print(f"\nWARNING: video_codec is set to '{cfg.video_codec}'.")
        print("This will use the CPU. If you want GPU, check config.py now.")
        print("Waiting 5 seconds before starting...\n")
        time.sleep(5)

    # 3. Setup Workers
    job_queue = queue.Queue()
    workers = [EncodeWorker(job_queue, hb_bin) for _ in range(cfg.encoder_worker_threads)]
    for w in workers: 
        w.start()

    utils.console(f"Scanning {cfg.raw_directory} for un-encoded files...")

    # 4. Scan Raw Directory
    # Structure is usually: Raw / DiscLabel / title_t00.mkv
    found_jobs = 0
    
    if not cfg.raw_directory.exists():
        utils.console(f"Error: Raw directory not found at {cfg.raw_directory}")
        return

    # Walk through all subfolders in Raw
    for disc_folder in cfg.raw_directory.iterdir():
        if disc_folder.is_dir():
            disc_label = disc_folder.name
            
            # Find all MKVs in this folder
            for mkv_path in disc_folder.glob("*.mkv"):
                # Check if the encoded file already exists
                encoded_folder = cfg.encoded_directory / disc_label
                expected_mp4 = encoded_folder / (mkv_path.stem + ".mp4")

                if expected_mp4.exists():
                    # Skip it if it's already done
                    continue
                
                # It's missing! Queue it up.
                found_jobs += 1
                
                # Create a specific log file for this batch run
                log_path = disc_folder / f"batch_encode_{datetime.now().strftime('%Y%m%d')}.log"
                
                utils.console(f"Queuing: {disc_label} / {mkv_path.name}")
                job_queue.put((mkv_path, disc_label, log_path))

    if found_jobs == 0:
        utils.console("No pending raw files found. Everything looks encoded!")
    else:
        utils.console(f"Queued {found_jobs} files. Processing...")
        
        # Wait for queue to empty
        job_queue.join()
        
        # Cleanup threads
        for _ in workers: job_queue.put(None)
        for w in workers: w.join()
        
        utils.console("Batch processing complete.")

if __name__ == "__main__":
    main()