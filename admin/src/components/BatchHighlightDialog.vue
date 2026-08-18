<template>
  <el-dialog
    :model-value="modelValue"
    title="批量亮点群发"
    width="900px"
    top="5vh"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <div v-loading="loading">
      <el-alert type="info" :closable="false" show-icon style="margin-bottom:14px">
        <template #title>
          选择一条线路，按小区 / 标签筛选客户并勾选，一键为每位客户生成「带入其偏好的个性化亮点介绍」。
          结果可逐条复制，或「复制全部」后粘贴到微信群发。真正的微信订阅消息推送需配置 AppSecret 与模板，本工具负责批量生成内容。
        </template>
      </el-alert>

      <!-- 筛选区 -->
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:14px">
        <span style="font-size:13px;color:#606266;white-space:nowrap">线路：</span>
        <el-select
          v-model="routeId"
          filterable
          placeholder="搜索并选择线路"
          style="width:280px"
          :loading="loadingRoutes"
          @change="clearResults"
        >
          <el-option v-for="r in routeOptions" :key="r.id" :label="`${r.name}（${r.destination}·${r.days}天）`" :value="r.id" />
        </el-select>

        <span style="font-size:13px;color:#606266;white-space:nowrap">小区：</span>
        <el-select
          v-model="community"
          filterable
          allow-create
          clearable
          placeholder="按小区筛选（可选）"
          style="width:200px"
          @change="applyFilter"
        >
          <el-option v-for="c in communityOptions" :key="c" :label="c" :value="c" />
        </el-select>

        <el-button type="primary" :disabled="!routeId" :loading="loading" @click="generate">
          为选中客户生成亮点
        </el-button>
      </div>

      <!-- 客户选择表 -->
      <el-table
        ref="tbl"
        :data="filteredCustomers"
        border
        height="300"
        @selection-change="onSelect"
        v-loading="loadingCustomers"
      >
        <el-table-column type="selection" width="46" />
        <el-table-column prop="name" label="客户" width="110" />
        <el-table-column prop="community" label="小区" width="140" />
        <el-table-column prop="tags" label="标签" width="140" show-overflow-tooltip />
        <el-table-column label="重点" width="70" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_key" type="warning" size="small">★</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="travel_preference" label="偏好" min-width="160" show-overflow-tooltip />
      </el-table>
      <div style="margin:8px 0;font-size:13px;color:#909399">
        已选 {{ selectedIds.length }} 位客户（共 {{ filteredCustomers.length }} 位匹配）
      </div>

      <!-- 生成结果 -->
      <template v-if="results.length">
        <el-divider>生成结果（{{ results.length }} 条）</el-divider>
        <div style="display:flex;justify-content:flex-end;margin-bottom:10px">
          <el-button type="success" @click="copyAll">复制全部全文</el-button>
        </div>
        <div v-for="(it, i) in results" :key="i" class="res-card">
          <div class="res-head">
            <strong>{{ it.customer_name || ('客户#' + it.customer_id) }}</strong>
            <el-button link type="primary" size="small" @click="copyOne(it)">复制此条</el-button>
          </div>
          <el-input :model-value="it.share_text" type="textarea" :rows="6" readonly />
          <div v-if="it.warning" style="color:#e6a23c;font-size:12px;margin-top:4px">{{ it.warning }}</div>
        </div>
      </template>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const loadingRoutes = ref(false)
const loadingCustomers = ref(false)
const routeOptions = ref([])
const routeId = ref(null)
const community = ref('')
const communityOptions = ref([])
const allCustomers = ref([])
const selectedIds = ref([])
const results = ref([])

const tbl = ref(null)

// 拉取线路列表（用于选择器）
async function loadRoutes() {
  loadingRoutes.value = true
  try {
    const res = await api.listRoutes({ pageSize: 200 })
    routeOptions.value = res.rows || []
  } catch (e) {
    ElMessage.error('线路列表加载失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loadingRoutes.value = false
  }
}

// 拉取客户（用于小区下拉 + 勾选表）；一次取足量，前端按小区/标签筛
async function loadCustomers() {
  loadingCustomers.value = true
  try {
    const res = await api.listCustomers({ pageSize: 500, include_deleted: true })
    allCustomers.value = res.rows || []
    const set = new Set()
    for (const c of allCustomers.value) if (c.community) set.add(c.community)
    communityOptions.value = Array.from(set)
  } catch (e) {
    ElMessage.error('客户列表加载失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loadingCustomers.value = false
  }
}

const filteredCustomers = computed(() => {
  if (!community.value) return allCustomers.value
  return allCustomers.value.filter(c => c.community === community.value)
})

function onSelect(rows) {
  selectedIds.value = rows.map(r => r.id)
}
function applyFilter() {
  selectedIds.value = []
  if (tbl.value) tbl.value.clearSelection()
}
function clearResults() {
  results.value = []
}

async function generate() {
  if (!routeId.value) { ElMessage.warning('请先选择线路'); return }
  if (!selectedIds.value.length) { ElMessage.warning('请勾选至少一位客户'); return }
  loading.value = true
  try {
    const data = await api.aiRouteHighlightBatch({
      route_id: Number(routeId.value),
      customer_ids: selectedIds.value.map(Number),
    })
    results.value = data || []
    const fallback = (data || []).filter(d => d.source === 'fallback').length
    if (fallback) {
      ElMessage.warning(`生成完成，其中 ${fallback} 条走兜底模板（大模型暂不可用）`)
    } else {
      ElMessage.success(`已为 ${results.value.length} 位客户生成个性化亮点`)
    }
  } catch (e) {
    ElMessage.error('批量生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function copyOne(it) {
  const t = it.share_text || ''
  copyText(t, `已复制「${it.customer_name || ('客户#' + it.customer_id)}」的亮点全文`)
}
function copyAll() {
  const all = results.value.map((it, i) =>
    `【${it.customer_name || ('客户#' + it.customer_id)}】\n` + (it.share_text || '')
  ).join('\n\n' + '—'.repeat(20) + '\n\n')
  copyText(all, `已复制全部 ${results.value.length} 条亮点全文`)
}
async function copyText(t, okMsg) {
  if (!t) return
  try {
    await navigator.clipboard.writeText(t)
    ElMessage.success(okMsg)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = t
    document.body.appendChild(ta)
    ta.select()
    try { document.execCommand('copy') } catch { /* ignore */ }
    document.body.removeChild(ta)
    ElMessage.success(okMsg)
  }
}

watch(() => props.modelValue, (v) => {
  if (v) {
    results.value = []
    selectedIds.value = []
    if (!routeOptions.value.length) loadRoutes()
    if (!allCustomers.value.length) loadCustomers()
  }
})

onMounted(() => {
  if (props.modelValue) {
    loadRoutes()
    loadCustomers()
  }
})
</script>

<style scoped>
.res-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  background: #fafafa;
}
.res-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
</style>
