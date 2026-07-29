<template>
  <el-card class="page-card">
    <div style="display:flex;gap:12px;margin-bottom:12px;align-items:center">
      <span style="color:#888;font-size:13px">仅超级管理员可管理账号</span>
      <el-button type="primary" @click="openCreate" style="margin-left:auto">+ 新增账号</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" min-width="120" />
      <el-table-column label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'super' ? 'danger' : 'info'" size="small">
            {{ row.role === 'super' ? '超级管理员' : '顾问' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="手机" width="140" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-switch
            v-model="row.status"
            active-value="active"
            inactive-value="disabled"
            :disabled="row.id === currentId"
            @change="(v) => toggleStatus(row, v)"
          />
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ fmt(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openReset(row)">重置密码</el-button>
          <el-button link type="success" :disabled="row.id === currentId" @click="openRole(row)">改角色</el-button>
          <el-button link type="danger" :disabled="row.id === currentId" @click="remove(row)">删除</el-button>
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

    <!-- 新增账号 -->
    <el-dialog v-model="createVisible" title="新增账号" width="480px" @closed="resetForm">
      <el-form :model="form" label-width="90px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" placeholder="登录账号" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="form.password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width:100%">
            <el-option label="顾问（受限）" value="advisor" />
            <el-option label="超级管理员" value="super" />
          </el-select>
        </el-form-item>
        <el-form-item label="手机">
          <el-input v-model="form.phone" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog v-model="resetVisible" title="重置密码" width="420px">
      <el-form label-width="80px">
        <el-form-item label="账号">
          <span>{{ resetTarget?.username }}</span>
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="newPassword" placeholder="至少 6 位" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doReset">确认重置</el-button>
      </template>
    </el-dialog>

    <!-- 改角色 -->
    <el-dialog v-model="roleVisible" title="变更角色" width="420px">
      <el-form label-width="80px">
        <el-form-item label="账号">
          <span>{{ roleTarget?.username }}</span>
        </el-form-item>
        <el-form-item label="新角色">
          <el-select v-model="newRole" style="width:100%">
            <el-option label="顾问（受限）" value="advisor" />
            <el-option label="超级管理员" value="super" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doRole">确认变更</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const saving = ref(false)
const currentId = JSON.parse(localStorage.getItem('admin') || '{}').id

const createVisible = ref(false)
const form = reactive({ username: '', password: '', role: 'advisor', phone: '' })
function resetForm() { Object.assign(form, { username: '', password: '', role: 'advisor', phone: '' }) }

const resetVisible = ref(false)
const resetTarget = ref(null)
const newPassword = ref('')

const roleVisible = ref(false)
const roleTarget = ref(null)
const newRole = ref('advisor')

function fmt(t) {
  if (!t) return '-'
  return String(t).replace('T', ' ').slice(0, 19)
}

const load = async () => {
  loading.value = true
  try {
    const res = await api.listUsers({ page: page.value, pageSize: pageSize.value })
    rows.value = res.rows
    total.value = res.total
  } catch (e) {
    ElMessage.error('加载失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function onPage(p) {
  page.value = p
  load()
}

const openCreate = () => { resetForm(); createVisible.value = true }
const create = async () => {
  if (!form.username || !form.password) { ElMessage.warning('请填写用户名和密码'); return }
  saving.value = true
  try {
    await api.createUser({ ...form })
    ElMessage.success('已创建')
    createVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error('创建失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

const openReset = (row) => { resetTarget.value = row; newPassword.value = ''; resetVisible.value = true }
const doReset = async () => {
  if (!newPassword.value || newPassword.value.length < 6) { ElMessage.warning('密码至少 6 位'); return }
  saving.value = true
  try {
    await api.resetUserPassword(resetTarget.value.id, newPassword.value)
    ElMessage.success('密码已重置')
    resetVisible.value = false
  } catch (e) {
    ElMessage.error('重置失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

const openRole = (row) => { roleTarget.value = row; newRole.value = row.role; roleVisible.value = true }
const doRole = async () => {
  saving.value = true
  try {
    await api.updateUserRole(roleTarget.value.id, newRole.value)
    ElMessage.success('角色已变更')
    roleVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error('变更失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

const toggleStatus = async (row, v) => {
  try {
    await api.updateUserStatus(row.id, v)
    ElMessage.success(v === 'active' ? '已启用' : '已停用')
  } catch (e) {
    row.status = v === 'active' ? 'disabled' : 'active'
    ElMessage.error('操作失败')
  }
}

const remove = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除账号「${row.username}」？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await api.deleteUser(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
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
