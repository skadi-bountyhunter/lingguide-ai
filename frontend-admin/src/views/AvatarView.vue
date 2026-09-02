<template>
  <div class="avatar-page animate-fade-up">
    <header class="avatar-hero">
      <div class="hero-copy">
        <span class="hero-kicker">XINGYUN · GUIDE ROSTER</span>
        <h2>数字人管理</h2>
        <p>管理已在星云平台创建的讲解员预设。启用后，游客端将加载对应的数字人驱动应用。</p>
      </div>
      <div class="hero-actions">
        <el-button plain :loading="loading" @click="loadPresets">
          <el-icon><RefreshRight /></el-icon>刷新状态
        </el-button>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>新建角色预设
        </el-button>
      </div>
    </header>

    <section v-if="activePreset" class="current-dossier">
      <div class="dossier-seal">{{ initials(activePreset.name) }}</div>
      <div class="dossier-main">
        <div class="dossier-eyebrow"><span class="live-dot" />当前游客端讲解员</div>
        <h3>{{ activePreset.name }}</h3>
        <p>{{ activePreset.description || '此角色将作为当前游客端的默认数字人讲解员。' }}</p>
        <div class="dossier-tags">
          <span>{{ activePreset.scene_label || '景区讲解' }}</span>
          <span v-if="activePreset.voice_label">{{ activePreset.voice_label }}</span>
          <span v-if="activePreset.performance_style">{{ activePreset.performance_style }}</span>
        </div>
      </div>
      <div class="dossier-state" :class="activePreset.sdk_configured ? 'ready' : 'waiting'">
        <span class="state-label">星云运行配置</span>
        <strong>{{ activePreset.sdk_configured ? '已就绪' : '等待配置' }}</strong>
        <small>{{ activePreset.sdk_configured ? '可由游客端安全代理连接' : '请编辑角色并填写星云应用 ID 与 Secret' }}</small>
      </div>
    </section>

    <section class="roster-section">
      <div class="section-heading">
        <div>
          <span>角色花名册</span>
          <p>角色预设与星云应用凭据均持久化保存；游客端仅通过服务端会话代理连接。</p>
        </div>
        <b>{{ presets.length }} 个预设</b>
      </div>

      <div v-if="loading" class="loading-grid">
        <div v-for="index in 3" :key="index" class="skeleton-card" />
      </div>
      <el-empty v-else-if="!presets.length" description="暂无数字人角色预设" :image-size="72">
        <el-button type="primary" @click="openCreate">创建首个角色预设</el-button>
      </el-empty>
      <div v-else class="preset-grid">
        <article v-for="preset in presets" :key="preset.preset_key" class="preset-card" :class="{ active: preset.is_active, unavailable: !preset.sdk_configured }">
          <div class="card-topline">
            <span class="preset-key">{{ preset.preset_key }}</span>
            <el-tag v-if="preset.is_active" type="success" effect="light">正在服务</el-tag>
            <el-tag v-else-if="preset.sdk_configured" type="info" effect="plain">可启用</el-tag>
            <el-tag v-else type="warning" effect="light">待配 SDK</el-tag>
          </div>
          <div class="portrait" :class="{ portraitImage: preset.thumbnail_url }">
            <img v-if="preset.thumbnail_url" :src="preset.thumbnail_url" :alt="preset.name" @error="clearBrokenImage(preset)" />
            <span v-else>{{ initials(preset.name) }}</span>
          </div>
          <h3>{{ preset.name }}</h3>
          <p class="preset-description">{{ preset.description || '尚未填写角色说明。' }}</p>
          <dl class="role-meta">
            <div><dt>服务场景</dt><dd>{{ preset.scene_label || '景区讲解' }}</dd></div>
            <div><dt>音色设定</dt><dd>{{ preset.voice_label || '未标注' }}</dd></div>
            <div><dt>表演风格</dt><dd>{{ preset.performance_style || '未标注' }}</dd></div>
            <div><dt>星云应用 ID</dt><dd>{{ preset.app_id || '未配置' }}</dd></div>
            <div><dt>应用 Secret</dt><dd>{{ preset.secret_masked || '未配置' }}</dd></div>
          </dl>
          <p v-if="preset.uses_legacy_credentials" class="setup-hint">当前沿用此前默认角色 SDK 配置；编辑后可保存为此角色专属凭据</p>
          <p v-else-if="!preset.sdk_configured" class="setup-hint">请编辑 <code>{{ preset.preset_key }}</code>，填写星云应用 ID 与 Secret</p>
          <div class="card-actions">
            <el-button text @click="openEdit(preset)"><el-icon><EditPen /></el-icon>编辑</el-button>
            <el-button v-if="!preset.is_active" type="primary" text :disabled="!preset.sdk_configured" @click="activate(preset)">
              <el-icon><Star /></el-icon>设为当前讲解员
            </el-button>
            <el-button v-if="!preset.is_active && preset.preset_key !== 'default_guide'" type="danger" text @click="removePreset(preset)">
              <el-icon><Delete /></el-icon>删除
            </el-button>
          </div>
        </article>
      </div>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingKey ? '编辑角色预设' : '新建角色预设'" width="620px" destroy-on-close @closed="resetSecret">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="角色预设标识" prop="preset_key">
          <el-input v-model="form.preset_key" :disabled="Boolean(editingKey)" placeholder="例如 hanfu_guide" />
          <p class="form-help">仅支持小写字母、数字和下划线；创建后不可修改，用于匹配服务器侧星云 SDK 配置。</p>
        </el-form-item>
        <el-form-item label="角色名称" prop="name"><el-input v-model="form.name" placeholder="例如：汉服文化讲解员" /></el-form-item>
        <el-form-item label="角色说明"><el-input v-model="form.description" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="说明该角色适合的讲解场景与服务特点" /></el-form-item>
        <div class="form-two-cols">
          <el-form-item label="服务场景"><el-input v-model="form.scene_label" placeholder="例如：传统文化讲解" /></el-form-item>
          <el-form-item label="音色设定"><el-input v-model="form.voice_label" placeholder="例如：温柔女声" /></el-form-item>
        </div>
        <div class="form-two-cols">
          <el-form-item label="表演风格"><el-input v-model="form.performance_style" placeholder="例如：古风讲解" /></el-form-item>
          <el-form-item label="排序"><el-input-number v-model="form.sort_order" :min="0" :max="9999" controls-position="right" style="width:100%" /></el-form-item>
        </div>
        <el-form-item label="缩略图地址（可选）"><el-input v-model="form.thumbnail_url" placeholder="例如：https://.../avatar.png" /></el-form-item>
        <div class="credential-section">
          <strong>星云应用凭据</strong>
          <p>{{ editingKey ? '为安全起见不回显 Secret；留空表示保持现有凭据不变。' : '用于切换该角色对应的星云数字人应用。' }}</p>
          <el-form-item label="星云应用 ID" prop="app_id"><el-input v-model="form.app_id" :disabled="form.clear_credentials" placeholder="输入该角色在星云平台的应用 ID" /></el-form-item>
          <el-form-item label="星云应用 Secret" prop="app_secret">
            <el-input v-model="form.app_secret" type="password" show-password :disabled="form.clear_credentials" :placeholder="editingKey ? '留空则保持不变' : '输入该角色在星云平台的应用 Secret'" />
          </el-form-item>
          <el-checkbox v-if="editingKey && hasExistingCredentials" v-model="form.clear_credentials">明确清除现有应用 ID 与 Secret</el-checkbox>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePreset">{{ editingKey ? '保存修改' : '创建预设' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import api from '@/services/api'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import * as Icons from '@element-plus/icons-vue'

const { Delete, EditPen, Plus, RefreshRight, Star } = Icons

interface AvatarPreset {
  id: string
  preset_key: string
  name: string
  description: string
  scene_label: string
  voice_label: string
  performance_style: string
  thumbnail_url: string
  sort_order: number
  is_active: boolean
  sdk_configured: boolean
  app_id: string
  secret_masked: string
  uses_legacy_credentials: boolean
}

const EMPTY_FORM = () => ({
  preset_key: '', name: '', description: '', scene_label: '景区讲解', voice_label: '',
  performance_style: '', thumbnail_url: '', sort_order: 0, app_id: '', app_secret: '', clear_credentials: false,
})

const presets = ref<AvatarPreset[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingKey = ref('')
const formRef = ref<FormInstance>()
const form = reactive(EMPTY_FORM())
const activePreset = computed(() => presets.value.find(item => item.is_active) || null)
const hasExistingCredentials = computed(() => {
  const preset = presets.value.find(item => item.preset_key === editingKey.value)
  return Boolean(preset?.app_id || preset?.secret_masked || preset?.uses_legacy_credentials)
})
const rules: FormRules = {
  preset_key: [
    { required: true, message: '请输入角色预设标识', trigger: 'blur' },
    { pattern: /^[a-z][a-z0-9_]*$/, message: '请使用小写字母、数字和下划线，并以字母开头', trigger: 'blur' },
  ],
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  app_id: [{ validator: (_rule, value, callback) => (editingKey.value || Boolean(value) === Boolean(form.app_secret) ? callback() : callback(new Error('应用 ID 与 Secret 必须同时填写'))), trigger: 'blur' }],
  app_secret: [{ validator: (_rule, value, callback) => (editingKey.value || Boolean(value) === Boolean(form.app_id) ? callback() : callback(new Error('应用 ID 与 Secret 必须同时填写'))), trigger: 'blur' }],
}

function initials(name: string) {
  return (name || '灵').replace(/\s/g, '').slice(0, 2)
}

function clearBrokenImage(preset: AvatarPreset) {
  preset.thumbnail_url = ''
}

function resetSecret() {
  form.app_secret = ''
  form.clear_credentials = false
  formRef.value?.clearValidate()
}

async function loadPresets() {
  loading.value = true
  try {
    const { data } = await api.get<{ presets: AvatarPreset[] }>('/api/avatar/presets')
    presets.value = data.presets
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '读取数字人角色失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingKey.value = ''
  Object.assign(form, EMPTY_FORM())
  dialogVisible.value = true
}

function openEdit(preset: AvatarPreset) {
  editingKey.value = preset.preset_key
  Object.assign(form, {
    preset_key: preset.preset_key, name: preset.name, description: preset.description,
    scene_label: preset.scene_label, voice_label: preset.voice_label,
    performance_style: preset.performance_style, thumbnail_url: preset.thumbnail_url,
    sort_order: preset.sort_order, app_id: preset.app_id, app_secret: '', clear_credentials: false,
  })
  dialogVisible.value = true
}

async function savePreset() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload: Partial<ReturnType<typeof EMPTY_FORM>> = { ...form }
    if (editingKey.value) {
      delete payload.preset_key
      if (!payload.app_id?.trim()) delete payload.app_id
      if (!payload.app_secret?.trim()) delete payload.app_secret
      await api.put(`/api/avatar/presets/${editingKey.value}`, payload)
      ElMessage.success('角色预设已保存')
    } else {
      delete payload.clear_credentials
      await api.post('/api/avatar/presets', payload)
      ElMessage.success('角色预设已创建，可启用对应的星云应用')
    }
    dialogVisible.value = false
    await loadPresets()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存角色预设失败')
  } finally {
    saving.value = false
  }
}

async function activate(preset: AvatarPreset) {
  try {
    await ElMessageBox.confirm(`启用“${preset.name}”后，之后唤醒数字人的游客端将加载该角色。`, '切换当前讲解员', {
      type: 'warning', confirmButtonText: '确认启用', cancelButtonText: '取消',
    })
    await api.post(`/api/avatar/presets/${preset.preset_key}/activate`, null)
    ElMessage.success(`已启用${preset.name}`)
    await loadPresets()
  } catch (error: any) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error?.response?.data?.detail || '启用角色失败')
  }
}

async function removePreset(preset: AvatarPreset) {
  try {
    await ElMessageBox.confirm(`删除“${preset.name}”后无法恢复角色说明，但不会影响星云控制台中的应用。`, '删除角色预设', {
      type: 'warning', confirmButtonText: '删除', confirmButtonClass: 'el-button--danger', cancelButtonText: '取消',
    })
    await api.delete(`/api/avatar/presets/${preset.preset_key}`)
    ElMessage.success('角色预设已删除')
    await loadPresets()
  } catch (error: any) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error?.response?.data?.detail || '删除角色预设失败')
  }
}

onMounted(loadPresets)
</script>

<style scoped>
.avatar-page { --ink:#18312d; --deep:#123e3a; --jade:#2d6a4f; --mist:#e9f0e8; --sand:#f5f1e8; --amber:#c8802d; display:flex; flex-direction:column; gap:22px; max-width:1240px; }
.avatar-hero { min-height:166px; padding:28px 30px; display:flex; align-items:flex-end; justify-content:space-between; gap:24px; border-radius:20px; color:#fff; overflow:hidden; position:relative; background:linear-gradient(112deg,var(--deep),#1f6359 62%,#328373); box-shadow:0 16px 32px rgba(18,62,58,.16); }
.avatar-hero::after { content:'云'; position:absolute; right:28px; top:-30px; font:900 180px/1 Georgia,serif; color:rgba(255,255,255,.07); transform:rotate(-8deg); }
.hero-copy,.hero-actions { position:relative; z-index:1; }.hero-copy { max-width:660px; }.hero-kicker { font-size:10px; letter-spacing:.18em; font-weight:700; color:#cbe8d9; }.hero-copy h2 { margin:8px 0 6px; font-size:1.55rem; letter-spacing:.02em; }.hero-copy p { max-width:610px; margin:0; font-size:.8rem; line-height:1.7; color:rgba(255,255,255,.77); }.hero-actions { display:flex; gap:10px; flex-shrink:0; }.hero-actions :deep(.el-button--default) { border-color:rgba(255,255,255,.35); color:#fff; background:rgba(255,255,255,.08); }.hero-actions :deep(.el-button--primary) { border:0; color:#173c36; background:#e9f1e7; }
.current-dossier { display:grid; grid-template-columns:76px minmax(0,1fr) 236px; align-items:center; gap:20px; padding:20px 24px; border:1px solid #dae8df; border-left:5px solid var(--jade); border-radius:16px; background:linear-gradient(100deg,#fbfdfb,#f1f7f2); }.dossier-seal,.portrait { display:flex; align-items:center; justify-content:center; color:#fff; font-weight:800; background:radial-gradient(circle at 30% 25%,#6bb38b,#245d4d 68%); }.dossier-seal { width:64px; height:64px; border-radius:50%; font-size:1.12rem; box-shadow:inset 0 0 0 5px rgba(255,255,255,.16); }.dossier-eyebrow { display:flex; align-items:center; gap:6px; color:#4a7862; font-size:.7rem; font-weight:700; }.live-dot { width:7px; height:7px; border-radius:50%; background:#3da76a; box-shadow:0 0 0 4px rgba(61,167,106,.12); }.dossier-main h3 { margin:5px 0; color:var(--ink); font-size:1.1rem; }.dossier-main p { margin:0; color:#65766f; font-size:.78rem; }.dossier-tags { display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }.dossier-tags span { padding:3px 8px; color:#477361; font-size:.68rem; border-radius:99px; background:#e4f0e7; }.dossier-state { align-self:stretch; display:flex; flex-direction:column; justify-content:center; padding-left:20px; border-left:1px dashed #b9d0c1; }.state-label { color:#72867d; font-size:.67rem; }.dossier-state strong { margin:3px 0; font-size:1rem; }.dossier-state.ready strong { color:#24734f; }.dossier-state.waiting strong { color:#b67524; }.dossier-state small { color:#75857e; font-size:.68rem; line-height:1.45; }
.guide-note { display:flex; align-items:flex-start; gap:10px; padding:13px 16px; color:#77572c; border-radius:12px; background:#fff8e9; border:1px solid #f0dfb8; }.guide-note .el-icon { margin-top:1px; color:#bd7b24; font-size:17px; }.guide-note strong,.guide-note span { font-size:.74rem; line-height:1.65; }.guide-note span { display:block; color:#826c4d; }
.roster-section { padding:24px; border-radius:18px; background:#fff; border:1px solid rgba(18,62,58,.08); }.section-heading { display:flex; align-items:flex-end; justify-content:space-between; gap:20px; margin-bottom:20px; }.section-heading span { color:var(--ink); font-size:1rem; font-weight:700; }.section-heading p { margin:5px 0 0; color:#7a8882; font-size:.73rem; }.section-heading b { color:#4b6e60; font-size:.7rem; white-space:nowrap; }
.preset-grid,.loading-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:16px; }.preset-card { position:relative; display:flex; flex-direction:column; padding:16px; min-height:330px; border:1px solid #e3ebe5; border-radius:15px; background:#fcfdfc; transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease; }.preset-card:hover { transform:translateY(-3px); border-color:#afd0ba; box-shadow:0 10px 24px rgba(24,49,45,.08); }.preset-card.active { border:2px solid #419266; background:linear-gradient(150deg,#fff,#f1f8f2); }.preset-card.unavailable:not(.active) { background:linear-gradient(150deg,#fdfdfb,#faf8f2); }.card-topline { min-height:22px; display:flex; align-items:center; justify-content:space-between; gap:8px; }.preset-key { overflow:hidden; max-width:135px; color:#7b8c84; font:600 .62rem/1 ui-monospace,SFMono-Regular,Menlo,monospace; text-overflow:ellipsis; white-space:nowrap; }.portrait { width:58px; height:58px; margin:18px 0 12px; overflow:hidden; border-radius:18px; font-size:1rem; }.portrait img { width:100%; height:100%; object-fit:cover; }.preset-card h3 { margin:0; color:var(--ink); font-size:1rem; }.preset-description { height:38px; margin:6px 0 13px; color:#708078; font-size:.72rem; line-height:1.55; overflow:hidden; }.role-meta { margin:0; padding:10px 0; display:grid; gap:7px; border-top:1px solid #edf1ee; }.role-meta div { display:flex; justify-content:space-between; gap:10px; font-size:.68rem; }.role-meta dt { color:#85938d; }.role-meta dd { max-width:150px; margin:0; overflow:hidden; color:#4f645b; text-align:right; text-overflow:ellipsis; white-space:nowrap; }.setup-hint { min-height:34px; margin:8px 0 0; color:#a07132; font-size:.66rem; line-height:1.45; }.setup-hint code { padding:1px 3px; color:#815e31; border-radius:3px; background:#f6ebd6; }.card-actions { margin-top:auto; padding-top:11px; display:flex; flex-wrap:wrap; gap:2px; border-top:1px solid #edf1ee; }.card-actions :deep(.el-button) { margin:0; padding:7px 5px; font-size:.68rem; }.skeleton-card { height:330px; border-radius:15px; background:linear-gradient(90deg,#f1f4f1 25%,#f8faf8 37%,#f1f4f1 63%); background-size:400% 100%; animation:shimmer 1.35s infinite; }@keyframes shimmer { 0% { background-position:100% 0 } 100% { background-position:0 0 } }
.form-help { margin:5px 0 0; color:#83918b; font-size:.68rem; line-height:1.45; }.form-two-cols { display:grid; grid-template-columns:1fr 1fr; gap:16px; }.credential-section { margin-top:8px; padding:14px 16px 2px; border:1px solid #dbe9df; border-radius:12px; background:#f7fbf8; }.credential-section strong { color:var(--ink); font-size:.82rem; }.credential-section p { margin:5px 0 13px; color:#708078; font-size:.68rem; line-height:1.55; }
@media (max-width:800px) { .avatar-hero { align-items:flex-start; flex-direction:column; }.current-dossier { grid-template-columns:58px 1fr; }.dossier-seal { width:54px; height:54px; }.dossier-state { grid-column:1/-1; padding:12px 0 0; border-top:1px dashed #b9d0c1; border-left:0; }.hero-actions { width:100%; }.form-two-cols { grid-template-columns:1fr; gap:0; } }
</style>
