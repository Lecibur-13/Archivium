"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
const electron = require("electron");
const path = require("node:path");
const node_fs = require("node:fs");
const promises = require("node:stream/promises");
const JPEG_EXTS = /* @__PURE__ */ new Set([
  ".jpg",
  ".jpeg",
  ".jpe",
  ".jfif",
  ".png",
  ".gif",
  ".bmp",
  ".tiff",
  ".tif",
  ".webp",
  ".ico",
  ".svg",
  ".heic",
  ".heif"
]);
const RAW_EXTS = /* @__PURE__ */ new Set([
  ".cr2",
  ".cr3",
  ".nef",
  ".raf",
  ".arw",
  ".rw2",
  ".dng",
  ".orf",
  ".sr2",
  ".pef",
  ".nrw"
]);
const VIDEO_EXTS = /* @__PURE__ */ new Set([
  ".mp4",
  ".mov",
  ".avi",
  ".mts",
  ".mxf",
  ".mpg",
  ".mpeg",
  ".mkv",
  ".wmv",
  ".3gp"
]);
function getFileType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (JPEG_EXTS.has(ext)) return "JPEG";
  if (RAW_EXTS.has(ext)) return "RAW";
  if (VIDEO_EXTS.has(ext)) return "VIDEO";
  return null;
}
function formatDate(date) {
  const dd = String(date.getDate()).padStart(2, "0");
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const yyyy = date.getFullYear();
  return `${dd}-${mm}-${yyyy}`;
}
async function getCaptureDate(filePath) {
  try {
    const { default: exifr } = await import("exifr");
    const exif = await exifr.parse(filePath, {
      DateTimeOriginal: true,
      DateTime: true,
      DateTimeDigitized: true
    });
    const date = exif?.DateTimeOriginal ?? exif?.DateTime ?? exif?.DateTimeDigitized;
    if (date instanceof Date && !isNaN(date.getTime())) {
      return formatDate(date);
    }
  } catch {
  }
  try {
    const stat = await node_fs.promises.stat(filePath);
    return formatDate(stat.mtime);
  } catch {
  }
  return formatDate(/* @__PURE__ */ new Date());
}
async function nextSequenceFolder(base) {
  const now = /* @__PURE__ */ new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  const prefix = `${yyyy}-${mm}-${dd}`;
  for (let n = 1; n <= 999; n++) {
    const name = `${prefix}_${String(n).padStart(2, "0")}`;
    const fullPath = path.join(base, name);
    try {
      await node_fs.promises.access(fullPath);
    } catch {
      return fullPath;
    }
  }
  throw new Error("Too many session folders for today");
}
async function uniqueDestPath(dir, filename) {
  const ext = path.extname(filename);
  const base = path.basename(filename, ext);
  let destPath = path.join(dir, filename);
  let counter = 1;
  while (true) {
    try {
      await node_fs.promises.access(destPath);
      destPath = path.join(dir, `${base}_${counter}${ext}`);
      counter++;
    } catch {
      return destPath;
    }
  }
}
async function copyFileWithProgress(src, dest, onBytes) {
  const stat = await node_fs.promises.stat(src);
  const total = stat.size;
  if (total === 0) {
    await node_fs.promises.copyFile(src, dest);
    return;
  }
  let transferred = 0;
  const read = node_fs.createReadStream(src);
  const write = node_fs.createWriteStream(dest);
  read.on("data", (chunk) => {
    transferred += chunk.length;
    onBytes?.(transferred, total);
  });
  await promises.pipeline(read, write);
  await node_fs.promises.utimes(dest, stat.atime, stat.mtime);
}
async function moveFileWithProgress(src, dest, onBytes) {
  try {
    await node_fs.promises.rename(src, dest);
  } catch {
    await copyFileWithProgress(src, dest, onBytes);
    await node_fs.promises.unlink(src);
  }
}
async function walkFiles(dir, isCancelled, onLog) {
  const results = [];
  async function walk(currentDir) {
    if (isCancelled()) return;
    let entries;
    try {
      entries = await node_fs.promises.readdir(currentDir, { withFileTypes: true });
    } catch {
      onLog(`Cannot read: ${currentDir}`);
      return;
    }
    for (const entry of entries) {
      if (isCancelled()) return;
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath);
      } else if (entry.isFile()) {
        const type = getFileType(fullPath);
        if (type) {
          const date = await getCaptureDate(fullPath);
          results.push({ path: fullPath, type, date });
        }
      }
    }
  }
  await walk(dir);
  return results;
}
let cancelFlag = false;
async function runTransfer(options, win) {
  cancelFlag = false;
  const { src, dest, move, mode } = options;
  const sendLog = (msg) => win.webContents.send("transfer:log", msg);
  const sendProgress = (data) => win.webContents.send("transfer:progress", data);
  const isCancelled = () => cancelFlag;
  sendLog("Scanning source folder...");
  let files;
  try {
    files = await walkFiles(src, isCancelled, sendLog);
  } catch (e) {
    sendLog(`Scan error: ${e}`);
    return { transferred: 0, errors: 1, cancelled: false };
  }
  if (isCancelled()) return { transferred: 0, errors: 0, cancelled: true };
  const total = files.length;
  sendLog(`Found ${total} media file${total !== 1 ? "s" : ""}`);
  if (total === 0) {
    sendLog("No media files found in source folder");
    return { transferred: 0, errors: 0, cancelled: false };
  }
  let sessionRoot;
  if (mode === "classic") {
    sessionRoot = await nextSequenceFolder(dest);
    await node_fs.promises.mkdir(sessionRoot, { recursive: true });
    sendLog(`Session: ${path.basename(sessionRoot)}`);
  } else {
    sessionRoot = dest;
  }
  let totalBytes = 0;
  for (const file of files) {
    try {
      const stat = await node_fs.promises.stat(file.path);
      totalBytes += stat.size;
    } catch {
    }
  }
  let transferred = 0;
  let errors = 0;
  let bytesTransferred = 0;
  for (const file of files) {
    if (isCancelled()) break;
    let destDir;
    if (mode === "classic") {
      destDir = path.join(sessionRoot, file.type);
    } else if (mode === "date_then_type") {
      destDir = path.join(sessionRoot, file.date, file.type);
    } else {
      destDir = path.join(sessionRoot, file.type, file.date);
    }
    await node_fs.promises.mkdir(destDir, { recursive: true });
    const filename = path.basename(file.path);
    const destPath = await uniqueDestPath(destDir, filename);
    sendLog(`${move ? "Moving" : "Copying"} ${filename}`);
    try {
      let fileStat;
      try {
        fileStat = await node_fs.promises.stat(file.path);
      } catch {
        fileStat = { size: 0 };
      }
      const bytesAtStart = bytesTransferred;
      const onBytes = (fb) => {
        bytesTransferred = bytesAtStart + fb;
        sendProgress({ transferred, total, currentFile: filename, type: file.type, bytesTransferred, totalBytes });
      };
      if (move) {
        await moveFileWithProgress(file.path, destPath, onBytes);
      } else {
        await copyFileWithProgress(file.path, destPath, onBytes);
      }
      bytesTransferred = bytesAtStart + fileStat.size;
      transferred++;
      sendProgress({ transferred, total, currentFile: filename, type: file.type, bytesTransferred, totalBytes });
    } catch (e) {
      errors++;
      sendLog(`Error: ${filename} — ${e}`);
    }
  }
  return { transferred, errors, cancelled: isCancelled() };
}
const DEFAULT_CONFIG = {
  defaultDest: "",
  theme: "dark",
  organizeMode: "classic"
};
function getConfigPath() {
  return path.join(electron.app.getPath("userData"), "config.json");
}
async function loadConfig() {
  try {
    const raw = await node_fs.promises.readFile(getConfigPath(), "utf-8");
    return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}
async function saveConfig(config) {
  await node_fs.promises.mkdir(path.dirname(getConfigPath()), { recursive: true });
  await node_fs.promises.writeFile(getConfigPath(), JSON.stringify(config, null, 2));
}
function createWindow() {
  const iconPath = path.join(__dirname, "../../img/logo.ico");
  const win = new electron.BrowserWindow({
    width: 700,
    height: 580,
    minWidth: 560,
    minHeight: 480,
    title: "Archivium",
    icon: iconPath,
    backgroundColor: "#0c0c0e",
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false
    }
  });
  electron.Menu.setApplicationMenu(null);
  if (process.env["ELECTRON_RENDERER_URL"]) {
    win.loadURL(process.env["ELECTRON_RENDERER_URL"]);
  } else {
    win.loadFile(path.join(__dirname, "../../dist/index.html"));
  }
  return win;
}
function registerHandlers(win) {
  electron.ipcMain.handle("dialog:selectFolder", async () => {
    const result = await electron.dialog.showOpenDialog(win, { properties: ["openDirectory"] });
    return result.canceled ? null : result.filePaths[0];
  });
  electron.ipcMain.handle("config:load", () => loadConfig());
  electron.ipcMain.handle("config:save", async (_, config) => {
    await saveConfig(config);
  });
  electron.ipcMain.handle("transfer:start", async (_, options) => {
    const result = await runTransfer(options, win);
    win.webContents.send("transfer:complete", result);
    return result;
  });
  electron.ipcMain.on("transfer:cancel", () => {
    cancelFlag = true;
  });
  electron.ipcMain.handle("shell:openPath", async (_, p) => {
    await electron.shell.openPath(p);
  });
}
electron.app.whenReady().then(() => {
  const win = createWindow();
  registerHandlers(win);
  electron.app.on("activate", () => {
    if (electron.BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});
electron.app.on("window-all-closed", () => {
  if (process.platform !== "darwin") electron.app.quit();
});
