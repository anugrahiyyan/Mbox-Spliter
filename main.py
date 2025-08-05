import mailbox
from pathlib import Path
from tqdm import tqdm
import os
import time
import json
import sys

# === Logging Setup ===
def log(msg):
    print(msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# === User Input ===
mbox_path = input("Enter full path to your MBOX file: ").strip()
output_dir = Path(input("Enter output directory (default 'split_output'): ").strip() or "split_output")
messages_per_file = int(input("Messages per file? (default 1000): ") or "1000")

# === Paths & Files ===
log_file = output_dir / "split.log"
progress_file = output_dir / "progress.json"

output_dir.mkdir(exist_ok=True)
log_file.touch(exist_ok=True)

# === Validate Input ===
if not os.path.isfile(mbox_path):
    log(f"[ERROR] MBOX file not found: {mbox_path}")
    sys.exit(1)

# === Load Previous Progress ===
if progress_file.exists():
    with open(progress_file, "r") as f:
        progress_data = json.load(f)
        last_written = progress_data.get("last_message", 0)
        log(f"[RESUME] Last written message: {last_written}")
else:
    last_written = 0

# === Start Timer ===
start_time = time.time()
log(f"\n[START] Splitting MBOX: {mbox_path}")
log(f"[CONFIG] Output dir: {output_dir.resolve()}")
log(f"[CONFIG] Messages per file: {messages_per_file}")

# === Open MBOX ===
mbox = mailbox.mbox(mbox_path)
total_messages = sum(1 for _ in mbox)

# === Start Splitting ===
message_count = 0
file_index = (last_written // messages_per_file) + 1
file_message_start = last_written + 1
out_mbox = None

try:
    for i, message in enumerate(tqdm(mbox, total=total_messages, desc="Processing", unit="msg")):
        if i < last_written:
            continue  # Skip already processed

        if message_count % messages_per_file == 0:
            if out_mbox:
                out_mbox.flush()
                out_mbox.close()
                log(f"[INFO] ➜ File 'part_{file_index - 1}.mbox' written: messages {file_message_start} to {message_count}")

            output_path = output_dir / f"part_{file_index}.mbox"
            out_mbox = mailbox.mbox(output_path, create=True)
            file_message_start = message_count + 1
            file_index += 1
            log(f"[INFO] Creating '{output_path.name}'...")

        try:
            out_mbox.add(message)
        except Exception as e:
            log(f"[WARNING] Failed to add message #{i}: {e}")

        message_count += 1
        # Save progress every 100 messages
        if message_count % 100 == 0:
            with open(progress_file, "w") as f:
                json.dump({"last_message": i}, f)

    # Final flush
    if out_mbox:
        out_mbox.flush()
        out_mbox.close()
        log(f"[INFO] ➜ Final file 'part_{file_index - 1}.mbox' written: messages {file_message_start} to {message_count}")

    with open(progress_file, "w") as f:
        json.dump({"last_message": total_messages}, f)

except KeyboardInterrupt:
    log("\n[INTERRUPTED] Script manually stopped.")
    if out_mbox:
        out_mbox.flush()
        out_mbox.close()
    with open(progress_file, "w") as f:
        json.dump({"last_message": i}, f)

except Exception as e:
    log(f"[ERROR] Unexpected exception: {e}")
    if out_mbox:
        out_mbox.flush()
        out_mbox.close()

# === Done ===
elapsed = time.time() - start_time
log(f"\n✅ Done! Messages written: {message_count}")
log(f"⏱️ Time elapsed: {int(elapsed)} seconds")
log(f"[LOG] Saved to: {log_file}")