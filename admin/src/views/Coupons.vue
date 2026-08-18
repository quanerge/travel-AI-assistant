<template>
  <el-card class="page-card">
    <div style="display:flex;gap:12px;margin-bottom:12px;align-items:center">
      <el-button type="success" @click="openCreate" style="margin-left:auto">+ 新增优惠券</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="title" label="名称" min-width="140" />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">{{ row.user_id ? '已发放' : '模板' }}</template>
      </el-table-column>
      <el-table-column label="面额" width="90">
        <template #default="{ row }">¥{{ row.amount }}</template>
      </el-table-column>
      <el-table-column prop="condition" label="使用门槛" min-width="120" />
      <el-table-column label="适用范围" min-width="120">
        <template #default="{ row }">{{ applicableText(row.applicable) }}</template>
      </el-table-column>
      <el-table-column label="有效期至" min-width="150">
        <template #default="{ row }">{{ row.expire_at ? String(row.expire_at).replace('T', ' ').slice(0, 16) : '长期' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-switch
            v-if="!row.user_id"
            v-model="row.status"
            active-value="active"
            inactive-value="inactive"
            @change="(v) => toggleStatus(row, v)"
          />
          <span v-else style="color:#999">—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" class-name="op-col">
        <template #default="{ row }">
          <el-button size="small" type="primary" :disabled="!!row.user_id" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="formVisible" :title="isEdit ? '编辑优惠券' : '新增优惠券'" width="600px" @closed="resetForm">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.title" placeholder="如：新客立减 200" />
        </el-form-item>
        <el-form-item label="面额(元)" required>
          <el-input-number v-model="form.amount" :min="0" :step="10" style="width:100%" />
        </el-form-item>
        <el-form-item label="使用门槛">
          <el-input v-model="form.condition" placeholder="如：满3000可用，留空为无门槛" />
        </el-form-item>
        <el-form-item label="适用范围">
          <el-select v-model="form.applicableType" style="width:100%" @change="onApplicableChange">
            <el-option label="全场通用" value="all" />
            <el-option label="指定线路" value="route" />
            <el-option label="指定分类" value="category" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.applicableType !== 'all'" label="适用参数">
          <el-input v-model="form.applicableParam" :placeholder="form.applicableType === 'route' ? '线路ID，如 1' : '分类名，如 国内游'" />
        </el-form-item>
        <el-form-item label="有效期至">
          <el-date-picker v-model="form.expire_at" type="datetime" placeholder="不选则为长期" style="width:100%" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width:100%">
            <el-option label="启用(可领取)" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
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
const formVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const editingId = ref(null)
const form = reactive(emptyForm())

function emptyForm() {
  return {
    title: '', amount: 0, condition: '',
    applicableType: 'all', applicableParam: '',
    applicable: 'all',
    expire_at: null, status: 'active'
  }
}
function resetForm() { Object.assign(form, emptyForm()) }
function applicableText(a) {
  if (!a || a === 'all') return '全场通用'
  if (a.indexOf('route:') === 0) return '指定线路#' + a.split(':')[1]
  if (a.indexOf('category:') === 0) return '分类:' + a.split(':')[1]
  return a
}
function onApplicableChange() {
  form.applicableParam = ''
  syncApplicable()
}
function syncApplicable() {
  if (form.applicableType === 'all') form.applicable = 'all'
  else form.applicable = form.applicableType + ':' + (form.applicableParam || '')
}

const load = async () => {
  loading.value = true
  try {
    const res = await api.listCoupons()
    rows.value = res.rows
  } catch (e) {
    ElMessage.error('加载失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  isEdit.value = false
  editingId.value = null
  resetForm()
  formVisible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  editingId.value = row.id
  const at = !row.applicable || row.applicable === 'all' ? 'all' : row.applicable.split(':')[0]
  const param = (!row.applicable || row.applicable === 'all') ? '' : row.applicable.split(':').slice(1).join(':')
  Object.assign(form, {
    title: row.title || '',
    amount: row.amount || 0,
    condition: row.condition || '',
    applicableType: at,
    applicableParam: param,
    applicable: row.applicable || 'all',
    expire_at: row.expire_at ? String(row.expire_at).replace(' ', 'T').slice(0, 19) : null,
    status: row.status || 'active'
  })
  formVisible.value = true
}

const save = async () => {
  if (!form.title) { ElMessage.warning('请填写名称'); return }
  if (!form.amount || form.amount <= 0) { ElMessage.warning('请填写有效面额'); return }
  syncApplicable()
  if (form.applicableType !== 'all' && !form.applicableParam) {
    ElMessage.warning('请填写适用参数'); return
  }
  saving.value = true
  const payload = {
    title: form.title,
    amount: form.amount,
    condition: form.condition || null,
    applicable: form.applicable,
    expire_at: form.expire_at || null,
    status: form.status
  }
  try {
    if (isEdit.value) {
      await api.updateCoupon(editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await api.createCoupon(payload)
      ElMessage.success('已新增')
    }
    formVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

const toggleStatus = async (row, v) => {
  try {
    await api.updateCoupon(row.id, { status: v })
    ElMessage.success(v === 'active' ? '已启用' : '已停用')
  } catch (e) {
    row.status = v === 'active' ? 'inactive' : 'active'
    ElMessage.error('操作失败')
  }
}

const remove = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除优惠券「${row.title || row.id}」？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await api.deleteCoupon(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

onMounted(load)
</script>
