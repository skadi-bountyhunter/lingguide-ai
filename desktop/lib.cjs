'use strict';

const path = require('node:path');

const READY_MARKER = 'LINGGUIDE_READY';
const DEFAULT_MAX_READY_BUFFER = 64 * 1024;

/** 从后端输出行提取动态端口；非协议行返回 null。 */
function parseReadyLine(line) {
  const text = String(line ?? '');
  const markerIndex = text.indexOf(READY_MARKER);
  if (markerIndex < 0) return null;

  const rawPayload = text
    .slice(markerIndex + READY_MARKER.length)
    .trim()
    .replace(/^[:=]\s*/, '');

  try {
    const payload = JSON.parse(rawPayload);
    if (!Number.isInteger(payload.port) || payload.port < 1 || payload.port > 65535) {
      return null;
    }
    return { port: payload.port };
  } catch {
    return null;
  }
}

/** 处理 stdout 分块、噪声和超长未换行内容。 */
class ReadyLineParser {
  constructor(maxBuffer = DEFAULT_MAX_READY_BUFFER) {
    if (!Number.isInteger(maxBuffer) || maxBuffer < 128) {
      throw new TypeError('maxBuffer 必须是至少 128 的整数');
    }
    this.maxBuffer = maxBuffer;
    this.buffer = '';
  }

  push(chunk) {
    this.buffer += Buffer.isBuffer(chunk) ? chunk.toString('utf8') : String(chunk ?? '');
    const lines = this.buffer.split(/\n/);
    this.buffer = lines.pop() ?? '';
    if (this.buffer.length > this.maxBuffer) {
      this.buffer = this.buffer.slice(-this.maxBuffer);
    }
    return lines
      .map((line) => parseReadyLine(line.replace(/\r$/, '')))
      .filter(Boolean);
  }

  flush() {
    const result = parseReadyLine(this.buffer.replace(/\r$/, ''));
    this.buffer = '';
    return result ? [result] : [];
  }
}

/** 解析便携数据目录；测试可通过 override 完全隔离。 */
function resolveDataRoot({ override, isPackaged, executablePath, projectRoot, cwd = process.cwd() }) {
  const configured = String(override ?? '').trim();
  if (configured) return path.resolve(cwd, configured);
  if (isPackaged) {
    if (!executablePath) throw new TypeError('打包态必须提供 executablePath');
    return path.join(path.dirname(path.resolve(executablePath)), 'LingGuideData');
  }
  if (!projectRoot) throw new TypeError('开发态必须提供 projectRoot');
  return path.join(path.resolve(projectRoot), 'LingGuideData');
}

/** 返回开发态 Python 或打包态 exe 的启动描述。 */
function resolveBackendSpec({ isPackaged, resourcesPath, projectRoot, pythonExecutable }) {
  if (isPackaged) {
    const backendDir = path.join(path.resolve(resourcesPath), 'backend');
    const entryPath = path.join(backendDir, 'lingguide-backend.exe');
    return { command: entryPath, args: [], cwd: backendDir, entryPath };
  }

  const backendDir = path.join(path.resolve(projectRoot), 'backend');
  const entryPath = path.join(backendDir, 'launcher.py');
  return {
    command: pythonExecutable,
    args: [entryPath],
    cwd: backendDir,
    entryPath,
  };
}

/** 创建不含管理令牌的渲染进程运行信息。 */
function createPublicRuntime({ port, isPackaged, version }) {
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new TypeError('port 无效');
  }
  const backendOrigin = `http://127.0.0.1:${port}`;
  return {
    version: String(version),
    isPackaged: Boolean(isPackaged),
    port,
    backendOrigin,
    apiBaseUrl: `${backendOrigin}/api`,
    webSocketBaseUrl: `ws://127.0.0.1:${port}`,
    visitorUrl: `${backendOrigin}/`,
    adminUrl: `${backendOrigin}/admin/`,
  };
}

function isTrustedNavigation(candidate, backendOrigin) {
  try {
    const url = new URL(candidate);
    return ['http:', 'https:'].includes(url.protocol)
      && url.origin === new URL(backendOrigin).origin;
  } catch {
    return false;
  }
}

function isSafeExternalUrl(candidate) {
  try {
    return new URL(candidate).protocol === 'https:';
  } catch {
    return false;
  }
}

function isAllowedWindowNavigation(candidate, backendOrigin, role) {
  if (!isTrustedNavigation(candidate, backendOrigin)) return false;
  const pathname = new URL(candidate).pathname;
  const isAdminPath = pathname === '/admin' || pathname.startsWith('/admin/');
  if (role === 'admin') return isAdminPath;
  if (role === 'visitor') return !isAdminPath;
  return false;
}

function isVisitorChatUrl(candidate, backendOrigin) {
  if (!isTrustedNavigation(candidate, backendOrigin)) return false;
  const pathname = new URL(candidate).pathname.replace(/\/+$/, '') || '/';
  return pathname === '/chat';
}

function isProbeReady(kind, responseOk, payload) {
  if (!responseOk || !payload || typeof payload !== 'object') return false;
  if (kind === 'health') return payload.status === 'healthy';
  if (kind === 'readiness') return payload.status === 'ready';
  return false;
}

module.exports = {
  READY_MARKER,
  ReadyLineParser,
  createPublicRuntime,
  isAllowedWindowNavigation,
  isProbeReady,
  isSafeExternalUrl,
  isTrustedNavigation,
  isVisitorChatUrl,
  parseReadyLine,
  resolveBackendSpec,
  resolveDataRoot,
};
