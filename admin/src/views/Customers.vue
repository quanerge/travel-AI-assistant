<template>
  <el-card class="page-card">
    <div class="toolbar">
      <el-input
        v-model="tagFilter"
        placeholder="按标签筛选"
        clearable
        style="width: 180px"
        @keyup.enter="search"
        @clear="search"
      />
      <el-select
        v-model="statusFilter"
        placeholder="跟进状态"
        clearable
        style="width: 160px"
        @change="search"
      >
        <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-button type="primary" @click="openCreate">新增客户</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="客户" width="110" />
      <el-table-column prop="wechat_no" label="微信号" width="130" />
      <el-table-column label="手机" width="160">
        <template #default="{ row }">
          <span>{{ revealed[row.id] ? row.phone : maskPhone(row.phone) }}</span>
          <el-button link type="primary" size="small" @click="toggleReveal(row.id)">
            {{ revealed[row.id] ? '隐藏' : '显示' }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column prop="birthday" label="生日" width="90" />
      <el-table-column prop="source" label="来源" width="100" />
      <el-table-column prop="tags" label="标签" width="120" />
      <el-table-column prop="total_orders" label="订单数" width="80" />
      <el-table-column prop="total_amount" label="累计消费" width="110" />
      <el-table-column label="跟进状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.follow_status)" size="small">
            {{ statusLabel(row.follow_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
      <el-table-column label="最后联系" width="160">
        <template #default="{ row }">{{ fmt(row.last_contact_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="success" @click="openFollow(row)">跟进</el-button>
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

    <!-- 新增 / 编辑客户 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑客户' : '新增客户'"
      width="520px"
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="姓名" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="微信号">
          <el-input v-model="form.wechat_no" />
        </el-form-item>
        <el-form-item label="手机">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="来源">
          <el-input v-model="form.source" placeholder="如：在线留言 / 订单报名" />
        </el-form-item>
        <el-form-item label="旅行偏好">
          <el-input v-model="form.travel_preference" />
        </el-form-item>
        <el-form-item label="预算区间">
          <el-input v-model="form.budget_range" />
        </el-form-item>
        <el-form-item label="生日">
          <el-date-picker
            v-model="form.birthday"
            type="date"
            value-format="MM-DD"
            placeholder="选填，用于生日关怀提醒"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="逗号分隔，如：高净值,亲子" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="跟进状态">
          <el-select v-model="form.follow_status" style="width: 100%">
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 跟进记录 -->
    <el-dialog v-model="followVisible" title="跟进记录" width="520px">
      <el-timeline v-if="follows.length">
        <el-timeline-item
          v-for="f in follows"
          :key="f.id"
          :timestamp="fmt(f.created_at)"
          placement="top"
        >
          {{ f.content }}
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无跟进记录" />
      <el-input
        v-model="followText"
        type="textarea"
        :rows="2"
        placeholder="填写本次跟进内容"
      />
      <template #footer>
        <el-button @click="followVisible = false">关闭</el-button>
        <el-button type="primary" @click="addFollow">添加跟进</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { maskPhone } from '../utils/mask'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const tagFilter = ref('')
// 手机号脱敏：默认掩码，点击「显示」才暴露完整号码（授权管理员可见）
const revealed = reactive({})
function toggleReveal(id) {
  revealed[id] = !revealed[id]
}
const statusFilter = ref('')

const statusOptions = [
  { value: 'pending_follow', label: '待跟进' },
  { value: 'contacting', label: '跟进中' },
  { value: 'deal', label: '已成交' },
  { value: 'lost', label: '已流失' }
]

const dialogVisible = ref(false)
const editingId = ref(null)
const form = ref(blankForm())
function blankForm() {
  return {
    name: '', wechat_no: '', phone: '', source: '',
    travel_preference: '', budget_range: '', birthday: '', tags: '', remark: '',
    follow_status: 'pending_follow'
  }
}

const followVisible = ref(false)
const follows = ref([])
const followText = ref('')
const followCustomerId = ref(null)

function statusType(s) {
  return { pending_follow: 'info', contacting: 'warning', deal: 'success', lost: 'danger' }[s] || 'info'
}
function statusLabel(s) {
  return (statusOptions.find(o => o.value === s) || {}).label || s || '待跟进'
}
function fmt(t) {
  if (!t) return '-'
  return String(t).replace('T', ' ').slice(0, 19)
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, pageSize: pageSize.value }
    if (tagFilter.value) params.tag = tagFilter.value
    if (statusFilter.value) params.follow_status = statusFilter.value
    const res = await api.listCustomers(params)
    rows.value = res.rows
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// 切换筛选条件时回到第一页
function search() {
  page.value = 1
  load()
}

function onPage(p) {
  page.value = p
  load()
}

function openCreate() {
  editingId.value = null
  form.value = blankForm()
  dialogVisible.value = true
}
function openEdit(row) {
  editingId.value = row.id
  form.value = { ...blankForm(), ...row }
  dialogVisible.value = true
}
async function save() {
  if (!form.value.name) { ElMessage.warning('请填写姓名'); return }
  try {
    if (editingId.value) {
      await api.updateCustomer(editingId.value, form.value)
      ElMessage.success('已保存')
    } else {
      await api.createCustomer(form.value)
      ElMessage.success('已新增')
    }
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

async function openFollow(row) {
  followCustomerId.value = row.id
  followText.value = ''
  follows.value = await api.getFollowUps(row.id)
  followVisible.value = true
}
async function addFollow() {
  if (!followText.value.trim()) { ElMessage.warning('请填写跟进内容'); return }
  await api.addFollowUp(followCustomerId.value, followText.value.trim())
  ElMessage.success('已添加')
  followText.value = ''
  follows.value = await api.getFollowUps(followCustomerId.value)
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
