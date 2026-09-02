<template>
  <div class="users-page animate-fade-up">
    <div class="page-hd">
      <div><h2>👥 用户管理</h2><p>管理注册用户数据</p></div>
      <div class="hd-stats">
        <span>共 <b>{{ total }}</b> 个用户</span>
      </div>
    </div>

    <div class="card section-card">
      <el-table :data="items" v-loading="loading" style="width:100%">
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="id" label="用户ID" min-width="240" show-overflow-tooltip />
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="s">{{ s.row.created_at?.slice(0, 19).replace('T', ' ') }}</template>
        </el-table-column>
      </el-table>

      <div class="pager-row" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchUsers"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const items = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20

onMounted(() => fetchUsers())

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await api.get('/api/users', { params: { page: page.value, page_size: pageSize } })
    items.value = data.items
    total.value = data.total
  } catch { /* noop */ }
  finally { loading.value = false }
}
</script>

<style scoped>
.users-page { display:flex; flex-direction:column; gap:24px; }
.page-hd { display:flex; justify-content:space-between; align-items:center; }
.page-hd h2 { font-size:1rem; font-weight:700; color:var(--color-text-primary); }
.page-hd p { font-size:0.75rem; color:var(--color-text-muted); margin-top:4px; }
.hd-stats { font-size:0.875rem; color:var(--color-text-secondary); }
.hd-stats b { color:var(--color-primary); }
.section-card { padding:20px; }
.pager-row { margin-top:16px; display:flex; justify-content:center; }
</style>
