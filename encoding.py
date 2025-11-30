# encoding.py
import threading
from pathlib import Path
from config import cfg
import utils

class EncodeWorker(threading.Thread):
    def __init__(self, queue, handbrake_bin):
        super().__init__(daemon=True)
        self.queue = queue
        self.hb_bin = handbrake_bin

    def run(self):
        """
        The Immortal Loop. Catches all errors to keep the thread alive.
        """
        while True:
            job = self.queue.get()
            if job is None: 
                self.queue.task_done()
                break
            
            try:
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

    def process_job(self, input_path: Path, label: str, log_path: Path):
        dest_dir = cfg.encoded_directory / utils.sanitize_filename(label)
        utils.ensure_directory(dest_dir)
        output_mp4 = dest_dir / (input_path.stem + ".mp4")

        utils.console(f"Encoding: {input_path.name}")
        utils.append_log_line(log_path, f"ENC START {input_path}")

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