'use strict';

const path = require('node:path');

function source(name, fallback) {
  return path.resolve(process.env[name] || path.resolve(__dirname, fallback));
}

module.exports = {
  appId: 'cn.lingguide.desktop',
  productName: '灵境导游',
  executableName: 'LingGuide',
  asar: true,
  files: [
    'main.cjs',
    'lib.cjs',
    'visitor-preload.cjs',
    'admin-preload.cjs',
    'error.html',
  ],
  extraResources: [
    {
      from: source('LINGGUIDE_BACKEND_SOURCE', '../backend/dist/lingguide-backend'),
      to: 'backend',
    },
    {
      from: source('LINGGUIDE_VISITOR_SOURCE', '../frontend-visitor/dist'),
      to: 'web/visitor',
    },
    {
      from: source('LINGGUIDE_ADMIN_SOURCE', '../frontend-admin/dist'),
      to: 'web/admin',
    },
    {
      from: source('LINGGUIDE_SEED_SOURCE', '../release/.build-cache/seed'),
      to: 'seed',
    },
  ],
  directories: {
    output: 'dist',
  },
  win: {
    icon: path.join(source('LINGGUIDE_BRANDING_DIR', '../release/branding'), 'lingguide-icon.ico'),
    target: [{ target: 'dir', arch: ['x64'] }],
  },
};
