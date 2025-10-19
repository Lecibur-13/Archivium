# Archivium

Archivium is a lightweight desktop tool to quickly ingest and organize photos and videos from SD cards or folders. It separates media by type (JPEG, RAW, Video) into a dated session folder and optionally moves files from the source.

## Features
- Select destination and source folders easily
- Creates session folders by date with incremental numbering
- Separates media into `JPEG`, `RAW`, and `Video` subfolders
- Optionally move files from source (instead of copying)
- Simple logs panel to monitor progress
- Format SD card on Windows (PowerShell `Format-Volume`)
- CustomTkinter or classic ttk UI (auto-detected)

## Requirements
- Python 3.10+
- Windows (for SD formatting); copy-only works on any OS
- Dependencies:
  - `customtkinter>=5.2.2` (optional but recommended)
  - `Pillow>=10.0.0` (optional, for folder icon rendering)

Install with:
```
pip install -r requirements.txt
```

## Run
```
python main.py
```

If `customtkinter` is installed, Archivium uses the modern CTk theme; otherwise it falls back to ttk.

## Usage
1. Click the folder button next to Destination to choose your default output.
2. Select Source (SD/Folder).
3. Toggle "Move instead of copy" if you want files deleted from the source.
4. Click "Organize" to transfer media into a new session directory.
5. Once done, you may click "Format SD" to format the detected SD drive (Windows only).
6. Use "Show log" to show/hide the logs panel.

## Session Naming
- Session folder name format: `YYYY-MM-DD_XX`, where `XX` increments from 01.
- Inside the session: `JPEG/`, `RAW/`, `Video/` subfolders.

## Configuration
- Config is stored at `%APPDATA%/Archivium/config.json` with the key `default_dest`.
- The app remembers your last chosen destination.

## Project Structure
```
photo_organizer/
├── main.py        # App logic and UI
├── styles.py      # Centralized styles and fonts for CTk/ttk
├── requirements.txt
├── .gitignore
└── README.md
```

## Publish to GitHub
1. Initialize git and make your first commit:
   - `git init`
   - `git add .`
   - `git commit -m "Initial commit: Archivium"`
2. Create a GitHub repo named `Archivium`.
3. Add remote and push:
   - `git remote add origin https://github.com/<your-username>/Archivium.git`
   - `git push -u origin main`

## Notes
- Formatting SD uses PowerShell and requires admin privileges depending on system policy.
- On non-Windows systems, the "Format SD" button will not work.
- If `Pillow` or `customtkinter` are not installed, the app will gracefully disable related features.