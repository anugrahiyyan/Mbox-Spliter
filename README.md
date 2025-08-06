# 📬 MBOX Splitter with Logging & Robust Handling

A Python script to split large `.mbox` email archives into smaller parts with:

- ✅ Resume support
- 📝 Real-time and file logging
- 🧠 Progress tracking (`progress.json`)
- 💥 Safe KeyboardInterrupt handling
- 🛡️ Atomic file operations with temp+replace
- 🖥️ Windows-friendly error recovery

---

## 📦 Requirements

Install dependencies via pip:

```bash
pip install colorama rich
```

## 🛠️ How to Use

Run the script:

```bash
python main.py
```

You will be prompted to input:

```bash
Enter full path to your MBOX file: Input your file location
Enter output directory (default 'split_output'): Save as to
Messages per file? (default 1000): 
```

# ✅ Sample Output Log

```bash
[START] Splitting MBOX: I:\Emails\backup.mbox
[CONFIG] Output dir: N:\MboxChunks
[CONFIG] Messages per file: 1000
[WRITE] Message #1 written to part_1.mbox
[WRITE] Message #2 written to part_1.mbox
[INFO] Creating part_2.mbox...
✅ Done!
Messages written : 3456
Files created    : 4
```