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
      <el-tooltip content="开启后显示已软删除（隐藏）的客户，可在表格中恢复。" placement="top">
        <span class="switch-item">
          <span class="switch-label">显示已删除</span>
          <el-switch v-model="includeDeleted" style="margin-left: 8px" @change="search" />
        </span>
      </el-tooltip>
      <el-tooltip content="开启后仅显示已标记为重点（★）的客户，方便聚焦高价值客户、优先跟进。" placement="top">
        <span class="switch-item">
          <span class="switch-label">仅看重点</span>
          <el-switch v-model="keyOnly" style="margin-left: 8px" @change="search" />
        </span>
      </el-tooltip>
      <el-tooltip content="开启后按客户所在小区聚合展示，同一小区归为一组（按人数从多到少排序），便于社区化运营。" placement="top">
        <span class="switch-item">
          <span class="switch-label">按小区分组</span>
          <el-switch v-model="groupMode" style="margin-left: 8px" />
        </span>
      </el-tooltip>
    </div>

    <el-table v-if="!groupMode" :data="rows" v-loading="loading" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="重点" width="64" align="center">
        <template #default="{ row }">
          <el-tooltip content="重点星标：点击 ★/☆ 切换该客户是否为「重点客户」，便于优先跟进与筛选。" placement="top">
            <span style="cursor:pointer;font-size:18px;color:#f7ba2a" @click="toggleKey(row)">{{ row.is_key ? '★' : '☆' }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
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
      <el-table-column prop="community" label="小区" width="120" />
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
          <el-button v-if="!row.is_deleted" link type="danger" @click="del(row)">删除</el-button>
          <el-button v-else link type="warning" @click="restore(row)">恢复</el-button>
        </template>
      </el-table-column>
    </el-table>

    <template v-if="groupMode">
      <div class="group-hint">
        按小区分组视图：同一小区的客户归为一组（按人数从多到少排列）。点击星标可切换重点客户；如需只看重点客户，可同时开启「仅看重点」。
      </div>
      <el-empty v-if="!rows.length" description="暂无客户" />
      <div v-for="g in groupedCustomers" :key="g.name" class="community-group">
        <div class="group-title">
          <span class="group-name">{{ g.name || '未填写小区' }}</span>
          <span class="group-count">{{ g.items.length }} 人</span>
        </div>
        <el-table :data="g.items" border size="small">
          <el-table-column prop="name" label="客户" width="110" />
          <el-table-column label="手机" width="170">
            <template #default="{ row }">
              <span>{{ revealed[row.id] ? row.phone : maskPhone(row.phone) }}</span>
              <el-button link type="primary" size="small" @click="toggleReveal(row.id)">{{ revealed[row.id] ? '隐藏' : '显示' }}</el-button>
            </template>
          </el-table-column>
          <el-table-column label="重点" width="60" align="center">
            <template #default="{ row }"><el-tooltip content="重点星标：点击 ★/☆ 切换该客户是否为「重点客户」，便于优先跟进与筛选。" placement="top"><span style="cursor:pointer;color:#f7ba2a;font-size:16px" @click="toggleKey(row)">{{ row.is_key ? '★' : '☆' }}</span></el-tooltip></template>
          </el-table-column>
          <el-table-column prop="community" label="小区" width="120" />
          <el-table-column prop="follow_status" label="状态" width="100">
            <template #default="{ row }"><el-tag :type="statusType(row.follow_status)" size="small">{{ statusLabel(row.follow_status) }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link type="success" @click="openFollow(row)">跟进</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

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
        <el-form-item label="小区">
          <el-input v-model="form.community" placeholder="填写客户所在小区，用于按小区分组" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
const includeDeleted = ref(false)
const keyOnly = ref(false)
const groupMode = ref(false)

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
    community: '', follow_status: 'pending_follow'
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
    if (includeDeleted.value) params.include_deleted = true
    if (keyOnly.value) params.is_key = true
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

// 按小区分组（前端聚合）：同一小区的客户归为一组，便于社区化运营
const groupedCustomers = computed(() => {
  const map = {}
  for (const c of rows.value) {
    const key = c.community || ''
    if (!map[key]) map[key] = { name: key, items: [] }
    map[key].items.push(c)
  }
  return Object.values(map).sort((a, b) => b.items.length - a.items.length)
})

async function toggleKey(row) {
  try {
    const updated = await api.toggleKeyCustomer(row.id)
    row.is_key = updated.is_key
    ElMessage.success(updated.is_key ? '已标记为重点客户' : '已取消重点')
  } catch {
    ElMessage.error('操作失败')
  }
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
  const isEdit = !!editingId.value
  try {
    if (isEdit) {
      await api.updateCustomer(editingId.value, form.value)
      ElMessage.success('已保存')
    } else {
      const created = await api.createCustomer(form.value)
      ElMessage.success('已新增')
      // 乐观更新：把新客户直接插到列表最前，避开分页/筛选导致的“看不见”
      rows.value = [created, ...rows.value]
      total.value = (total.value || 0) + 1
      page.value = 1
    }
  } catch (e) {
    // 暴露真实错误原因，便于定位（如 422 校验失败 / 500 服务异常 / 网络错误）
    const detail = e?.response?.data?.detail
    ElMessage.error('保存失败：' + (typeof detail === 'string' ? detail : (e?.message || '请查看控制台/服务端日志')))
    return
  }
  dialogVisible.value = false
  try {
    await load()
  } catch (e) {
    ElMessage.warning('数据已保存成功，但列表刷新失败，请手动刷新页面')
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

async function del(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除客户「${row.name}」？删除后仅隐藏，关联订单/需求单/跟进均保留，可在「显示已删除」中恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await api.deleteCustomer(row.id)
    ElMessage.success('已删除')
    load()
  } catch {
    ElMessage.error('删除失败')
  }
}
async function restore(row) {
  try {
    await api.restoreCustomer(row.id)
    ElMessage.success('已恢复')
    load()
  } catch {
    ElMessage.error('恢复失败')
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.switch-item {
  display: inline-flex;
  align-items: center;
}
.switch-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.group-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  padding: 10px 14px;
  background: #ecf5ff;
  border-left: 4px solid #409eff;
  border-radius: 4px;
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
}
.community-group {
  margin-bottom: 18px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
}
.group-title {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background: #f5f7fa;
  font-weight: 600;
}
.group-count {
  color: #909399;
  font-weight: 400;
  font-size: 12px;
}
</style>
