<template>
  <div v-loading="loading">
    <!-- 生日 / 纪念日关怀提醒 -->
    <el-alert
      v-if="birthdayReminders.length"
      class="birthday-alert"
      :closable="false"
      type="warning"
      show-icon
    >
      <template #title>
        <span class="ba-title">🎂 生日关怀提醒（{{ birthdayReminders.length }} 位客户）</span>
      </template>
      <div class="ba-list">
        <span
          v-for="b in birthdayReminders"
          :key="b.customer_id"
          class="ba-chip"
          @click="goCustomers"
        >
          <b>{{ b.name }}</b>
          <span class="ba-when" :class="b.offset === 0 ? 'is-today' : ''">
            {{ b.offset === 0 ? '今天生日' : '明天生日' }}
          </span>
          <span class="ba-date">{{ b.birthday }}</span>
        </span>
      </div>
      <div class="ba-tip">点击客户可前往「客户管理」发送生日祝福或专属优惠</div>
    </el-alert>

    <!-- 指标卡 -->
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card class="page-card stat-card">
          <div class="stat-label">今日订单</div>
          <div class="stat-num">{{ d.today_orders }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="page-card stat-card">
          <div class="stat-label">本月收入(元)</div>
          <div class="stat-num">{{ money(d.month_income) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="page-card stat-card">
          <div class="stat-label">累计利润(元)</div>
          <div class="stat-num" :style="{ color: d.profit >= 0 ? '#19be6b' : '#f56c6c' }">{{ money(d.profit) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="page-card stat-card">
          <div class="stat-label">近7天新增客户</div>
          <div class="stat-num">{{ d.customer_growth }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <!-- 待办 -->
      <el-col :span="10">
        <el-card class="page-card" style="height:100%">
          <div style="font-weight:600;margin-bottom:12px">待办事项</div>
          <div class="todo-row" @click="goOrders">
            <span>待确认订单</span>
            <span class="todo-num warn">{{ d.pending_confirm_orders }}</span>
          </div>
          <div class="todo-row" @click="goOrders">
            <span>待收定金订单</span>
            <span class="todo-num warn">{{ d.pending_deposit_orders }}</span>
          </div>
          <div class="todo-row">
            <span>当前在售线路</span>
            <span class="todo-num">{{ d.active_routes }}</span>
          </div>
        </el-card>
      </el-col>

      <!-- TOP5 热门线路 -->
      <el-col :span="14">
        <el-card class="page-card" style="height:100%">
          <div style="font-weight:600;margin-bottom:12px">热门线路 TOP5（按报名数）</div>
          <div v-if="top.length" class="bar-chart">
            <div class="bar-row" v-for="t in top" :key="t.id">
              <div class="bar-name" :title="t.name">{{ t.name }}</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: barPct(t.signup_count) + '%' }"></div>
              </div>
              <div class="bar-val">{{ t.signup_count }} 人</div>
            </div>
          </div>
          <el-empty v-else description="暂无线路" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 近30天订单趋势 -->
    <el-card class="page-card" style="margin-top:16px">
      <div style="font-weight:600;margin-bottom:12px">近 30 天订单趋势</div>
      <div v-if="trend.length" class="trend">
        <div class="trend-col" v-for="(p, i) in trend" :key="i">
          <div class="trend-bar" :style="{ height: (p.count / trendMax * 120) + 'px' }"></div>
          <div class="trend-x">{{ p.md }}</div>
        </div>
      </div>
      <el-empty v-else description="暂无订单" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const loading = ref(true)
const d = ref({
  today_orders: 0, month_income: 0, profit: 0, customer_growth: 0,
  active_routes: 0, pending_confirm_orders: 0, pending_deposit_orders: 0,
  top_routes: [], order_trend: [], birthday_reminders: []
})

const birthdayReminders = computed(() => d.value.birthday_reminders || [])

const money = (v) => (v == null ? '0.00' : Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
const top = computed(() => d.value.top_routes || [])
const maxSignup = computed(() => Math.max(1, ...top.value.map(t => t.signup_count || 0)))
const barPct = (v) => Math.round((v / maxSignup.value) * 100)

// 近30天：以 order_trend 为准，前端补零成连续序列
const trend = computed(() => {
  const raw = {}
  ;(d.value.order_trend || []).forEach(p => { raw[p.date] = p.count })
  const arr = []
  const today = new Date()
  for (let i = 29; i >= 0; i--) {
    const dt = new Date(today)
    dt.setDate(today.getDate() - i)
    const iso = dt.toISOString().slice(0, 10)
    arr.push({ date: iso, md: (dt.getMonth() + 1) + '/' + dt.getDate(), count: raw[iso] || 0 })
  }
  return arr
})
const trendMax = computed(() => Math.max(1, ...trend.value.map(p => p.count)))

const goOrders = () => router.push('/orders')
// 点击生日关怀提醒：带 care=birthday 跳转到客户管理，由 CRM 页高亮今天/明天生日的客户
const goCustomers = () => router.push({ path: '/customers', query: { care: 'birthday' } })

onMounted(async () => {
  try {
    d.value = await api.dashboard()
  } catch (e) {
    // 401 由拦截器统一处理跳转
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-label { color: #888; font-size: 13px; }
.stat-num { font-size: 30px; font-weight: 700; margin-top: 6px; color: #2b7fff; }
.birthday-alert { margin-bottom: 16px; }
.ba-title { font-weight: 700; }
.ba-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
.ba-chip {
  display: inline-flex; align-items: center; gap: 6px;
  background: #fff7e6; border: 1px solid #ffd591; border-radius: 16px;
  padding: 4px 12px; font-size: 13px; cursor: pointer; transition: .2s;
}
.ba-chip:hover { background: #ffe7ba; }
.ba-when { color: #fa8c16; font-weight: 600; }
.ba-when.is-today { color: #f5222d; }
.ba-date { color: #999; }
.ba-tip { color: #999; font-size: 12px; margin-top: 8px; }
.todo-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 0; border-bottom: 1px solid #f2f2f2; cursor: pointer;
}
.todo-row:last-child { border-bottom: none; }
.todo-num { font-size: 20px; font-weight: 700; }
.todo-num.warn { color: #ff8a3d; }
.bar-chart { display: flex; flex-direction: column; gap: 10px; }
.bar-row { display: flex; align-items: center; gap: 10px; font-size: 13px; }
.bar-name { width: 110px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bar-track { flex: 1; background: #f2f5fa; border-radius: 6px; height: 14px; overflow: hidden; }
.bar-fill { height: 100%; background: linear-gradient(90deg, #2b7fff, #5aa0ff); border-radius: 6px; transition: width .4s; }
.bar-val { width: 56px; text-align: right; color: #666; }
.trend { display: flex; align-items: flex-end; gap: 4px; height: 150px; overflow-x: auto; }
.trend-col { flex: 1; min-width: 14px; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; }
.trend-bar { width: 10px; background: #2b7fff; border-radius: 3px 3px 0 0; min-height: 2px; }
.trend-x { font-size: 10px; color: #aaa; margin-top: 4px; transform: rotate(-45deg); white-space: nowrap; }
</style>
