import { app, BrowserWindow, ipcMain, dialog, shell, Menu } from 'electron'
import { join } from 'node:path'
import { promises as fs, createReadStream, createWriteStream } from 'node:fs'
import { pipeline } from 'node:stream/promises'
import path from 'node:path'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Config {
  defaultDest: string
  theme: 'light' | 'dark' | 'system'
  organizeMode: 'classic' | 'date_then_type' | 'type_then_date'
}

interface TransferOptions {
  src: string
  dest: string
  move: boolean
  mode: 'classic' | 'date_then_type' | 'type_then_date'
}

interface ProgressData {
  transferred: number
  total: number
  currentFile: string
  type: string
  bytesTransferred: number
  totalBytes: number
}

interface FileInfo {
  path: string
  type: 'JPEG' | 'RAW' | 'VIDEO'
  date: string
}

// ─── File Type Detection ──────────────────────────────────────────────────────

const JPEG_EXTS = new Set([
  '.jpg', '.jpeg', '.jpe', '.jfif', '.png', '.gif',
  '.bmp', '.tiff', '.tif', '.webp', '.ico', '.svg', '.heic', '.heif'
])
const RAW_EXTS = new Set([
  '.cr2', '.cr3', '.nef', '.raf', '.arw', '.rw2',
  '.dng', '.orf', '.sr2', '.pef', '.nrw'
])
const VIDEO_EXTS = new Set([
  '.mp4', '.mov', '.avi', '.mts', '.mxf',
  '.mpg', '.mpeg', '.mkv', '.wmv', '.3gp'
])

function getFileType(filePath: string): 'JPEG' | 'RAW' | 'VIDEO' | null {
  const ext = path.extname(filePath).toLowerCase()
  if (JPEG_EXTS.has(ext)) return 'JPEG'
  if (RAW_EXTS.has(ext)) return 'RAW'
  if (VIDEO_EXTS.has(ext)) return 'VIDEO'
  return null
}

// ─── Date Extraction ──────────────────────────────────────────────────────────

function formatDate(date: Date): string {
  const dd = String(date.getDate()).padStart(2, '0')
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const yyyy = date.getFullYear()
  return `${dd}-${mm}-${yyyy}`
}

async function getCaptureDate(filePath: string): Promise<string> {
  try {
    const { default: exifr } = await import('exifr')
    const exif = await exifr.parse(filePath, {
      DateTimeOriginal: true,
      DateTime: true,
      DateTimeDigitized: true
    })
    const date = exif?.DateTimeOriginal ?? exif?.DateTime ?? exif?.DateTimeDigitized
    if (date instanceof Date && !isNaN(date.getTime())) {
      return formatDate(date)
    }
  } catch { /* fall through */ }

  try {
    const stat = await fs.stat(filePath)
    return formatDate(stat.mtime)
  } catch { /* fall through */ }

  return formatDate(new Date())
}

// ─── Folder Utilities ─────────────────────────────────────────────────────────

async function nextSequenceFolder(base: string): Promise<string> {
  const now = new Date()
  const yyyy = now.getFullYear()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  const prefix = `${yyyy}-${mm}-${dd}`

  for (let n = 1; n <= 999; n++) {
    const name = `${prefix}_${String(n).padStart(2, '0')}`
    const fullPath = path.join(base, name)
    try {
      await fs.access(fullPath)
    } catch {
      return fullPath
    }
  }
  throw new Error('Too many session folders for today')
}

async function uniqueDestPath(dir: string, filename: string): Promise<string> {
  const ext = path.extname(filename)
  const base = path.basename(filename, ext)
  let destPath = path.join(dir, filename)
  let counter = 1

  while (true) {
    try {
      await fs.access(destPath)
      destPath = path.join(dir, `${base}_${counter}${ext}`)
      counter++
    } catch {
      return destPath
    }
  }
}

// ─── File Copy / Move ─────────────────────────────────────────────────────────

async function copyFileWithProgress(
  src: string,
  dest: string,
  onBytes?: (transferred: number, total: number) => void
): Promise<void> {
  const stat = await fs.stat(src)
  const total = stat.size

  if (total === 0) {
    await fs.copyFile(src, dest)
    return
  }

  let transferred = 0
  const read = createReadStream(src)
  const write = createWriteStream(dest)

  read.on('data', (chunk: Buffer) => {
    transferred += chunk.length
    onBytes?.(transferred, total)
  })

  await pipeline(read, write)
  await fs.utimes(dest, stat.atime, stat.mtime)
}

async function moveFileWithProgress(
  src: string,
  dest: string,
  onBytes?: (transferred: number, total: number) => void
): Promise<void> {
  try {
    await fs.rename(src, dest)
  } catch {
    await copyFileWithProgress(src, dest, onBytes)
    await fs.unlink(src)
  }
}

// ─── Directory Walker ─────────────────────────────────────────────────────────

async function walkFiles(
  dir: string,
  isCancelled: () => boolean,
  onLog: (msg: string) => void
): Promise<FileInfo[]> {
  const results: FileInfo[] = []

  async function walk(currentDir: string) {
    if (isCancelled()) return
    let entries: Awaited<ReturnType<typeof fs.readdir>>
    try {
      entries = await fs.readdir(currentDir, { withFileTypes: true })
    } catch {
      onLog(`Cannot read: ${currentDir}`)
      return
    }

    for (const entry of entries) {
      if (isCancelled()) return
      const fullPath = path.join(currentDir, entry.name)
      if (entry.isDirectory()) {
        await walk(fullPath)
      } else if (entry.isFile()) {
        const type = getFileType(fullPath)
        if (type) {
          const date = await getCaptureDate(fullPath)
          results.push({ path: fullPath, type, date })
        }
      }
    }
  }

  await walk(dir)
  return results
}

// ─── Transfer Engine ──────────────────────────────────────────────────────────

let cancelFlag = false

async function runTransfer(
  options: TransferOptions,
  win: BrowserWindow
): Promise<{ transferred: number; errors: number; cancelled: boolean }> {
  cancelFlag = false
  const { src, dest, move, mode } = options

  const sendLog = (msg: string) => win.webContents.send('transfer:log', msg)
  const sendProgress = (data: ProgressData) => win.webContents.send('transfer:progress', data)
  const isCancelled = () => cancelFlag

  sendLog('Scanning source folder...')

  let files: FileInfo[]
  try {
    files = await walkFiles(src, isCancelled, sendLog)
  } catch (e) {
    sendLog(`Scan error: ${e}`)
    return { transferred: 0, errors: 1, cancelled: false }
  }

  if (isCancelled()) return { transferred: 0, errors: 0, cancelled: true }

  const total = files.length
  sendLog(`Found ${total} media file${total !== 1 ? 's' : ''}`)

  if (total === 0) {
    sendLog('No media files found in source folder')
    return { transferred: 0, errors: 0, cancelled: false }
  }

  let sessionRoot: string
  if (mode === 'classic') {
    sessionRoot = await nextSequenceFolder(dest)
    await fs.mkdir(sessionRoot, { recursive: true })
    sendLog(`Session: ${path.basename(sessionRoot)}`)
  } else {
    sessionRoot = dest
  }

  // Pre-calculate total bytes
  let totalBytes = 0
  for (const file of files) {
    try {
      const stat = await fs.stat(file.path)
      totalBytes += stat.size
    } catch { /* skip */ }
  }

  let transferred = 0
  let errors = 0
  let bytesTransferred = 0

  for (const file of files) {
    if (isCancelled()) break

    let destDir: string
    if (mode === 'classic') {
      destDir = path.join(sessionRoot, file.type)
    } else if (mode === 'date_then_type') {
      destDir = path.join(sessionRoot, file.date, file.type)
    } else {
      destDir = path.join(sessionRoot, file.type, file.date)
    }

    await fs.mkdir(destDir, { recursive: true })

    const filename = path.basename(file.path)
    const destPath = await uniqueDestPath(destDir, filename)
    sendLog(`${move ? 'Moving' : 'Copying'} ${filename}`)

    try {
      let fileStat: Awaited<ReturnType<typeof fs.stat>>
      try {
        fileStat = await fs.stat(file.path)
      } catch {
        fileStat = { size: 0 } as Awaited<ReturnType<typeof fs.stat>>
      }

      const bytesAtStart = bytesTransferred

      const onBytes = (fb: number) => {
        bytesTransferred = bytesAtStart + fb
        sendProgress({ transferred, total, currentFile: filename, type: file.type, bytesTransferred, totalBytes })
      }

      if (move) {
        await moveFileWithProgress(file.path, destPath, onBytes)
      } else {
        await copyFileWithProgress(file.path, destPath, onBytes)
      }

      bytesTransferred = bytesAtStart + fileStat.size
      transferred++
      sendProgress({ transferred, total, currentFile: filename, type: file.type, bytesTransferred, totalBytes })
    } catch (e) {
      errors++
      sendLog(`Error: ${filename} — ${e}`)
    }
  }

  return { transferred, errors, cancelled: isCancelled() }
}

// ─── Config ───────────────────────────────────────────────────────────────────

const DEFAULT_CONFIG: Config = {
  defaultDest: '',
  theme: 'dark',
  organizeMode: 'classic'
}

function getConfigPath() {
  return path.join(app.getPath('userData'), 'config.json')
}

async function loadConfig(): Promise<Config> {
  try {
    const raw = await fs.readFile(getConfigPath(), 'utf-8')
    return { ...DEFAULT_CONFIG, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULT_CONFIG }
  }
}

async function saveConfig(config: Config): Promise<void> {
  await fs.mkdir(path.dirname(getConfigPath()), { recursive: true })
  await fs.writeFile(getConfigPath(), JSON.stringify(config, null, 2))
}

// ─── Window ───────────────────────────────────────────────────────────────────

function createWindow() {
  const iconPath = app.isPackaged
    ? join(process.resourcesPath, 'img/logo256.ico')
    : join(__dirname, '../../img/logo256.ico')

  const win = new BrowserWindow({
    width: 700,
    height: 580,
    minWidth: 560,
    minHeight: 480,
    title: 'Archivium',
    icon: iconPath,
    backgroundColor: '#0c0c0e',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false
    }
  })

  Menu.setApplicationMenu(null)

  if (process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    win.loadFile(join(__dirname, '../../dist/index.html'))
  }

  return win
}

// ─── IPC Handlers ─────────────────────────────────────────────────────────────

function registerHandlers(win: BrowserWindow) {
  ipcMain.handle('dialog:selectFolder', async () => {
    const result = await dialog.showOpenDialog(win, { properties: ['openDirectory'] })
    return result.canceled ? null : result.filePaths[0]
  })

  ipcMain.handle('config:load', () => loadConfig())

  ipcMain.handle('config:save', async (_, config: Config) => {
    await saveConfig(config)
  })

  ipcMain.handle('transfer:start', async (_, options: TransferOptions) => {
    const result = await runTransfer(options, win)
    win.webContents.send('transfer:complete', result)
    return result
  })

  ipcMain.on('transfer:cancel', () => {
    cancelFlag = true
  })

  ipcMain.handle('shell:openPath', async (_, p: string) => {
    await shell.openPath(p)
  })
}

// ─── Bootstrap ────────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  const win = createWindow()
  registerHandlers(win)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
