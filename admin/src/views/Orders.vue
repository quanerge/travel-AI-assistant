<template>
  <el-card class="page-card">
    <div style="display:flex;gap:12px;margin-bottom:12px">
      <el-input v-model="kw" placeholder="姓名/手机号" clearable style="width:220px" @keyup.enter="search" />
      <el-select v-model="statusFilter" placeholder="全部状态" clearable style="width:150px" @change="onFilter">
        <el-option label="待确认" value="pending_confirm" />
        <el-option label="已确认" value="confirmed" />
        <el-option label="待付定金" value="pending_deposit" />
        <el-option label="定金已收" value="deposit_received" />
        <el-option label="待付尾款" value="balance_pending" />
        <el-option label="完成" value="completed" />
      </el-select>
      <el-button type="primary" @click="search">查询</el-button>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="order_no" label="订单号" width="160" />
      <el-table-column prop="name" label="客户" width="100" />
      <el-table-column label="线路" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">{{ row.route_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="手机" width="170">
        <template #default="{ row }">
          <span>{{ revealed[row.id] ? row.phone : maskPhone(row.phone) }}</span>
          <el-button link type="primary" size="small" @click="toggleReveal(row.id)">
            {{ revealed[row.id] ? '隐藏' : '显示' }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column prop="person_count" label="人数" width="70" />
      <el-table-column prop="departure_date" label="出发日" width="120" />
      <el-table-column prop="total_amount" label="总额(元)" width="100" />
      <el-table-column prop="balance_amount" label="应收尾款(元)" width="110">
        <template #default="{ row }">
          <span v-if="row.balance_amount > 0">
            {{ row.balance_amount }}
            <el-tag v-if="!row.balance_paid" type="warning" size="small" style="margin-left:4px">未收</el-tag>
            <el-tag v-else type="success" size="small" style="margin-left:4px">已收</el-tag>
          </span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" class-name="op-col">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="openDetail(row)">详情</el-button>
          <el-button size="small" type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPage"
      />
    </div>

    <OrderDetail v-model="detailVisible" :order-id="detailId" @updated="load" />
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import OrderDetail from './OrderDetail.vue'
import { maskPhone } from '../utils/mask'

const route = useRoute()
const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const kw = ref('')
const statusFilter = ref('')
const detailVisible = ref(false)
const detailId = ref(null)
// 手机号脱敏：默认掩码，点击「显示」才暴露完整号码
const revealed = reactive({})
function toggleReveal(id) {
  revealed[id] = !revealed[id]
}

const statusMap = {
  pending_confirm: ['warning', '待确认'],
  confirmed: ['', '已确认'],
  pending_deposit: ['warning', '待付定金'],
  deposit_received: ['success', '定金已收'],
  balance_pending: ['warning', '待付尾款'],
  success: ['success', '报名成功'],
  completed: ['info', '完成']
}
const statusType = (s) => (statusMap[s] ? statusMap[s][0] : 'info')
const statusText = (s) => (statusMap[s] ? statusMap[s][1] : s)

const load = async () => {
  loading.value = true
  try {
    const res = await api.listOrders({
      page: page.value, pageSize: pageSize.value,
      status: statusFilter.value || undefined
    })
    let list = res.rows
    if (kw.value) {
      const k = kw.value.trim()
      list = list.filter((o) => o.name.includes(k) || (o.phone || '').includes(k))
    }
    rows.value = list
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// 查询/刷新时回到第一页（关键词搜索在客户端按当前页结果过滤）
function search() {
  page.value = 1
  load()
}

// 切换状态筛选（看板「待付尾款」跳转会带上 ?status=balance_pending）
function onFilter() {
  page.value = 1
  load()
}

function onPage(p) {
  page.value = p
  load()
}

const openDetail = (row) => {
  detailId.value = row.id
  detailVisible.value = true
}

// 删除订单（软删除：列表不再展示，但保留审计与支付记录）
function del(row) {
  ElMessageBox.confirm(
    `确认删除订单 ${row.order_no}（${row.name || '匿名'}）？删除后列表不再显示，但保留数据可追溯。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  ).then(() => api.deleteOrder(row.id))
    .then(() => {
      ElMessage.success('已删除')
      load()
    })
    .catch((e) => {
      if (e !== 'cancel' && e !== 'close') {
        ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
      }
    })
}

onMounted(() => {
  // 支持从看板「待付尾款订单」带状态筛选进入
  if (route.query && route.query.status) {
    statusFilter.value = String(route.query.status)
  }
  load()
})
</script>

<style scoped>
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
