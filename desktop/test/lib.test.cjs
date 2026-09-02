'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const {
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
} = require('../lib.cjs');

test('parseReadyLine 仅接受带有效动态端口的协议行', () => {
  assert.deepEqual(parseReadyLine('LINGGUIDE_READY {"port":49152}'), { port: 49152 });
  assert.deepEqual(parseReadyLine('日志前缀 LINGGUIDE_READY: {"port":8000,"extra":true}'), { port: 8000 });
  assert.equal(parseReadyLine('普通后端噪声'), null);
  assert.equal(parseReadyLine('LINGGUIDE_READY {"port":0}'), null);
  assert.equal(parseReadyLine('LINGGUIDE_READY not-json'), null);
});

test('ReadyLineParser 处理分块、CRLF、噪声和超长缓存', () => {
  const parser = new ReadyLineParser(128);
  assert.deepEqual(parser.push('启动中\r\nLINGGUIDE_RE'), []);
  assert.deepEqual(parser.push('ADY {"port":43210}\r\n后续噪声\n'), [{ port: 43210 }]);
  assert.deepEqual(parser.push('x'.repeat(300)), []);
  assert.equal(parser.buffer.length, 128);
  assert.deepEqual(parser.flush(), []);
});

test('数据目录优先使用覆盖值，打包态默认在 exe 同级', () => {
  const override = resolveDataRoot({
    override: './tmp-data',
    isPackaged: false,
    projectRoot: 'C:\\project',
    cwd: 'C:\\workspace',
  });
  assert.equal(override, path.resolve('C:\\workspace', './tmp-data'));

  const packaged = resolveDataRoot({
    isPackaged: true,
    executablePath: 'C:\\Apps\\LingGuide\\灵境导游.exe',
  });
  assert.equal(packaged, path.join(path.dirname(path.resolve('C:\\Apps\\LingGuide\\灵境导游.exe')), 'LingGuideData'));
});

test('后端启动描述区分开发态 Python 和打包态 exe', () => {
  const development = resolveBackendSpec({
    isPackaged: false,
    projectRoot: 'C:\\project',
    pythonExecutable: 'python',
  });
  assert.equal(development.command, 'python');
  assert.deepEqual(development.args, [path.join(path.resolve('C:\\project'), 'backend', 'launcher.py')]);

  const packaged = resolveBackendSpec({
    isPackaged: true,
    resourcesPath: 'C:\\resources',
  });
  assert.equal(packaged.command, path.join(path.resolve('C:\\resources'), 'backend', 'lingguide-backend.exe'));
  assert.deepEqual(packaged.args, []);
});

test('公开运行信息不包含管理令牌', () => {
  const runtime = createPublicRuntime({ port: 54321, isPackaged: true, version: '1.0.0' });
  assert.equal(runtime.backendOrigin, 'http://127.0.0.1:54321');
  assert.equal(runtime.adminUrl, 'http://127.0.0.1:54321/admin/');
  assert.equal('adminToken' in runtime, false);
  assert.equal(JSON.stringify(runtime).includes('token'), false);
});

test('导航、外链和麦克风页面判定限制来源', () => {
  const origin = 'http://127.0.0.1:54321';
  assert.equal(isTrustedNavigation(`${origin}/chat`, origin), true);
  assert.equal(isTrustedNavigation('http://localhost:54321/chat', origin), false);
  assert.equal(isTrustedNavigation('https://example.com', origin), false);
  assert.equal(isAllowedWindowNavigation(`${origin}/chat`, origin, 'visitor'), true);
  assert.equal(isAllowedWindowNavigation(`${origin}/admin/`, origin, 'visitor'), false);
  assert.equal(isAllowedWindowNavigation(`${origin}/admin/dashboard`, origin, 'admin'), true);
  assert.equal(isAllowedWindowNavigation(`${origin}/chat`, origin, 'admin'), false);
  assert.equal(isSafeExternalUrl('https://example.com/help'), true);
  assert.equal(isSafeExternalUrl('http://example.com/help'), false);
  assert.equal(isVisitorChatUrl(`${origin}/chat/`, origin), true);
  assert.equal(isVisitorChatUrl(`${origin}/`, origin), false);
});

test('health 与 readiness 必须同时匹配各自状态', () => {
  assert.equal(isProbeReady('health', true, { status: 'healthy' }), true);
  assert.equal(isProbeReady('health', false, { status: 'healthy' }), false);
  assert.equal(isProbeReady('readiness', true, { status: 'ready' }), true);
  assert.equal(isProbeReady('readiness', true, { status: 'not_ready' }), false);
});
