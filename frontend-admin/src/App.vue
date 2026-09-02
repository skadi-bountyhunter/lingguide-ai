<template>
  <div class="admin-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sb-brand">
        <div class="sb-logo"><img :src="logoUrl" alt="logo" /></div>
        <div>
          <h1>灵境导游</h1>
          <p>管理后台</p>
        </div>
      </div>

      <nav class="sb-nav">
        <router-link v-for="item in navItems" :key="item.path" :to="item.path" class="sb-nav-item">
          <span class="nav-icon" v-html="item.icon" />
          <span class="nav-label">{{ item.label }}</span>
          <div v-if="$route.path === item.path" class="nav-dot" />
        </router-link>
      </nav>

      <div class="sb-footer">
        <div class="sb-user">
          <span>🧑‍💼</span>
          <div>
            <p>管理员</p>
            <span>超级管理员</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main -->
    <div class="main-wrap">
      <header class="topbar">
        <h2>{{ pageTitle }}</h2>
        <div class="topbar-right">
          <div class="search-box">
            <el-icon><Search /></el-icon>
            <input placeholder="搜索功能..." />
          </div>
          <button class="notify-btn">
            <el-icon><Bell /></el-icon>
            <span class="notify-dot" />
          </button>
          <div class="topbar-divider" />
          <div class="topbar-user">
            <span>🧑‍💼</span>
            <span>管理员</span>
          </div>
        </div>
      </header>

      <main class="content-area">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const logoUrl = `${import.meta.env.BASE_URL}logo.png`

const navItems = [
  { path: '/dashboard', label: '数据大屏', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>' },
  { path: '/knowledge', label: '知识库管理', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><line x1="8" y1="7" x2="16" y2="7"/><line x1="8" y1="11" x2="14" y2="11"/></svg>' },
  { path: '/rag-diagnostics', label: 'RAG 诊断', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/><path d="M8 11h6M11 8v6"/></svg>' },
  { path: '/spots', label: '景点管理', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>' },
  { path: '/routes', label: '路线管理', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/></svg>' },
  { path: '/avatar', label: '数字人管理', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>' },
  { path: '/report', label: '感受度报告', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>' },
  { path: '/users', label: '用户管理', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>' },
  { path: '/feedback', label: '反馈管理', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/><line x1="8" y1="9" x2="16" y2="9"/><line x1="8" y1="13" x2="13" y2="13"/></svg>' },
  { path: '/notifications', label: '通知管理', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></svg>' },
]

const titles: Record<string, string> = {
  '/dashboard': '数据大屏概览',
  '/knowledge': '知识库管理',
  '/rag-diagnostics': 'RAG 诊断',
  '/spots': '景点内容管理',
  '/routes': '预设路线管理',
  '/avatar': '数字人管理',
  '/report': '游客感受度报告',
  '/users': '用户管理',
  '/feedback': '游客反馈管理',
  '/notifications': '通知管理',
}

const pageTitle = computed(() => titles[route.path] || '管理后台')
</script>

<style scoped>
.admin-layout { display:flex; min-height:100vh; }

/* Sidebar */
.sidebar { width:240px; background:#fff; border-right:1px solid rgba(0,0,0,0.06); display:flex; flex-direction:column; position:fixed; top:0; bottom:0; left:0; z-index:20; flex-shrink:0; }
.sb-brand { display:flex; align-items:center; gap:12px; padding:16px 20px; border-bottom:1px solid rgba(0,0,0,0.04); }
.sb-logo { width:36px; height:36px; border-radius:12px; overflow:hidden; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 8px rgba(45,106,79,0.2); }
.sb-logo img { width:100%; height:100%; object-fit:contain; }
.sb-brand h1 { font-size:0.875rem; font-weight:700; color:var(--color-text-primary); line-height:1.2; }
.sb-brand p { font-size:10px; color:var(--color-text-muted); }

.sb-nav { flex:1; padding:16px 12px; display:flex; flex-direction:column; gap:4px; }
.sb-nav-item { display:flex; align-items:center; gap:12px; padding:10px 12px; border-radius:12px; font-size:0.875rem; font-weight:500; text-decoration:none; color:var(--color-text-secondary); transition:all 0.2s; position:relative; }
.sb-nav-item:hover { background:var(--color-bg-elevated); color:var(--color-text-primary); }
.sb-nav-item.router-link-active { background:var(--color-primary-bg); color:var(--color-primary); }
.nav-icon { display:flex; color:inherit; }
.router-link-active .nav-icon { color:var(--color-primary); }
.nav-dot { width:6px; height:6px; border-radius:50%; background:var(--color-primary); margin-left:auto; }

.sb-footer { padding:16px; border-top:1px solid rgba(0,0,0,0.04); }
.sb-user { display:flex; align-items:center; gap:12px; padding:0 8px; }
.sb-user span:first-child { width:32px; height:32px; border-radius:8px; background:var(--color-primary-bg); display:flex; align-items:center; justify-content:center; font-size:0.875rem; }
.sb-user p { font-size:0.75rem; font-weight:600; color:var(--color-text-primary); }
.sb-user span:last-child { font-size:10px; color:var(--color-text-muted); }

/* Main Area */
.main-wrap { margin-left:240px; flex:1; }
.topbar { height:64px; background:rgba(255,255,255,0.8); backdrop-filter:blur(12px); border-bottom:1px solid rgba(0,0,0,0.04); display:flex; align-items:center; justify-content:space-between; padding:0 32px; position:sticky; top:0; z-index:10; }
.topbar h2 { font-size:1.125rem; font-weight:700; color:var(--color-text-primary); }
.topbar-right { display:flex; align-items:center; gap:16px; }
.search-box { position:relative; display:flex; align-items:center; }
.search-box .el-icon { position:absolute; left:12px; color:var(--color-text-muted); font-size:0.875rem; }
.search-box input { width:224px; padding:8px 12px 8px 36px; border-radius:8px; border:1px solid rgba(0,0,0,0.04); background:var(--color-bg-input); font-size:0.75rem; color:var(--color-text-primary); outline:none; transition:all 0.3s; }
.search-box input:focus { border-color:var(--color-primary-border); box-shadow:0 0 0 3px rgba(45,106,79,0.1); }
.search-box input::placeholder { color:var(--color-text-muted); }
.notify-btn { width:36px; height:36px; border-radius:8px; border:none; background:none; cursor:pointer; position:relative; display:flex; align-items:center; justify-content:center; color:var(--color-text-muted); }
.notify-btn:hover { color:var(--color-primary); background:var(--color-primary-bg); }
.notify-dot { position:absolute; top:6px; right:6px; width:8px; height:8px; border-radius:50%; background:var(--color-error); }
.topbar-divider { width:1px; height:24px; background:rgba(0,0,0,0.06); }
.topbar-user { display:flex; align-items:center; gap:8px; cursor:pointer; }
.topbar-user span:first-child { width:32px; height:32px; border-radius:8px; background:var(--color-primary-bg); display:flex; align-items:center; justify-content:center; font-size:0.875rem; }
.topbar-user span:last-child { font-size:0.75rem; font-weight:500; color:var(--color-text-primary); }

.content-area { padding:32px; }
</style>
