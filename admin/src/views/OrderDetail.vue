<template>
  <el-dialog :model-value="modelValue" title="订单详情" width="640px" @update:model-value="$emit('update:modelValue', $event)" @open="load">
    <div v-loading="loading">
      <template v-if="o">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="订单号">{{ o.order_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(o.status)">{{ statusText(o.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="客户">{{ o.name }}</el-descriptions-item>
          <el-descriptions-item label="手机">
            <span>{{ showPhone ? o.phone : maskPhone(o.phone) }}</span>
            <el-button link type="primary" size="small" @click="showPhone = !showPhone">
              {{ showPhone ? '隐藏' : '显示' }}
            </el-button>
          </el-descriptions-item>
          <el-descriptions-item label="人数">{{ o.person_count }}</el-descriptions-item>
          <el-descriptions-item label="出发日">{{ o.departure_date || '—' }}</el-descriptions-item>
          <el-descriptions-item label="总额(元)">{{ o.total_amount != null ? o.total_amount : '—' }}</el-descriptions-item>
          <el-descriptions-item label="定金">{{ o.deposit_paid ? '已收' : '未收' }}</el-descriptions-item>
          <el-descriptions-item label="下单时间" :span="2">{{ fmtTime(o.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ o.remark || '—' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
      <el-button
        v-if="o && o.status === 'pending_confirm'"
        type="primary" :loading="acting" @click="act('confirm')"
      >确认订单</el-button>
      <el-button
        v-if="o && (o.status === 'pending_confirm' || o.status === 'pending_deposit')"
        type="warning" :loading="acting" @click="act('deposit')"
      >确认定金</el-button>
      <el-button
        v-if="o && (o.status === 'confirmed' || o.status === 'deposit_received')"
        type="success" :loading="acting" @click="act('complete')"
      >完成</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { maskPhone } from '../utils/mask'

const props = defineProps({ modelValue: Boolean, orderId: Number })
const emit = defineEmits(['update:modelValue', 'updated'])

const loading = ref(false)
const acting = ref(false)
const o = ref(null)
const showPhone = ref(false)

const statusMap = {
  pending_confirm: ['warning', '待确认'],
  confirmed: ['', '已确认'],
  pending_deposit: ['warning', '待付定金'],
  deposit_received: ['success', '定金已收'],
  success: ['success', '报名成功'],
  completed: ['info', '完成']
}
const statusType = (s) => (statusMap[s] ? statusMap[s][0] : 'info')
const statusText = (s) => (statusMap[s] ? statusMap[s][1] : s)
const fmtTime = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '—')

watch(() => props.modelValue, (v) => { if (v && props.orderId) load() })

const load = async () => {
  loading.value = true
  showPhone.value = false
  try {
    o.value = await api.getOrder(props.orderId)
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const act = async (type) => {
  acting.value = true
  try {
    if (type === 'confirm') await api.confirmOrder(props.orderId)
    else if (type === 'deposit') await api.confirmDeposit(props.orderId)
    else if (type === 'complete') await api.completeOrder(props.orderId)
    ElMessage.success('操作成功')
    emit('updated')
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  } finally {
    acting.value = false
  }
}
</script>
