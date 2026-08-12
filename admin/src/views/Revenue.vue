<template>
  <div v-loading="loading">
    <!-- 筛选条 -->
    <el-card class="page-card" style="margin-bottom:16px">
      <div style="display:flex;flex-wrap:wrap;gap:12px;align-items:center">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          @change="load"
        />
        <el-button @click="resetRange">全部</el-button>
        <span style="color:#999;font-size:13px">按下单时间统计（不选则累计全部）</span>
        <el-button type="primary" plain style="margin-left:auto" @click="exportCsv">导出 CSV</el-button>
      </div>
    </el-card>

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
          <div class="stat-label">已收定金订单</div>
          <div class="stat-num">{{ summary.depositPaidOrders }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="page-card" style="margin-top:16px">
      <div style="font-weight:600;margin-bottom:12px">订单收益明细</div>
      <el-table :data="rows" border @row-click="openDetail" style="cursor:pointer">
        <el-table-column prop="order_no" label="订单号" width="160" />
        <el-table-column prop="name" label="客户" width="100" />
        <el-table-column prop="route_name" label="线路" min-width="140">
          <template #default="{ row }">{{ row.route_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="person_count" label="人数" width="70" />
        <el-table-column label="应收(元)" width="110">
          <template #default="{ row }">{{ money(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column label="优惠(元)" width="100">
          <template #default="{ row }">
            <span v-if="row.discount_amount > 0" style="color:#f56c6c">-{{ money(row.discount_amount) }}</span>
            <span v-else>0.00</span>
          </template>
        </el-table-column>
        <el-table-column label="成本(元)" width="110">
          <template #default="{ row }">
            <span v-if="row.cost_unset" style="color:#aaa">未设成本</span>
            <span v-else>{{ money(row.cost) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="利润(元)" width="110">
          <template #default="{ row }">
            <span :style="{ color: row.profit >= 0 ? '#19be6b' : '#f56c6c', fontWeight: 600 }">{{ money(row.profit) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status] ? statusMap[row.status].type : 'info'">
              {{ statusMap[row.status] ? statusMap[row.status].label : row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="下单时间" min-width="160">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <div v-if="!rows.length" style="text-align:center;color:#999;padding:24px">暂无订单收益数据</div>
    </el-card>

    <!-- 订单详情下钻 -->
    <OrderDetail v-model="detailVisible" :order-id="detailId" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import OrderDetail from './OrderDetail.vue'

const loading = ref(false)
const rows = ref([])
const dateRange = ref([])
const detailVisible = ref(false)
const detailId = ref(null)

const summary = ref({ totalIncome: 0, totalProfit: 0, depositIncome: 0, depositPaidOrders: 0 })

const statusMap = {
  pending_confirm: { label: '待确认', type: 'warning' },
  confirmed: { label: '已确认', type: '' },
  pending_deposit: { label: '待付定金', type: 'warning' },
  deposit_received: { label: '定金已收', type: 'success' },
  success: { label: '报名成功', type: 'success' },
  completed: { label: '已完成', type: 'success' },
}

const money = (v) => (v == null ? '0.00' : Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
const fmtTime = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '—')
const round2 = (v) => Math.round(v * 100) / 100

const load = async () => {
  loading.value = true
  try {
    const params = {}
    if (dateRange.value && dateRange.value.length === 2) {
      params.start = dateRange.value[0]
      params.end = dateRange.value[1]
    }
    const data = await api.getRevenue(params)
    rows.value = data.details || []
    summary.value = {
      totalIncome: data.total_income || 0,
      totalProfit: data.total_profit || 0,
      depositIncome: data.deposit_income || 0,
      depositPaidOrders: data.deposit_paid_orders || 0,
    }
  } catch (e) {
    // 401 由拦截器统一处理跳转
  } finally {
    loading.value = false
  }
}

const resetRange = () => {
  dateRange.value = []
  load()
}

const openDetail = (row) => {
  detailId.value = row.id
  detailVisible.value = true
}

const exportCsv = () => {
  if (!rows.value.length) return
  const headers = ['订单号', '客户', '线路', '人数', '应收(元)', '优惠(元)', '成本(元)', '利润(元)', '状态', '下单时间']
  const statusText = (s) => (statusMap[s] ? statusMap[s].label : s)
  const lines = [headers.join(',')]
  rows.value.forEach((r) => {
    const cost = r.cost_unset ? '未设成本' : r.cost
    const cells = [r.order_no, r.name, r.route_name || '', r.person_count, r.total_amount,
      r.discount_amount, cost, r.profit, statusText(r.status), fmtTime(r.created_at)]
    lines.push(cells.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))
  })
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '收益明细.csv'
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-label { color: #888; font-size: 13px; }
.stat-num { font-size: 28px; font-weight: 700; margin-top: 6px; color: #2b7fff; }
</style>
