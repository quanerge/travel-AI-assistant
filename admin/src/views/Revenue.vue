<template>
  <div v-loading="loading">
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card class="page-card stat-card">
          <div class="stat-label">累计收益(元)</div>
          <div class="stat-num">{{ money(summary.totalIncome) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="page-card stat-card">
          <div class="stat-label">累计利润(元)</div>
          <div class="stat-num" :style="{ color: summary.totalProfit >= 0 ? '#19be6b' : '#f56c6c' }">{{ money(summary.totalProfit) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="page-card stat-card">
          <div class="stat-label">已收定金(元)</div>
          <div class="stat-num">{{ money(summary.depositIncome) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="page-card stat-card">
          <div class="stat-label">已付款订单</div>
          <div class="stat-num">{{ summary.paidCount }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="page-card" style="margin-top:16px">
      <div style="font-weight:600;margin-bottom:12px">订单收益明细</div>
      <el-table :data="rows" border>
        <el-table-column prop="order_no" label="订单号" width="160" />
        <el-table-column prop="name" label="客户" width="100" />
        <el-table-column prop="person_count" label="人数" width="70" />
        <el-table-column label="应收(元)" width="110">
          <template #default="{ row }">{{ money(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column label="成本(元)" width="110">
          <template #default="{ row }">{{ money(row.cost) }}</template>
        </el-table-column>
        <el-table-column label="利润(元)" width="110">
          <template #default="{ row }">
            <span :style="{ color: row.profit >= 0 ? '#19be6b' : '#f56c6c', fontWeight: 600 }">{{ money(row.profit) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.deposit_paid ? 'success' : 'warning'">
              {{ row.deposit_paid ? '定金已收' : '待收定金' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const loading = ref(false)
const rows = ref([])
const summary = ref({ totalIncome: 0, totalProfit: 0, depositIncome: 0, paidCount: 0 })
const money = (v) => (v == null ? '0.00' : Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))

onMounted(async () => {
  loading.value = true
  try {
    const [orders, routes] = await Promise.all([api.listOrders(), api.listRoutes()])
    const routeMap = {}
    routes.forEach(r => { routeMap[r.id] = r })
    let totalIncome = 0, totalProfit = 0, depositIncome = 0, paidCount = 0
    rows.value = orders.map(o => {
      const r = o.route_id ? routeMap[o.route_id] : null
      const revenue = o.total_amount != null ? o.total_amount : (r ? r.price * o.person_count : 0)
      const cost = r && r.cost_price ? r.cost_price * o.person_count : 0
      const profit = revenue - cost
      if (o.deposit_paid) { depositIncome += revenue; paidCount++ }
      totalIncome += revenue
      totalProfit += profit
      return { ...o, cost, profit }
    })
    summary.value = {
      totalIncome: round2(totalIncome),
      totalProfit: round2(totalProfit),
      depositIncome: round2(depositIncome),
      paidCount
    }
  } finally {
    loading.value = false
  }
})

const round2 = (v) => Math.round(v * 100) / 100
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-label { color: #888; font-size: 13px; }
.stat-num { font-size: 28px; font-weight: 700; margin-top: 6px; color: #2b7fff; }
</style>
