# Archivium

Archivium is a desktop tool to ingest and organize photos and videos by copying or moving content from a source folder (e.g., an SD card) into a consistent, easy-to-browse destination structure.

## Features
- Select destination and source folders easily
- Creates session folders by date with incremental numbering
- Separates media into `JPEG`, `RAW`, and `Video` subfolders
- Optionally move files from source (instead of copying)
- Simple logs panel to monitor progress
- CustomTkinter or classic ttk UI (auto-detected)
- Cancel ongoing transfers and hide progress bar when idle

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

## What’s New in 1.2.0
- Destination organization modes:
  - Classic Session (default): creates `YYYY-MM-DD_XX` with `JPEG/`, `RAW/`, `VIDEO/` subfolders.
  - Chronological (Date First): groups by capture date, then by file type.
  - Collections (Type First): groups by file type, then by date.
- New typographic hierarchy and Modern UI styles (CustomTkinter when available).
- Optimized transfer and expanded format support (`HEIC/HEIF`, `WEBP`, `SVG`, `ICO`, `TIFF`, etc.).

If `customtkinter` is installed, Archivium uses the modern CTk theme; otherwise it falls back to ttk.

## Quick Start
- Select `Destination` (remembered as default) and `Source`.
- Toggle `Move` if you want to move instead of copy.
- Click `Organize`.
- Open `⚙️` Settings to choose **Folder Organization Mode**:
  - `Classic Session` (default)
  - `Chronological (Date First)`
  - `Collections (Type First)`
- The activity log and progress bar show real-time transfer details.

## Configuration
- Location: `%APPDATA%/Archivium/config.json`
- Keys:
  - `default_dest`: default destination folder.
  - `theme`: `light`, `dark`, `system` (Windows auto-detection when using `system`).
  - `organize_mode`: `current` (Classic Session), `date_then_type`, `type_then_date`.
- The app remembers the last chosen destination and the selected organization mode.

## Project Structure
```
Archivium/
├── main.py        # App logic and UI (CTk/ttk)
├── styles.py      # Centralized styles and fonts
├── img/logo.PNG   # Icon used in header and window
├── img/logo.ico   # Generated automatically if Pillow is available
├── requirements.txt
├── .gitignore
└── README.md
```

## Build Executable
Archivium includes an automated build script.

### Option 1: Automated Build (recommended)

```bash
python build.py
```

This script:
- Cleans previous build directories
- Creates a single executable using PyInstaller
- Includes required dependencies and assets
- Generates `release/` with the executable and documentation
- Cleans temporary build artifacts automatically

The final executable is available at `release/Archivium.exe`.

### Option 2: Manual Build
1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Ensure `img/logo.PNG` exists. If Pillow is installed, the app will create `img/logo.ico` automatically.
3. Build:
   ```bash
   pyinstaller --onefile --windowed --name=Archivium --icon=img/logo.ico --add-data=img;img --hidden-import=customtkinter --hidden-import=tkinter --hidden-import=PIL --clean main.py
   ```
4. The executable is created in `dist/`.

### Icon Generation
If `img/logo.ico` does not exist, you can convert the PNG using Python (requires Pillow):
```python
from PIL import Image; im=Image.open('img/logo.PNG').convert('RGBA'); im.save('img/logo.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
```

## Notes
- If `Pillow` or `customtkinter` are not installed, the app gracefully disables related features.
- Requirements (`requirements.txt`): `customtkinter>=5.2.2`, `Pillow>=10.0.0`, `PyInstaller>=5.10.1`.