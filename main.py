import os
import sys
import json
import time
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from colorama import init as colorama_init
from rich.console import Console # pyright: ignore[reportMissingImports]
from rich.live import Live # pyright: ignore[reportMissingImports]
from rich.panel import Panel # pyright: ignore[reportMissingImports]

# === Init Colorama & Rich Console ===
colorama_init()
console = Console()

# === Time Formatting ===
def fmt_time(dt): return dt.strftime("%d-%m-%y %I:%M:%S %p")
def fmt_hms(seconds): return str(timedelta(seconds=int(seconds)))

# === User Input ===
mbox_path = input("Enter full path to your MBOX file: ").strip()
output_dir = Path(input("Enter output directory (default 'split_output'): ").strip() or "split_output")
messages_per_file = int(input("Messages per file? (default 1000): ") or "1000")

# === Setup ===
output_dir.mkdir(exist_ok=True)
log_file = output_dir / "split.log"
progress_file = output_dir / "progress.json"

# === Logging Setup ===
live_logs = []
MAX_LIVE_LINES = 3
realtime_started = False

def log(msg, realtime=False):
    global realtime_started, live_logs

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

    if realtime:
        live_logs.append(msg)
        if len(live_logs) > MAX_LIVE_LINES:
            live_logs = live_logs[-MAX_LIVE_LINES:]
        if not realtime_started:
            realtime_started = True
        live.update(Panel("\n".join(live_logs), title="Real-Time Logging"))
    else:
        if realtime_started:
            live.update(Panel("", title="Real-Time Logging"))
            realtime_started = False
        console.print(msg)

# === Validate MBOX File ===
if not os.path.isfile(mbox_path):
    log(f"[ERROR] MBOX file not found: {mbox_path}")
    sys.exit(1)

# === Load Progress ===
last_written = 0
last_byte = 0
if progress_file.exists():
    try:
        with open(progress_file, "r") as f:
            prog = json.load(f)
            last_written = prog.get("last_message", 0)
            last_byte = prog.get("last_byte", 0)
            log(f"[RESUME] Last written message: {last_written}")
    except Exception as e:
        # Try .bak fallback
        try:
            with open(progress_file.with_suffix(".bak"), "r") as f:
                prog = json.load(f)
                last_written = prog.get("last_message", 0)
                last_byte = prog.get("last_byte", 0)
                log(f"[RESUME] Used fallback .bak progress file")
        except Exception as e2:
            log(f"[WARNING] Failed to load progress file: {e2}")

# === Timer ===
start_dt = datetime.now()
start_time = time.time()
log(f"\nStart time               : {fmt_time(start_dt)}")
log(f"[START] Splitting MBOX     : {mbox_path}")
log(f"[CONFIG] Output dir        : {output_dir.resolve()}")
log(f"[CONFIG] Messages per file : {messages_per_file}")
log(f"[CONFIG] Resume from message #{last_written} at byte {last_byte}")
log(f"------------------------------------------------------------------------------")

# === Output State ===
msg_count = 0
part = (last_written // messages_per_file) + 1
file_msg_start = last_written + 1
current_msg_lines = []
out_file = None

def open_output_file(index):
    path = output_dir / f"part_{index}.mbox"
    return open(path, "w", encoding="utf-8", errors="ignore")

def safe_replace(src, dst, retries=10, delay=0.5):
    backup = dst.with_suffix('.bak')
    for i in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            time.sleep(delay)
    try:
        # If failed after retries, move to .bak so we don’t lose progress
        os.replace(src, backup)
        console.print(f"[yellow]⚠ Could not replace {dst}, wrote to fallback: {backup}[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Failed to write progress file fallback: {e}[/red]")

with Live(console=console, refresh_per_second=5) as live:
    try:
        with open(mbox_path, "r", encoding="utf-8", errors="ignore") as f:
            offset = 0
            msg_count = 0
            current_msg_lines = []
            writing = False

            if last_byte > 0:
                f.seek(last_byte)

            out_file = open_output_file(part)

            for line in f:
                if line.startswith("From "):
                    if writing:
                        out_file.writelines(current_msg_lines)
                        msg_count += 1
                        log(f"[WRITE] Message #{msg_count} written to {out_file.name}", realtime=True)

                        if msg_count % messages_per_file == 0:
                            out_file.close()
                            part += 1
                            out_file = open_output_file(part)
                            log(f"\n[INFO] Creating part_{part}.mbox...")

                        current_msg_lines = []

                    current_offset = offset
                    writing = True

                if writing:
                    current_msg_lines.append(line)
                offset += len(line)

    except KeyboardInterrupt:
        log("\n[INTERRUPTED] Script manually stopped.")

        try:
            current_offset = offset
        except Exception:
            current_offset = 0

        with tempfile.NamedTemporaryFile("w", delete=False, dir=output_dir, encoding="utf-8") as tmp:
            json.dump({"last_message": msg_count, "last_byte": current_offset}, tmp)
            tmp.flush()
        safe_replace(Path(tmp.name), Path(progress_file))

        if out_file:
            out_file.close()
        sys.exit(0)

    except Exception as e:
        log(f"[ERROR] Unexpected error: {e}")

        try:
            current_offset = offset
        except Exception:
            current_offset = 0

        with tempfile.NamedTemporaryFile("w", delete=False, dir=output_dir, encoding="utf-8") as tmp:
            json.dump({"last_message": msg_count, "last_byte": current_offset}, tmp)
            tmp.flush()
        safe_replace(Path(tmp.name), Path(progress_file))

        log(f"[PROGRESS] Resume point saved at message #{msg_count}, byte {current_offset}")

        if out_file:
            out_file.close()
        sys.exit(1)

# === Finalization ===
if out_file:
    out_file.flush()
    out_file.close()
    log(f"[INFO] ➔ Final file 'part_{part}.mbox' written: messages {file_msg_start} to {msg_count}")

with open(progress_file, "w") as f:
    json.dump({"last_message": msg_count, "last_byte": offset}, f)

end_dt = datetime.now()
elapsed = time.time() - start_time

log(f"\n✅ Done!")
log(f"Messages written : {msg_count}")
log(f"Files created    : {part}")
log(f"Start time       : {fmt_time(start_dt)}")
log(f"End time         : {fmt_time(end_dt)}")
log(f"Elapsed time     : {fmt_hms(elapsed)}")
log(f"[LOG] Saved to   : {log_file}")
