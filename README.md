# Archivium

Archivium is a lightweight desktop tool to quickly ingest and organize photos and videos from SD cards or folders. It separates media by type (JPEG, RAW, Video) into a dated session folder and optionally moves files from the source.

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

If `customtkinter` is installed, Archivium uses the modern CTk theme; otherwise it falls back to ttk.

## Usage
1. Click the folder button next to Destination to choose your default output.
2. Select Source (SD/Folder).
3. Toggle "Move instead of copy" if you want files deleted from the source.
4. Click "Organize" to start the transfer; it changes to "Cancel" while copying.
5. Use "Show log" to show/hide the logs panel.

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
├── img/logo.PNG   # App icon used in header and window icon
├── img/logo.ico   # Generated automatically for packaging (if Pillow available)
├── requirements.txt
├── .gitignore
└── README.md
```

## Build Executable

Archivium includes an automated build script to create a standalone executable.

### Option 1: Automated Build (Recommended)
Use the included build script for a complete automated process:

```bash
python build.py
```

This script will:
- Clean previous build directories
- Create a single executable file using PyInstaller
- Include all necessary dependencies and assets
- Generate a `release/` folder with the executable and documentation
- Clean up temporary build artifacts automatically

The final executable will be available at `release/Archivium.exe`.

### Option 2: Manual Build
If you prefer to build manually:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Ensure `img/logo.PNG` exists. The app will create `img/logo.ico` automatically if Pillow is installed.

3. Build with PyInstaller:
   ```bash
   pyinstaller --onefile --windowed --name=Archivium --icon=img/logo.ico --add-data=img;img --hidden-import=customtkinter --hidden-import=tkinter --hidden-import=PIL --clean main.py
   ```

4. The executable will be created in the `dist/` folder.

### Icon Generation
If `img/logo.ico` does not exist, you can convert the PNG using this Python command (requires Pillow):
```python
from PIL import Image; im=Image.open('img/logo.PNG').convert('RGBA'); im.save('img/logo.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
```

## Notes
- If `Pillow` or `customtkinter` are not installed, the app will gracefully disable related features.