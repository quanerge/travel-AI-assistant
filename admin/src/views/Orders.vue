<template>
  <el-card class="page-card">
    <div style="display:flex;gap:12px;margin-bottom:12px">
      <el-input v-model="kw" placeholder="姓名/手机号" clearable style="width:220px" @keyup.enter="search" />
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
import { ElMessage } from 'element-plus'
import { api } from '../api'
import OrderDetail from './OrderDetail.vue'
import { maskPhone } from '../utils/mask'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const kw = ref('')
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
  success: ['success', '报名成功'],
  completed: ['info', '完成']
}
const statusType = (s) => (statusMap[s] ? statusMap[s][0] : 'info')
const statusText = (s) => (statusMap[s] ? statusMap[s][1] : s)

const load = async () => {
  loading.value = true
  try {
    const res = await api.listOrders({ page: page.value, pageSize: pageSize.value })
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

function onPage(p) {
  page.value = p
  load()
}

const openDetail = (row) => {
  detailId.value = row.id
  detailVisible.value = true
}

onMounted(load)
</script>

<style scoped>
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
