<template>
  <article class="route-plan-card">
    <header class="route-card-header">
      <div class="route-heading">
        <span class="route-identity" :class="{ saved: mode === 'saved' }">
          <el-icon>
            <Collection v-if="mode === 'saved'" />
            <Guide v-else />
          </el-icon>
          {{ mode === 'saved' ? t('routeCard.saved') : t('routeCard.recommended') }}
        </span>
        <h3>{{ route.title }}</h3>
      </div>

      <div class="route-meta">
        <span v-if="route.duration">
          <el-icon><Clock /></el-icon>
          {{ route.duration }}
        </span>
        <time v-if="mode === 'saved' && createdAtText" :datetime="createdAt">
          {{ createdAtText }}
        </time>
      </div>
    </header>

    <!-- 站点顺序即游览顺序，竖线用于强化路线方向。 -->
    <VueDraggableNext
      v-if="isEditing"
      v-model="editableSpots"
      tag="ol"
      class="route-stations editing"
      :aria-label="t('routeCard.stations')"
      handle=".drag-handle"
    >
      <li v-for="(spot, index) in editableSpots" :key="`${spot.name}-${index}`">
        <span class="drag-handle" aria-label="拖拽排序">⋮⋮</span>
        <span class="station-marker" aria-hidden="true">{{ index + 1 }}</span>
        <div class="station-copy">
          <strong class="station-name" @click="emit('focus-spot', spot.name)">{{ spot.display_name || spot.name }}</strong>
          <p v-if="spot.description">{{ spot.description }}</p>
        </div>
        <button
          type="button"
          class="remove-spot-btn"
          :disabled="editableSpots.length <= 2"
          @click="removeSpot(index)"
          :aria-label="`删除${spot.name}`"
        >
          <el-icon><Close /></el-icon>
        </button>
      </li>
    </VueDraggableNext>
    <ol v-else class="route-stations" :aria-label="t('routeCard.stations')">
      <li v-for="(spot, index) in displaySpots" :key="`${spot.name}-${index}`">
        <span class="station-marker" aria-hidden="true">{{ index + 1 }}</span>
        <div class="station-copy">
          <strong class="station-name" @click="emit('focus-spot', spot.name)">{{ spot.display_name || spot.name }}</strong>
          <p v-if="spot.description">{{ spot.description }}</p>
        </div>
      </li>
    </ol>

    <aside v-if="route.tips" class="route-tips">
      <span class="tips-label">{{ t('routeCard.tips') }}</span>
      <p>{{ route.tips }}</p>
    </aside>

    <button
      v-if="isEditing"
      type="button"
      class="add-spot-trigger"
      @click="emit('add-spot')"
    >
      <el-icon><Plus /></el-icon>
      添加景点
    </button>

    <details v-if="route.citations?.length" class="route-evidence">
      <summary>{{ t('routeCard.evidence', { count: route.citations.length }) }}</summary>
      <div v-for="citation in route.citations" :key="citation.id" class="route-evidence-item">
        <strong>{{ citation.id }} · {{ citation.source?.title || citation.source?.filename || t('routeCard.scenicSource') }}</strong>
        <p>{{ citation.quote }}</p>
        <small v-if="citation.as_of">{{ t('routeCard.dataTime', { time: citation.as_of }) }}</small>
      </div>
      <small v-if="route.traceId || route.trace_id" class="route-trace">{{ t('routeCard.trace', { id: route.traceId || route.trace_id }) }}</small>
    </details>

    <footer class="route-actions">
      <button
        v-if="!isEditing"
        type="button"
        class="route-button map-button"
        :disabled="saving || deleting"
        @click="emit('show-map')"
      >
        <el-icon><Guide /></el-icon>
        {{ t('routeCard.viewMap') }}
      </button>

      <button
        v-if="mode === 'generated' && !isEditing && editable"
        type="button"
        class="route-button edit-button"
        :disabled="saving"
        @click="startEdit"
      >
        <el-icon><Edit /></el-icon>
        编辑路线
      </button>

      <button
        v-if="mode === 'generated' && !isEditing"
        type="button"
        class="route-button save-button"
        :disabled="saved || saving"
        @click="emit('save')"
      >
        <el-icon :class="{ 'is-loading': saving }">
          <Loading v-if="saving" />
          <Collection v-else />
        </el-icon>
        {{ saving ? t('routeCard.saving') : saved ? t('routeCard.saved') : t('routeCard.save') }}
      </button>

      <button
        v-if="mode === 'saved' && !isEditing"
        type="button"
        class="route-button delete-button"
        :disabled="deleting"
        @click="emit('delete')"
      >
        <el-icon :class="{ 'is-loading': deleting }">
          <Loading v-if="deleting" />
          <Delete v-else />
        </el-icon>
        {{ deleting ? t('routeCard.deleting') : t('routeCard.delete') }}
      </button>

      <button
        v-if="isEditing"
        type="button"
        class="route-button cancel-button"
        @click="cancelEdit"
      >
        <el-icon><Close /></el-icon>
        取消
      </button>

      <button
        v-if="isEditing"
        type="button"
        class="route-button save-edit-button"
        :disabled="editableSpots.length < 2"
        @click="saveEdit"
      >
        <el-icon><Check /></el-icon>
        保存修改
      </button>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { VueDraggableNext } from 'vue-draggable-next'
import type { RoutePlan, RouteSpot } from '../types/route'

const { t, locale } = useI18n()
const props = withDefaults(defineProps<{
  route: RoutePlan
  mode: 'generated' | 'saved'
  saved?: boolean
  saving?: boolean
  deleting?: boolean
  createdAt?: string
  editable?: boolean
}>(), {
  saved: false,
  saving: false,
  deleting: false,
  createdAt: '',
  editable: false,
})

const emit = defineEmits<{
  save: []
  'show-map': []
  delete: []
  'update:spots': [spots: RouteSpot[]]
  'edit': []
  'recalculate': []
  'add-spot': []
  'focus-spot': [name: string]
}>()

const isEditing = ref(false)
const editableSpots = ref<RouteSpot[]>([...props.route.spots])

const createdAtText = computed(() => {
  if (!props.createdAt) return ''

  const date = new Date(props.createdAt)
  if (Number.isNaN(date.getTime())) return props.createdAt

  return new Intl.DateTimeFormat(locale.value, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
})

function startEdit() {
  isEditing.value = true
  editableSpots.value = [...props.route.spots]
  emit('edit')
}

function cancelEdit() {
  isEditing.value = false
  editableSpots.value = [...props.route.spots]
}

function saveEdit() {
  emit('update:spots', editableSpots.value)
  isEditing.value = false
  emit('recalculate')
}

function removeSpot(index: number) {
  editableSpots.value.splice(index, 1)
}

const displaySpots = computed(() => {
  return isEditing.value ? editableSpots.value : props.route.spots
})
</script>

<style scoped>
.route-plan-card {
  width: 100%;
  min-width: 0;
  overflow: hidden;
  padding: 18px;
  background: var(--color-bg-card);
  border: 1px solid rgba(45, 106, 79, 0.1);
  border-radius: 16px;
  box-shadow: var(--shadow-card);
  color: var(--color-text-primary);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.route-plan-card:hover {
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-card-hover);
}

.route-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(27, 42, 61, 0.06);
}

.route-heading {
  min-width: 0;
}

.route-identity {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 7px;
  padding: 3px 8px;
  color: var(--color-primary);
  background: var(--color-primary-bg);
  border: 1px solid var(--color-primary-border);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.4;
}

.route-identity.saved {
  color: var(--color-accent);
  background: var(--color-accent-bg);
  border-color: var(--color-accent-border);
}

.route-heading h3 {
  overflow-wrap: anywhere;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.45;
}

.route-meta {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  align-items: flex-end;
  gap: 5px;
  padding-top: 2px;
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.4;
  white-space: nowrap;
}

.route-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-accent);
  font-weight: 600;
}

.route-stations {
  margin: 18px 0;
  list-style: none;
}

.route-stations li {
  position: relative;
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr);
  gap: 11px;
  min-height: 58px;
  padding-bottom: 14px;
}

.route-stations li:last-child {
  min-height: auto;
  padding-bottom: 0;
}

.route-stations li:not(:last-child)::before {
  position: absolute;
  top: 25px;
  bottom: -1px;
  left: 12px;
  width: 2px;
  background: linear-gradient(var(--color-primary-lighter), var(--color-accent-lighter));
  content: '';
}

.station-marker {
  position: relative;
  z-index: 1;
  display: grid;
  width: 26px;
  height: 26px;
  place-items: center;
  color: #fff;
  background: var(--color-primary);
  border: 3px solid #edf5f0;
  border-radius: 50%;
  box-shadow: 0 0 0 1px var(--color-primary-border);
  font-size: 10px;
  font-weight: 700;
}

.route-stations li:last-child .station-marker {
  background: var(--color-accent);
  border-color: #f7f0e9;
  box-shadow: 0 0 0 1px var(--color-accent-border);
}

.station-copy {
  min-width: 0;
  padding-top: 2px;
}

.station-copy strong {
  display: block;
  overflow-wrap: anywhere;
  font-size: 13px;
  line-height: 1.5;
}

.station-name {
  cursor: pointer;
  transition: color 0.15s ease;
}

.station-name:hover {
  color: var(--color-primary);
  text-decoration: underline;
}

.station-copy p {
  margin-top: 2px;
  overflow-wrap: anywhere;
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.6;
}

.route-tips {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 9px;
  padding: 10px 12px;
  background: var(--color-accent-bg);
  border-left: 3px solid var(--color-accent);
  border-radius: 4px 10px 10px 4px;
}

.tips-label {
  color: var(--color-accent);
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.route-tips p {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--color-text-secondary);
  font-size: 11px;
  line-height: 1.6;
}

.route-evidence {
  margin-top: 14px;
  padding: 9px 11px;
  border: 1px solid rgba(45, 106, 79, 0.12);
  border-radius: 10px;
  background: rgba(45, 106, 79, 0.035);
  color: var(--color-text-muted);
  font-size: 11px;
}

.route-evidence summary {
  cursor: pointer;
  color: var(--color-primary);
  font-weight: 700;
}

.route-evidence-item {
  margin-top: 8px;
  padding: 7px 8px;
  border-radius: 7px;
  background: var(--color-bg-card);
}

.route-evidence-item strong {
  color: var(--color-text-secondary);
}

.route-evidence-item p {
  margin-top: 3px;
  line-height: 1.5;
}

.route-evidence-item small,
.route-trace {
  display: block;
  margin-top: 3px;
  opacity: 0.8;
}

.route-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 16px;
}

.route-stations.editing li {
  grid-template-columns: 20px 26px minmax(0, 1fr) 28px;
  gap: 8px;
}

.drag-handle {
  cursor: move;
  color: var(--color-text-muted);
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  padding-top: 2px;
}

.drag-handle:hover {
  color: var(--color-primary);
}

.remove-spot-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid rgba(196, 84, 74, 0.2);
  background: rgba(196, 84, 74, 0.06);
  color: var(--color-error);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  padding: 0;
  flex-shrink: 0;
}

.remove-spot-btn:hover:not(:disabled) {
  background: var(--color-error);
  color: #fff;
  border-color: var(--color-error);
}

.remove-spot-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.route-button {
  display: inline-flex;
  min-width: 0;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 10px;
  border: 1px solid transparent;
  border-radius: 10px;
  font: inherit;
  font-size: 12px;
  font-weight: 650;
  line-height: 1.2;
  cursor: pointer;
  transition: color 0.2s ease, background 0.2s ease, border-color 0.2s ease,
    transform 0.2s ease;
}

.route-button:active:not(:disabled) {
  transform: scale(0.98);
}

.route-button:focus-visible {
  outline: 3px solid rgba(64, 145, 108, 0.28);
  outline-offset: 2px;
}

.route-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.map-button {
  color: var(--color-primary);
  background: var(--color-primary-bg);
  border-color: var(--color-primary-border);
}

.map-button:hover:not(:disabled) {
  color: #fff;
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.save-button {
  color: #fff;
  background: var(--color-accent);
  box-shadow: 0 3px 10px rgba(176, 125, 79, 0.18);
}

.save-button:hover:not(:disabled) {
  background: var(--color-accent-light);
}

.delete-button {
  color: var(--color-error);
  background: rgba(196, 84, 74, 0.06);
  border-color: rgba(196, 84, 74, 0.16);
}

.delete-button:hover:not(:disabled) {
  color: #fff;
  background: var(--color-error);
  border-color: var(--color-error);
}

.edit-button {
  color: var(--color-primary);
  background: var(--color-primary-bg);
  border-color: var(--color-primary-border);
}

.edit-button:hover:not(:disabled) {
  color: #fff;
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.cancel-button {
  color: var(--color-text-secondary);
  background: var(--color-bg-elevated);
  border-color: rgba(0,0,0,0.1);
}

.cancel-button:hover:not(:disabled) {
  background: rgba(0,0,0,0.08);
}

.save-edit-button {
  color: #fff;
  background: var(--color-primary);
  box-shadow: 0 3px 10px rgba(64, 145, 108, 0.18);
}

.save-edit-button:hover:not(:disabled) {
  background: var(--color-primary-light);
}

.add-spot-trigger {
  width: 100%; margin-top: 12px; padding: 10px;
  border: 1px dashed var(--color-primary-border);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-size: 13px; font-weight: 600;
  border-radius: 10px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: all 0.2s;
}

.add-spot-trigger:hover {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

@media (max-width: 360px) {
  .route-plan-card {
    padding: 15px;
  }

  .route-card-header {
    flex-direction: column;
  }

  .route-meta {
    align-items: flex-start;
  }

  .route-actions {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .route-plan-card,
  .route-button {
    transition: none;
  }

  .route-button:active:not(:disabled) {
    transform: none;
  }
}
</style>
