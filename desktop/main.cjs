'use strict';

const { spawn } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const {
  app,
  BrowserWindow,
  ipcMain,
  session,
  shell,
} = require('electron');
const {
  ReadyLineParser,
  createPublicRuntime,
  isAllowedWindowNavigation,
  isProbeReady,
  isSafeExternalUrl,
  isTrustedNavigation,
  isVisitorChatUrl,
  resolveBackendSpec,
  resolveDataRoot,
} = require('./lib.cjs');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const ERROR_PAGE = path.join(__dirname, 'error.html');
const ERROR_PAGE_URL = pathToFileURL(ERROR_PAGE).href;
const VISITOR_PARTITION = 'persist:lingguide-visitor';
const ADMIN_PARTITION = 'persist:lingguide-admin';
const STARTUP_TIMEOUT_MS = readTimeout('LINGGUIDE_STARTUP_TIMEOUT_MS', 90_000);
const PROBE_TIMEOUT_MS = readTimeout('LINGGUIDE_PROBE_TIMEOUT_MS', 2_500);
const STOP_TIMEOUT_MS = readTimeout('LINGGUIDE_STOP_TIMEOUT_MS', 5_000);

let visitorWindow = null;
let adminWindow = null;
let backendState = null;
let backendRuntime = null;
let adminToken = null;
let dataRoot = null;
let logDirectory = null;
let logPath = null;
let logStream = null;
let restartPromise = null;
let isQuitting = false;
let quitCompleted = false;

function readTimeout(name, fallback) {
  const value = Number(process.env[name]);
  return Number.isInteger(value) && value >= 100 ? value : fallback;
}

function hasExited(child) {
  return child.exitCode !== null || child.signalCode !== null;
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function formatError(error) {
  return error instanceof Error ? error.message : String(error);
}

function writeLog(level, message) {
  const line = `[${new Date().toISOString()}] [${level}] ${String(message).replace(/[\r\n]+/g, ' ')}\n`;
  if (logStream && !logStream.destroyed) logStream.write(line);
}

function writeBackendLog(source, chunk, token) {
  let text = Buffer.isBuffer(chunk) ? chunk.toString('utf8') : String(chunk);
  if (token) text = text.split(token).join('[已隐藏管理令牌]');
  if (logStream && !logStream.destroyed) {
    logStream.write(`[${new Date().toISOString()}] [backend:${source}] ${text}`);
    if (!text.endsWith('\n')) logStream.write('\n');
  }
}

function initializeStorage() {
  dataRoot = resolveDataRoot({
    override: process.env.LINGGUIDE_DATA_ROOT,
    isPackaged: app.isPackaged,
    executablePath: process.execPath,
    projectRoot: PROJECT_ROOT,
  });
  logDirectory = path.join(dataRoot, 'logs');
  fs.mkdirSync(logDirectory, { recursive: true });
  logPath = path.join(logDirectory, 'desktop.log');
  logStream = fs.createWriteStream(logPath, { flags: 'a', encoding: 'utf8' });
  logStream.on('error', (error) => console.error('桌面日志写入失败：', error));
  writeLog('INFO', `桌面端启动，版本 ${app.getVersion()}，数据目录 ${dataRoot}`);
}

function backendResourcesRoot() {
  return app.isPackaged ? process.resourcesPath : PROJECT_ROOT;
}

function pythonExecutable() {
  return process.env.LINGGUIDE_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
}

function waitForExit(child, timeoutMs) {
  if (hasExited(child)) return Promise.resolve(true);
  return new Promise((resolve) => {
    let settled = false;
    const finish = (exited) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      child.off('exit', onExit);
      child.off('close', onExit);
      resolve(exited);
    };
    const onExit = () => finish(true);
    const timer = setTimeout(() => finish(false), timeoutMs);
    child.once('exit', onExit);
    child.once('close', onExit);
  });
}

function taskkillOwnedTree(pid) {
  return new Promise((resolve) => {
    const killer = spawn('taskkill.exe', ['/PID', String(pid), '/T', '/F'], {
      windowsHide: true,
      stdio: 'ignore',
    });
    killer.once('error', (error) => {
      writeLog('ERROR', `按 PID ${pid} 回收进程树失败：${formatError(error)}`);
      resolve();
    });
    killer.once('exit', () => resolve());
  });
}

async function stopBackend() {
  const state = backendState;
  if (!state) return;
  state.stopping = true;
  const { child } = state;
  writeLog('INFO', `正在回收自有后端 PID ${child.pid ?? '未知'}`);

  if (!hasExited(child)) {
    try {
      if (child.stdin && !child.stdin.destroyed) child.stdin.write('LINGGUIDE_SHUTDOWN\n');
      if (process.platform !== 'win32') child.kill('SIGTERM');
    } catch (error) {
      writeLog('WARN', `发送优雅停止信号失败：${formatError(error)}`);
    }
  }

  const exitedGracefully = await waitForExit(child, STOP_TIMEOUT_MS);
  if (!exitedGracefully && !hasExited(child)) {
    writeLog('WARN', `后端停止超时，强制回收自有 PID ${child.pid}`);
    if (process.platform === 'win32' && child.pid) {
      await taskkillOwnedTree(child.pid);
    } else {
      try {
        if (child.pid) process.kill(-child.pid, 'SIGKILL');
      } catch (error) {
        writeLog('ERROR', `强制回收后端失败：${formatError(error)}`);
      }
    }
    await waitForExit(child, 2_000);
  }

  if (backendState === state) backendState = null;
  backendRuntime = null;
  adminToken = null;
}

function waitForReadyMarker(state, deadline) {
  if (state.pendingReady) return Promise.resolve(state.pendingReady);
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (error, ready) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      state.readyResolve = null;
      state.readyReject = null;
      if (error) reject(error);
      else resolve(ready);
    };
    state.readyResolve = (ready) => finish(null, ready);
    state.readyReject = (error) => finish(error);
    const remaining = Math.max(1, deadline - Date.now());
    const timer = setTimeout(
      () => finish(new Error(`等待 ${'LINGGUIDE_READY'} 超时`)),
      remaining,
    );
  });
}

function probeJson(port, pathname, timeoutMs) {
  return new Promise((resolve, reject) => {
    const request = http.get({
      hostname: '127.0.0.1',
      port,
      path: pathname,
      timeout: timeoutMs,
      headers: { Accept: 'application/json' },
    }, (response) => {
      let body = '';
      response.setEncoding('utf8');
      response.on('data', (chunk) => {
        body += chunk;
        if (body.length > 1024 * 1024) request.destroy(new Error('健康检查响应过大'));
      });
      response.on('end', () => {
        try {
          resolve({
            ok: response.statusCode >= 200 && response.statusCode < 300,
            statusCode: response.statusCode,
            payload: JSON.parse(body),
          });
        } catch {
          reject(new Error(`${pathname} 未返回有效 JSON`));
        }
      });
    });
    request.once('timeout', () => request.destroy(new Error(`${pathname} 请求超时`)));
    request.once('error', reject);
  });
}

function describeProbe(result) {
  if (result.status === 'rejected') return formatError(result.reason);
  const status = result.value.payload?.status ?? result.value.payload?.detail?.status ?? '未知';
  return `HTTP ${result.value.statusCode}，status=${status}`;
}

async function waitForHealthAndReadiness(state, port, deadline) {
  let healthDescription = '尚未检查';
  let readinessDescription = '尚未检查';

  while (Date.now() < deadline) {
    if (backendState !== state || hasExited(state.child)) throw new Error('后端在就绪检查期间退出');
    const remaining = Math.max(100, deadline - Date.now());
    const timeout = Math.min(PROBE_TIMEOUT_MS, remaining);
    const [health, readiness] = await Promise.allSettled([
      probeJson(port, '/api/health', timeout),
      probeJson(port, '/api/readiness', timeout),
    ]);
    healthDescription = describeProbe(health);
    readinessDescription = describeProbe(readiness);
    const healthReady = health.status === 'fulfilled'
      && isProbeReady('health', health.value.ok, health.value.payload);
    const readinessReady = readiness.status === 'fulfilled'
      && isProbeReady('readiness', readiness.value.ok, readiness.value.payload);
    if (healthReady && readinessReady) return;
    await delay(Math.min(500, Math.max(1, deadline - Date.now())));
  }

  throw new Error(`后端未通过检查（health：${healthDescription}；readiness：${readinessDescription}）`);
}

async function startBackend() {
  if (backendState) throw new Error('后端已在运行');
  const token = crypto.randomBytes(32).toString('base64url');
  const spec = resolveBackendSpec({
    isPackaged: app.isPackaged,
    resourcesPath: process.resourcesPath,
    projectRoot: PROJECT_ROOT,
    pythonExecutable: pythonExecutable(),
  });
  if (!fs.existsSync(spec.entryPath)) throw new Error(`找不到后端入口：${spec.entryPath}`);

  const child = spawn(spec.command, spec.args, {
    cwd: spec.cwd,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      LINGGUIDE_DESKTOP: '1',
      LINGGUIDE_DATA_ROOT: dataRoot,
      LINGGUIDE_RESOURCE_ROOT: backendResourcesRoot(),
      LINGGUIDE_ADMIN_TOKEN: token,
    },
    detached: process.platform !== 'win32',
    windowsHide: true,
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  const state = {
    child,
    parser: new ReadyLineParser(),
    ready: false,
    stopping: false,
    pendingReady: null,
    readyResolve: null,
    readyReject: null,
  };
  backendState = state;
  adminToken = token;
  writeLog('INFO', `已启动自有后端 PID ${child.pid ?? '未知'}`);

  child.stdout.on('data', (chunk) => {
    writeBackendLog('stdout', chunk, token);
    for (const ready of state.parser.push(chunk)) {
      state.pendingReady = ready;
      if (state.readyResolve) state.readyResolve(ready);
    }
  });
  child.stderr.on('data', (chunk) => writeBackendLog('stderr', chunk, token));
  child.once('error', (error) => {
    writeLog('ERROR', `后端进程错误：${formatError(error)}`);
    if (state.readyReject) state.readyReject(new Error(`无法启动后端：${formatError(error)}`));
  });
  child.once('exit', (code, signal) => {
    const trailing = state.parser.flush();
    if (trailing[0]) {
      state.pendingReady = trailing[0];
      if (state.readyResolve) state.readyResolve(trailing[0]);
    }
    const description = `后端退出，code=${code ?? 'null'}，signal=${signal ?? 'null'}`;
    writeLog(state.stopping ? 'INFO' : 'ERROR', description);
    if (state.readyReject) state.readyReject(new Error(description));
    if (backendState === state) {
      backendState = null;
      backendRuntime = null;
      adminToken = null;
      if (state.ready && !state.stopping && !isQuitting) showBackendFailure(description);
    }
  });

  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  try {
    const { port } = await waitForReadyMarker(state, deadline);
    writeLog('INFO', `收到后端就绪协议，动态端口 ${port}`);
    await waitForHealthAndReadiness(state, port, deadline);
    if (backendState !== state || hasExited(child)) throw new Error('后端通过检查前已退出');
    state.ready = true;
    backendRuntime = createPublicRuntime({
      port,
      isPackaged: app.isPackaged,
      version: app.getVersion(),
    });
    writeLog('INFO', '后端 health/readiness 检查通过');
    return backendRuntime;
  } catch (error) {
    writeLog('ERROR', `后端启动失败：${formatError(error)}`);
    await stopBackend();
    throw error;
  }
}

function isErrorPage(url) {
  return url === ERROR_PAGE_URL || url.startsWith(`${ERROR_PAGE_URL}?`);
}

function secureWindow(window, role) {
  const contents = window.webContents;
  const roleLabel = role === 'admin' ? '管理端' : '游客端';
  const navigationAllowed = (url) => {
    if (isErrorPage(url)) return true;
    return Boolean(backendRuntime
      && isAllowedWindowNavigation(url, backendRuntime.backendOrigin, role));
  };
  const guardNavigation = (event, url) => {
    if (navigationAllowed(url)) return;
    event.preventDefault();
    if (isSafeExternalUrl(url)) shell.openExternal(url).catch((error) => {
      writeLog('ERROR', `打开外链失败：${formatError(error)}`);
    });
  };

  contents.on('will-navigate', guardNavigation);
  contents.on('will-redirect', guardNavigation);
  contents.setWindowOpenHandler(({ url }) => {
    if (isSafeExternalUrl(url)) shell.openExternal(url).catch((error) => {
      writeLog('ERROR', `打开外链失败：${formatError(error)}`);
    });
    return { action: 'deny' };
  });
  contents.on('will-attach-webview', (event) => event.preventDefault());
  contents.on('render-process-gone', (_event, details) => {
    writeLog('ERROR', `${roleLabel}渲染进程崩溃：${details.reason}`);
    if (!isQuitting) loadErrorPage(window, `${roleLabel}窗口渲染进程异常退出`);
  });
  contents.on('did-fail-load', (_event, code, description, validatedUrl, isMainFrame) => {
    if (!isMainFrame || code === -3 || isErrorPage(validatedUrl)) return;
    writeLog('ERROR', `${roleLabel}页面加载失败：${code} ${description}`);
    loadErrorPage(window, `${roleLabel}页面加载失败（${code}）`);
  });
}

function baseWindowOptions(preload, partition, size) {
  return {
    width: size.width,
    height: size.height,
    minWidth: size.minWidth,
    minHeight: size.minHeight,
    show: false,
    autoHideMenuBar: true,
    backgroundColor: '#f5f7fa',
    webPreferences: {
      preload,
      partition,
      nodeIntegration: false,
      nodeIntegrationInWorker: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      devTools: !app.isPackaged,
      webviewTag: false,
    },
  };
}

function createVisitorWindow() {
  if (visitorWindow && !visitorWindow.isDestroyed()) return visitorWindow;
  const window = new BrowserWindow(baseWindowOptions(
    path.join(__dirname, 'visitor-preload.cjs'),
    VISITOR_PARTITION,
    { width: 1280, height: 800, minWidth: 960, minHeight: 640 },
  ));
  visitorWindow = window;
  secureWindow(window, 'visitor');
  window.once('ready-to-show', () => window.show());
  window.on('closed', () => {
    if (visitorWindow === window) visitorWindow = null;
  });
  return window;
}

function createAdminWindow() {
  if (adminWindow && !adminWindow.isDestroyed()) return adminWindow;
  const window = new BrowserWindow(baseWindowOptions(
    path.join(__dirname, 'admin-preload.cjs'),
    ADMIN_PARTITION,
    { width: 1440, height: 900, minWidth: 1024, minHeight: 700 },
  ));
  adminWindow = window;
  secureWindow(window, 'admin');
  window.once('ready-to-show', () => window.show());
  window.on('closed', () => {
    if (adminWindow === window) adminWindow = null;
  });
  return window;
}

async function loadErrorPage(window, message) {
  if (!window || window.isDestroyed()) return;
  try {
    await window.loadFile(ERROR_PAGE, {
      query: { message: String(message), logPath: logPath || '' },
    });
    window.show();
  } catch (error) {
    writeLog('ERROR', `错误页加载失败：${formatError(error)}`);
  }
}

function showBackendFailure(message) {
  writeLog('ERROR', message);
  if (!visitorWindow && !adminWindow) {
    loadErrorPage(createVisitorWindow(), message);
    return;
  }
  loadErrorPage(visitorWindow, message);
  loadErrorPage(adminWindow, message);
}

function configurePermissions() {
  const visitorSession = session.fromPartition(VISITOR_PARTITION);
  const adminSession = session.fromPartition(ADMIN_PARTITION);
  const isTrustedVisitorChat = (webContents, permission, details = {}) => {
    if (permission !== 'media' || !visitorWindow || visitorWindow.isDestroyed()) return false;
    if (!webContents || webContents !== visitorWindow.webContents || !backendRuntime) return false;
    if (!isVisitorChatUrl(webContents.getURL(), backendRuntime.backendOrigin)) return false;
    const requestingUrl = details.requestingUrl || details.requestingOrigin || webContents.getURL();
    return isTrustedNavigation(requestingUrl, backendRuntime.backendOrigin);
  };

  visitorSession.setPermissionRequestHandler((webContents, permission, callback, details) => {
    const mediaTypes = details.mediaTypes || [];
    callback(isTrustedVisitorChat(webContents, permission, details)
      && mediaTypes.length > 0
      && mediaTypes.every((type) => type === 'audio' || type === 'audioCapture'));
  });
  visitorSession.setPermissionCheckHandler((webContents, permission, _origin, details) => {
    const mediaType = details.mediaType;
    return isTrustedVisitorChat(webContents, permission, details)
      && (!mediaType || mediaType === 'audio' || mediaType === 'audioCapture');
  });
  adminSession.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
  adminSession.setPermissionCheckHandler(() => false);
}

function assertSender(event, window, role) {
  if (!window || window.isDestroyed() || event.sender !== window.webContents) {
    throw new Error(`拒绝非${role}窗口调用`);
  }
  const senderUrl = event.senderFrame?.url || event.sender.getURL();
  if (!isErrorPage(senderUrl)
    && (!backendRuntime || !isTrustedNavigation(senderUrl, backendRuntime.backendOrigin))) {
    throw new Error(`拒绝不可信${role}页面调用`);
  }
}

function installIpcHandlers() {
  ipcMain.handle('desktop:open-admin', async (event) => {
    assertSender(event, visitorWindow, '游客端');
    if (!backendRuntime) throw new Error('后端尚未就绪');
    const window = createAdminWindow();
    if (window.webContents.getURL() !== backendRuntime.adminUrl) {
      await window.loadURL(backendRuntime.adminUrl);
    }
    if (window.isMinimized()) window.restore();
    window.show();
    window.focus();
  });

  ipcMain.handle('desktop:get-admin-token', async (event) => {
    assertSender(event, adminWindow, '管理端');
    return adminToken || null;
  });

  ipcMain.handle('desktop:open-logs', async (event) => {
    assertSender(event, adminWindow, '管理端');
    const error = await shell.openPath(logDirectory);
    if (error) throw new Error(error);
  });

  ipcMain.handle('desktop:restart-backend', async (event) => {
    assertSender(event, adminWindow, '管理端');
    if (!restartPromise) {
      restartPromise = (async () => {
        writeLog('INFO', '管理端请求重启后端');
        await loadErrorPage(visitorWindow, '后端正在重启，请稍候…');
        await stopBackend();
        return startBackend();
      })().finally(() => {
        restartPromise = null;
      });
    }
    try {
      const runtime = await restartPromise;
      setTimeout(() => {
        if (visitorWindow && !visitorWindow.isDestroyed()) visitorWindow.loadURL(runtime.visitorUrl);
        if (adminWindow && !adminWindow.isDestroyed()) adminWindow.loadURL(runtime.adminUrl);
      }, 0);
    } catch (error) {
      setTimeout(() => showBackendFailure(`后端重启失败：${formatError(error)}`), 0);
      throw error;
    }
  });
}

async function bootstrap() {
  initializeStorage();
  configurePermissions();
  installIpcHandlers();
  const runtime = await startBackend();
  const window = createVisitorWindow();
  await window.loadURL(runtime.visitorUrl);
}

const hasSingleInstanceLock = app.requestSingleInstanceLock();
if (!hasSingleInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    const window = visitorWindow || adminWindow;
    if (!window || window.isDestroyed()) return;
    if (window.isMinimized()) window.restore();
    window.show();
    window.focus();
  });

  app.whenReady().then(bootstrap).catch((error) => {
    showBackendFailure(`启动失败：${formatError(error)}`);
  });

  app.on('activate', () => {
    if (!visitorWindow && backendRuntime) {
      const window = createVisitorWindow();
      window.loadURL(backendRuntime.visitorUrl);
    }
  });

  app.on('window-all-closed', () => app.quit());

  app.on('before-quit', (event) => {
    if (quitCompleted) return;
    event.preventDefault();
    if (isQuitting) return;
    isQuitting = true;
    stopBackend().catch((error) => {
      writeLog('ERROR', `退出时回收后端失败：${formatError(error)}`);
    }).finally(() => {
      writeLog('INFO', '桌面端退出');
      quitCompleted = true;
      if (logStream && !logStream.destroyed) logStream.end();
      app.quit();
    });
  });
}
