# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Archivium is a desktop application for ingesting and organizing media files (photos/videos) from SD cards or folders. Built with Electron + React + TypeScript + Tailwind CSS.

The Python original is preserved in `legacy/` for reference.

## Development Commands

```bash
npm install          # install dependencies
npm run dev          # start dev server (Electron + hot reload)
npm run build        # production build (all platforms output to dist/ & dist-electron/)
npm run build:win    # build + package Windows .exe
npm run build:linux  # build + package Linux .AppImage + .deb
npm run build:mac    # build + package macOS .dmg + .zip
```

Packaged outputs land in `release/`.

## Architecture

### Process Model (Electron)

```
electron/main/index.ts   → Node.js main process: file I/O, IPC handlers, window management
electron/preload/index.ts → context bridge: exposes window.api to renderer (safe IPC)
src/                     → Renderer process: React UI (no direct Node.js access)
```

**All file system operations happen in the main process.** The renderer sends requests via `window.api.*` IPC calls and receives progress/log events back.

### IPC Contract (`window.api`)

Defined in `electron/preload/index.ts`, typed in `src/types.ts`:

| Method | Direction | Purpose |
|--------|-----------|---------|
| `selectFolder()` | renderer → main | Opens OS folder dialog |
| `loadConfig()` / `saveConfig(cfg)` | renderer → main | Persistent config in userData |
| `startTransfer(options)` | renderer → main | Starts file transfer, resolves on completion |
| `cancelTransfer()` | renderer → main | Sets cancel flag |
| `onProgress(cb)` | main → renderer | Per-file progress stream |
| `onLog(cb)` | main → renderer | Activity log messages |
| `onComplete(cb)` | main → renderer | Transfer result `{ transferred, errors, cancelled }` |

### Business Logic (main process)

All in `electron/main/index.ts`:

- **File type detection**: extension lookup against three sets (JPEG/RAW/VIDEO)
- **EXIF date**: `exifr` library, falls back to `mtime`
- **File copy**: Node.js streams (`createReadStream` → `pipeline`) with per-chunk progress callbacks; timestamps preserved via `fs.utimes`
- **File move**: `fs.rename` (fast, same-drive) with fallback to copy+delete
- **Session folder naming**: `YYYY-MM-DD_NN` incremental, based on today's date
- **Unique filename**: appends `_N` suffix when destination already has the file
- **Cancellation**: module-level `cancelFlag` boolean checked at each file boundary

### Folder Organization Modes

| Mode key | Structure |
|----------|-----------|
| `classic` | `dest/YYYY-MM-DD_NN/JPEG\|RAW\|VIDEO/filename` |
| `date_then_type` | `dest/DD-MM-YYYY/JPEG\|RAW\|VIDEO/filename` |
| `type_then_date` | `dest/JPEG\|RAW\|VIDEO/DD-MM-YYYY/filename` |

Files are **always copied flat** — subdirectory structure from the source is never recreated inside the type folders.

### React UI (`src/`)

- `App.tsx` — root component: owns all state, wires up IPC listeners in `useEffect`
- `components/SettingsModal.tsx` — modal overlay for theme + organize mode
- `components/ActivityLog.tsx` — scrollable log panel with live indicator
- `src/types.ts` — shared TypeScript types + `window.api` global declaration

State machine in `App.tsx`: `idle → transferring → done | cancelled | error → idle` (auto-reset after 3.5s).

### Build System

- `electron-vite` — Vite for renderer (React/TS/Tailwind), esbuild for main+preload
- `electron-builder` — cross-platform packaging (NSIS/portable on Windows, AppImage+deb on Linux, dmg+zip on macOS)
- `electron.vite.config.ts` — entry points: main (`electron/main/index.ts`), preload (`electron/preload/index.ts`), renderer (`index.html` at root)
- `electron-builder.config.ts` — output to `release/`, icons from `img/`

### Config Persistence

Stored as JSON in `app.getPath('userData')/config.json`. Schema: `{ defaultDest, theme, organizeMode }`.

### GitHub Actions

`.github/workflows/build.yml` runs on `v*` tags and `workflow_dispatch`. Matrix strategy across `windows-latest`, `ubuntu-latest`, `macos-latest`. Each runner installs dependencies, builds, and uploads platform artifacts. A final `release` job creates a GitHub Release with all artifacts when triggered by a tag.
