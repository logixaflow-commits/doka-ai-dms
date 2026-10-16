const { app, BrowserWindow, ipcMain, dialog, Notification, shell, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const http = require('http');
const fs = require('fs');
const { spawn } = require('child_process');

let mainWindow = null;
let backendProcess = null;
let tray = null;

const BACKEND_PORT = 8002;
const FRONTEND_PORT = 5173;
const FRONTEND_DEV_URL = `http://127.0.0.1:${FRONTEND_PORT}`;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

// Detect production mode: look for the built static index.html next to this file
const DIST_DIR = path.join(__dirname, '..', 'web-platform', 'frontend', 'dist');
const IS_PRODUCTION = fs.existsSync(path.join(DIST_DIR, 'index.html'));

function checkServiceRunning(url) {
  return new Promise((resolve) => {
    http.get(url, (res) => {
      resolve(res.statusCode < 500);
    }).on('error', () => {
      resolve(false);
    });
  });
}

/**
 * Wait up to maxWaitMs for a service URL to respond, polling every intervalMs.
 * Returns true if service came up within the time limit.
 */
async function waitForService(url, maxWaitMs = 15000, intervalMs = 500) {
  const deadline = Date.now() + maxWaitMs;
  while (Date.now() < deadline) {
    const up = await checkServiceRunning(url);
    if (up) return true;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
}

function startBackend() {
  const rootDir = path.resolve(__dirname, '../..');
  const backendDir = path.join(rootDir, 'apps', 'web-platform', 'backend');
  const pythonPath = path.join(backendDir, '.venv', 'Scripts', 'python.exe');

  console.log('[Desktop] Starting Doka Backend on port', BACKEND_PORT);
  backendProcess = spawn(pythonPath, [
    '-m', 'uvicorn', 'app.main:app',
    '--app-dir', backendDir,
    '--host', '127.0.0.1',
    '--port', String(BACKEND_PORT)
  ], {
    cwd: backendDir,
    stdio: 'ignore',
    detached: false
  });

  backendProcess.on('error', (err) => {
    console.error('[Desktop] Failed to start backend:', err);
  });
}

function createTray() {
  // Use a blank 16x16 tray icon; replace with a real .ico/.png asset if available
  const iconPath = path.join(__dirname, 'icon.png');
  const icon = fs.existsSync(iconPath)
    ? nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })
    : nativeImage.createEmpty();

  tray = new Tray(icon);
  tray.setToolTip('DOKA AI DMS');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open DOKA',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        } else {
          createWindow();
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 850,
    minWidth: 1024,
    minHeight: 700,
    title: 'DOKA AI DMS — Personal Local Desktop',
    backgroundColor: '#0f172a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true  // Security fix: sandbox enabled; contextBridge API remains available via preload
    }
  });

  if (IS_PRODUCTION) {
    // Production: serve built static files directly (no dev server required)
    console.log('[Desktop] Production mode: loading from', DIST_DIR);
    mainWindow.loadFile(path.join(DIST_DIR, 'index.html')).catch((err) => {
      console.error('[Desktop] Failed to load production build:', err);
    });
  } else {
    mainWindow.loadURL(FRONTEND_DEV_URL).catch(() => {
      // If frontend dev server isn't running yet, show a friendly retry page
      mainWindow.loadURL(`data:text/html;charset=utf-8,
        <html style="background:#0f172a;color:#f8fafc;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;">
          <div style="text-align:center;">
            <h2 style="color:#38bdf8;">DOKA AI DMS Desktop</h2>
            <p>Connecting to Doka services at ${FRONTEND_DEV_URL}...</p>
            <p style="font-size:12px;color:#94a3b8;">Please ensure Frontend &amp; Backend are started or run: start-doka.bat</p>
            <button onclick="location.reload()" style="background:#0284c7;color:white;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;margin-top:16px;">
              Retry Connection
            </button>
          </div>
        </html>
      `);
    });
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handlers
ipcMain.handle('dialog:openDirectory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });
  return result.filePaths[0] || null;
});

ipcMain.handle('dialog:openFiles', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile', 'multiSelections'],
    filters: [
      { name: 'Documents & Images', extensions: ['pdf', 'png', 'jpg', 'jpeg', 'tif', 'tiff'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });
  return result.filePaths;
});

ipcMain.handle('notification:show', (event, { title, body }) => {
  if (Notification.isSupported()) {
    new Notification({ title: title || 'DOKA DMS', body }).show();
  }
});

ipcMain.handle('shell:openExternal', (event, url) => {
  shell.openExternal(url);
});

app.whenReady().then(async () => {
  const isBackendUp = await checkServiceRunning(`${BACKEND_URL}/health`);
  if (!isBackendUp) {
    try {
      startBackend();
      // Wait up to 15 seconds for backend to fully start before opening the window
      console.log('[Desktop] Waiting for backend to become ready...');
      const ready = await waitForService(`${BACKEND_URL}/health`, 15000, 500);
      if (ready) {
        console.log('[Desktop] Backend is ready.');
      } else {
        console.warn('[Desktop] Backend did not respond within 15s; opening window anyway.');
      }
    } catch (e) {
      console.warn('[Desktop] Could not auto-launch backend:', e);
    }
  }

  createTray();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
