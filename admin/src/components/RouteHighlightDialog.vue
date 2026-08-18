<template>
  <el-dialog
    :model-value="modelValue"
    title="线路亮点介绍"
    width="680px"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <div v-loading="loading">
      <!-- 客户页模式：未给定线路时，先让顾问选线路 -->
      <div v-if="!routeId" style="margin-bottom:14px;display:flex;gap:10px;align-items:center">
        <span style="font-size:13px;color:#606266;white-space:nowrap">选择线路：</span>
        <el-select
          v-model="pickedRouteId"
          filterable
          placeholder="搜索并选择线路"
          style="flex:1"
          :loading="loadingRoutes"
          @change="onPickRoute"
        >
          <el-option v-for="r in routeOptions" :key="r.id" :label="`${r.name}（${r.destination}·${r.days}天）`" :value="r.id" />
        </el-select>
      </div>

      <el-alert
        v-if="customerName"
        type="success"
        :closable="false"
        show-icon
        style="margin-bottom:14px"
      >
        <template #title>已为「{{ customerName }}」带入偏好做个性化（年龄/预算/兴趣/小区）</template>
      </el-alert>

      <el-alert
        v-if="data && data.warning"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom:14px"
      >
        <template #title>{{ data.warning }}</template>
      </el-alert>

      <template v-if="data">
        <div v-if="data.overview" class="hl-block">
          <div class="hl-title">✨ 亮点概览</div>
          <div class="hl-text">{{ data.overview }}</div>
        </div>

        <div v-if="data.must_see && data.must_see.length" class="hl-block">
          <div class="hl-title">🌟 必看景点</div>
          <ul class="hl-list">
            <li v-for="(x, i) in data.must_see" :key="i">{{ x }}</li>
          </ul>
        </div>

        <div v-if="data.food && data.food.length" class="hl-block">
          <div class="hl-title">🍜 特色美食</div>
          <ul class="hl-list">
            <li v-for="(x, i) in data.food" :key="i">{{ x }}</li>
          </ul>
        </div>

        <div v-if="data.scenery && data.scenery.length" class="hl-block">
          <div class="hl-title">🏞 绝美风光</div>
          <ul class="hl-list">
            <li v-for="(x, i) in data.scenery" :key="i">{{ x }}</li>
          </ul>
        </div>

        <div v-if="data.tips && data.tips.length" class="hl-block">
          <div class="hl-title">💡 出行贴士</div>
          <ul class="hl-list">
            <li v-for="(x, i) in data.tips" :key="i">{{ x }}</li>
          </ul>
        </div>

        <div class="hl-block">
          <div class="hl-title">📋 可发送全文（一键复制发给客户）</div>
          <el-input
            :model-value="data.share_text"
            type="textarea"
            :rows="10"
            readonly
            style="margin-top:6px"
          />
        </div>
      </template>

      <el-empty v-else-if="!loading && !routeId" description="请选择一条线路以生成亮点介绍" />
      <el-empty v-else-if="!loading" description="暂无内容，请重试" />
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">关闭</el-button>
      <el-button
        v-if="effectiveRouteId"
        type="primary"
        :loading="loading"
        @click="generate"
      >重新生成</el-button>
      <el-button
        v-if="data && data.share_text"
        type="success"
        @click="copyText"
      >复制全文</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // 预设线路（线路页直接传）；客户页不传则组件内提供线路选择器
  routeId: { type: [Number, String], default: null },
  customerId: { type: [Number, String], default: null },
  customerName: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const loadingRoutes = ref(false)
const data = ref(null)
const routeOptions = ref([])
const pickedRouteId = ref(null)

const effectiveRouteId = computed(() => props.routeId || pickedRouteId.value)

watch(() => props.modelValue, (v) => {
  if (v) {
    data.value = null
    if (props.routeId) {
      pickedRouteId.value = props.routeId
      generate()
    } else {
      pickedRouteId.value = null
      loadRoutes()
    }
  }
})

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

function onPickRoute() {
  data.value = null
  if (pickedRouteId.value) generate()
}

async function generate() {
  const rid = effectiveRouteId.value
  if (!rid) return
  loading.value = true
  try {
    // 带客户个性化时不写回线路缓存（缓存只存通用版，供小程序读取），避免覆盖通用版
    const payload = { route_id: Number(rid), save: !props.customerId }
    if (props.customerId) payload.customer_id = Number(props.customerId)
    data.value = await api.aiRouteHighlight(payload)
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

async function copyText() {
  const t = data.value?.share_text || ''
  if (!t) return
  try {
    await navigator.clipboard.writeText(t)
    ElMessage.success('已复制全文，可直接发给客户')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = t
    document.body.appendChild(ta)
    ta.select()
    try { document.execCommand('copy') } catch { /* ignore */ }
    document.body.removeChild(ta)
    ElMessage.success('已复制全文')
  }
}
</script>

<style scoped>
.hl-block { margin-bottom: 14px; }
.hl-title { font-weight: 600; font-size: 14px; color: #0E9F6E; margin-bottom: 6px; }
.hl-text { font-size: 13px; color: #303133; line-height: 1.7; }
.hl-list { margin: 0; padding-left: 18px; }
.hl-list li { font-size: 13px; color: #303133; line-height: 1.8; }
</style>
