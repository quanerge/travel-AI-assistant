<template>
  <el-card class="page-card">
    <div style="display:flex;gap:12px;margin-bottom:12px;align-items:center">
      <el-button type="success" @click="openCreate" style="margin-left:auto">+ 新增 Banner</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="预览" width="160">
        <template #default="{ row }">
          <img v-if="row.image" :src="row.image" style="width:140px;height:70px;object-fit:cover;border-radius:6px" />
          <span v-else style="color:#999">无图</span>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="文案" min-width="140" />
      <el-table-column label="跳转线路" width="160">
        <template #default="{ row }">{{ routeName(row.route_id) }}</template>
      </el-table-column>
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-switch
            v-model="row.status"
            active-value="active"
            inactive-value="inactive"
            @change="(v) => toggleStatus(row, v)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" class-name="op-col">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="formVisible" :title="isEdit ? '编辑 Banner' : '新增 Banner'" width="600px" @closed="resetForm">
      <el-form :model="form" label-width="90px">
        <el-form-item label="图片 URL" required>
          <el-input v-model="form.image" placeholder="https://... 或 /static/..." />
          <img v-if="form.image" :src="form.image" style="width:100%;height:120px;object-fit:cover;border-radius:6px;margin-top:8px" />
        </el-form-item>
        <el-form-item label="文案">
          <el-input v-model="form.title" placeholder="轮播文案，如：云南8日深度游" />
        </el-form-item>
        <el-form-item label="跳转线路">
          <el-select v-model="form.route_id" clearable placeholder="不跳转" style="width:100%">
            <el-option v-for="r in routes" :key="r.id" :label="`${r.id} · ${r.name}`" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="排序">
              <el-input-number v-model="form.sort" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="启用" value="active" />
                <el-option label="停用" value="inactive" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
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
const routes = ref([])
const routeMap = ref({})
const formVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const editingId = ref(null)
const form = reactive(emptyForm())

function emptyForm() {
  return { image: '', title: '', route_id: null, sort: 0, status: 'active' }
}
function resetForm() { Object.assign(form, emptyForm()) }
const routeName = (id) => (id && routeMap.value[id]) ? routeMap.value[id] : (id ? `线路#${id}` : '不跳转')

const load = async () => {
  loading.value = true
  try {
    const [bs, rs] = await Promise.all([api.listBannersAdmin(), api.listRoutes()])
    rows.value = bs.rows
    routes.value = rs.rows
    routeMap.value = {}
    rs.rows.forEach(r => { routeMap.value[r.id] = r.name })
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
  Object.assign(form, {
    image: row.image || '', title: row.title || '',
    route_id: row.route_id || null, sort: row.sort || 0, status: row.status || 'active'
  })
  formVisible.value = true
}

const save = async () => {
  if (!form.image) { ElMessage.warning('请填写图片 URL'); return }
  saving.value = true
  try {
    const payload = { ...form }
    if (isEdit.value) {
      await api.updateBanner(editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await api.createBanner(payload)
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
    await api.updateBanner(row.id, { status: v })
    ElMessage.success(v === 'active' ? '已启用' : '已停用')
  } catch (e) {
    row.status = v === 'active' ? 'inactive' : 'active' // 回滚
    ElMessage.error('操作失败')
  }
}

const remove = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除 Banner「${row.title || row.id}」？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await api.deleteBanner(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

onMounted(load)
</script>
