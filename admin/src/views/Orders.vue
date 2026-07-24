<template>
  <el-card class="page-card">
    <div style="display:flex;gap:12px;margin-bottom:12px">
      <el-input v-model="kw" placeholder="姓名/手机号" clearable style="width:220px" @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="order_no" label="订单号" width="160" />
      <el-table-column prop="name" label="客户" width="100" />
      <el-table-column prop="phone" label="手机" width="140" />
      <el-table-column prop="person_count" label="人数" width="70" />
      <el-table-column prop="departure_date" label="出发日" width="120" />
      <el-table-column prop="total_amount" label="总额(元)" width="100" />
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="openDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <OrderDetail v-model="detailVisible" :order-id="detailId" @updated="load" />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import OrderDetail from './OrderDetail.vue'

const loading = ref(false)
const rows = ref([])
const kw = ref('')
const detailVisible = ref(false)
const detailId = ref(null)

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

const load = async () => {
  loading.value = true
  try {
    let list = await api.listOrders()
    if (kw.value) {
      const k = kw.value.trim()
      list = list.filter((o) => o.name.includes(k) || (o.phone || '').includes(k))
    }
    rows.value = list
  } finally {
    loading.value = false
  }
}

const openDetail = (row) => {
  detailId.value = row.id
  detailVisible.value = true
}

onMounted(load)
</script>
