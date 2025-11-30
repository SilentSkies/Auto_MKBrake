import threading
from pathlib import Path
from typing import Dict, Optional
from config import cfg
import utils

class EncodeWorker(threading.Thread):
    def __init__(self, queue, handbrake_bin):
        super().__init__(daemon=True)
        self.queue = queue
        self.hb_bin = handbrake_bin

    def run(self):
        while True:
            job = self.queue.get()
            if job is None: 
                self.queue.task_done()
                break
            
            try:
                # Unpack the job. 
                # We use *job to handle cases where title_info might be missing (legacy/batch scripts)
                self.process_job(*job)
            except Exception as e:
                # CATCH-ALL: This prevents the thread from dying
                mkv_path = job[0]
                log_path = job[2]
                error_msg = f"CRITICAL WORKER CRASH on {mkv_path.name}: {e}"
                utils.console(error_msg)
                utils.append_log_line(log_path, error_msg)
            finally:
                self.queue.task_done()

    def process_job(self, input_path: Path, label: str, log_path: Path, title_info: Optional[Dict] = None):
        dest_dir = cfg.encoded_directory / utils.sanitize_filename(label)
        utils.ensure_directory(dest_dir)
        output_mp4 = dest_dir / (input_path.stem + ".mp4")

        # Verbose Output
        if title_info:
            msg = f"Encoding: {label} Track {title_info['ID']} ({title_info['Length']} / {title_info['Size']})"
        else:
            msg = f"Encoding: {label} ({input_path.name})"

        utils.console(msg)
        utils.append_log_line(log_path, f"ENC START {msg}")

        args = [
            "-i", str(input_path),
            "-o", str(output_mp4),
            "-f", "av_mp4",
            "-e", cfg.video_codec,
            "-q", cfg.video_quality,
            "--encoder-preset", cfg.video_codec_preset,
            "--optimize", "--auto-anamorphic", "--modulus", "2",
            "--all-audio",
            "--mixdown", cfg.audio_mixdown, 
            "--aencoder", cfg.audio_codec, 
            "--aq", cfg.audio_quality,
            "--subtitle", "none"
        ]

        # Run with LOW priority to protect the Ripping process
        rc = utils.run_stream_log(self.hb_bin, args, log_path, low_priority=True)

        if rc == 0:
            utils.console(f"Finished: {output_mp4.name}")
            utils.append_log_line(log_path, "ENC SUCCESS")
            if not cfg.keep_raw_files and output_mp4.stat().st_size > 1024:
                try: input_path.unlink()
                except OSError: pass
        else:
            utils.console(f"Failed: {input_path.name}")
            utils.append_log_line(log_path, f"ENC FAIL rc={rc}")