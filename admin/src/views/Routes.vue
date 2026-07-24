<template>
  <el-card class="page-card">
    <div style="display:flex;gap:12px;margin-bottom:12px;align-items:center">
      <el-input v-model="kw" placeholder="线路名/目的地" clearable style="width:220px" @keyup.enter="load" />
      <el-select v-model="cat" placeholder="分类" clearable style="width:140px" @change="load">
        <el-option v-for="c in cats" :key="c" :label="c" :value="c" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button type="success" @click="openCreate" style="margin-left:auto">+ 新增线路</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="线路名称" min-width="160" />
      <el-table-column prop="category" label="分类" width="100" />
      <el-table-column prop="destination" label="目的地" width="100" />
      <el-table-column prop="days" label="天数" width="70" />
      <el-table-column prop="price" label="单价(元)" width="100" />
      <el-table-column prop="signup_count" label="报名数" width="80" />
      <el-table-column prop="cost_price" label="成本价(元)" width="100">
        <template #default="{ row }">{{ row.cost_price != null ? row.cost_price : '—' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '上架' : '下架' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button size="small" @click="openDetail(row)">行程</el-button>
          <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" :type="row.status === 'active' ? 'warning' : 'success'" @click="toggleStatus(row)">
            {{ row.status === 'active' ? '下架' : '上架' }}
          </el-button>
          <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 行程查看弹窗 -->
    <el-dialog v-model="detailVisible" title="行程安排" width="640px">
      <template v-if="detail">
        <h3>{{ detail.name }}（{{ detail.days }}天）</h3>
        <el-timeline>
          <el-timeline-item
            v-for="d in detail.route_days"
            :key="d.id"
            :timestamp="`第${d.day_no}天 · ${d.title}`"
          >
            <div>内容：{{ d.content || '—' }}</div>
            <div style="color:#888">餐饮：{{ d.meals || '—' }} ｜ 住宿：{{ d.accommodation || '—' }} ｜ 交通：{{ d.traffic || '—' }}</div>
          </el-timeline-item>
        </el-timeline>
      </template>
    </el-dialog>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="formVisible" :title="isEdit ? '编辑线路' : '新增线路'" width="780px" @closed="resetForm">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="线路名称" required><el-input v-model="form.name" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类">
              <el-select v-model="form.category" style="width:100%">
                <el-option v-for="c in cats" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="出发地"><el-input v-model="form.departure" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="目的地"><el-input v-model="form.destination" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="天数" required><el-input-number v-model="form.days" :min="1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="价格(元)" required><el-input-number v-model="form.price" :min="0" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="成本价(元)"><el-input-number v-model="form.cost_price" :min="0" :step="100" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="评分"><el-input-number v-model="form.rating" :min="0" :max="5" :step="0.1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="成团人数"><el-input-number v-model="form.group_size" :min="1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="上架 active" value="active" />
                <el-option label="下架 inactive" value="inactive" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="封面图">
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
            <el-upload
              action="/api/upload/cover"
              name="file"
              :show-file-list="false"
              accept="image/*"
              :before-upload="beforeCover"
              :on-success="onCoverOk"
              :on-error="onCoverErr"
            >
              <el-button type="primary" :loading="uploading">上传本地图片</el-button>
            </el-upload>
            <img v-if="form.cover" :src="coverPreview" style="width:120px;height:80px;object-fit:cover;border-radius:6px;border:1px solid #ebeef5" />
            <el-button v-if="form.cover" link type="danger" @click="form.cover=''">清除</el-button>
          </div>
          <el-input v-model="form.cover" style="margin-top:8px" placeholder="也可直接粘贴图片 URL（http(s) 或 /static/...）；留空则小程序用按目的地兜底图" />
        </el-form-item>
        <el-form-item label="行程亮点"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="费用包含"><el-input v-model="form.fee_included" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="费用不含"><el-input v-model="form.fee_excluded" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="注意事项"><el-input v-model="form.notice" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="图集(多图)">
          <el-input v-model="form.galleryText" type="textarea" :rows="2" placeholder="每行一个图片 URL，或用逗号分隔；展示在线路详情页" />
          <div v-if="galleryList.length" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">
            <img v-for="(u, i) in galleryList" :key="i" :src="u" style="width:80px;height:54px;object-fit:cover;border-radius:6px;border:1px solid #ebeef5" />
          </div>
        </el-form-item>

        <el-divider>每日行程</el-divider>
        <div
          v-for="(d, i) in form.route_days"
          :key="i"
          style="border:1px solid #ebeef5;border-radius:8px;padding:12px;margin-bottom:12px"
        >
          <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
            <span>第 <el-input-number v-model="d.day_no" :min="1" controls-position="right" style="width:120px" /></span>
            <el-input v-model="d.title" placeholder="标题，如：抵达昆明" style="flex:1" />
            <el-button type="danger" link @click="form.route_days.splice(i, 1)">删除</el-button>
          </div>
          <el-input v-model="d.content" type="textarea" :rows="2" placeholder="当日内容" style="margin-bottom:6px" />
          <el-row :gutter="8">
            <el-col :span="8"><el-input v-model="d.meals" placeholder="餐饮" /></el-col>
            <el-col :span="8"><el-input v-model="d.accommodation" placeholder="住宿" /></el-col>
            <el-col :span="8"><el-input v-model="d.traffic" placeholder="交通" /></el-col>
          </el-row>
        </div>
        <el-button @click="addDay">+ 添加一天</el-button>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const loading = ref(false)
const rows = ref([])
const kw = ref('')
const cat = ref('')
const cats = ['国内游', '短途游', '出境游', '周边游', '主题游']
const detailVisible = ref(false)
const detail = ref(null)

const formVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const uploading = ref(false)
const editingId = ref(null)
const form = reactive(emptyForm())

// 上传成功后的预览：相对 /static/... 在 dev 下由 vite 代理到后端；绝对 URL 直连
const coverPreview = computed(() => {
  const c = form.cover || ''
  if (c.startsWith('http')) return c
  return c // 以 / 开头的相对路径，浏览器会基于当前 origin（dev 下经代理）解析
})

// 图集：多 URL 文本 <-> 数组
const galleryList = computed(() => form.galleryText
  ? form.galleryText.split(/[\n,]/).map(s => s.trim()).filter(Boolean)
  : [])

const beforeCover = (file) => {
  const okType = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(file.type)
  if (!okType) { ElMessage.error('仅支持 jpg/png/webp/gif'); return false }
  if (file.size > 5 * 1024 * 1024) { ElMessage.error('图片不能超过 5MB'); return false }
  uploading.value = true
  return true
}
const onCoverOk = (res) => {
  uploading.value = false
  form.cover = res.url
  ElMessage.success('封面上传成功')
}
const onCoverErr = () => {
  uploading.value = false
  ElMessage.error('封面上传失败')
}

function emptyForm() {
  return {
    name: '', category: '国内游', departure: '', destination: '',
    days: 1, price: 0, cost_price: 0, rating: 5.0, group_size: 20, status: 'active',
    cover: '', description: '', fee_included: '', fee_excluded: '', notice: '',
    galleryText: '', route_days: []
  }
}
function resetForm() { Object.assign(form, emptyForm()) }

const load = async () => {
  loading.value = true
  try {
    rows.value = await api.listRoutes({ keyword: kw.value || undefined, category: cat.value || undefined })
  } finally { loading.value = false }
}

const openDetail = async (row) => {
  detail.value = await api.getRoute(row.id)
  detailVisible.value = true
}

const openCreate = () => {
  isEdit.value = false
  editingId.value = null
  resetForm()
  formVisible.value = true
}

const openEdit = async (row) => {
  const r = await api.getRoute(row.id)
  isEdit.value = true
  editingId.value = r.id
  Object.assign(form, {
    name: r.name, category: r.category, departure: r.departure, destination: r.destination,
    days: r.days, price: r.price, cost_price: r.cost_price || 0, rating: r.rating, group_size: r.group_size, status: r.status,
    cover: r.cover || '', description: r.description || '', fee_included: r.fee_included || '',
    fee_excluded: r.fee_excluded || '', notice: r.notice || '',
    galleryText: (r.gallery || []).join('\n'),
    route_days: (r.route_days || []).map(d => ({
      day_no: d.day_no, title: d.title, content: d.content || '',
      meals: d.meals || '', accommodation: d.accommodation || '', traffic: d.traffic || ''
    }))
  })
  formVisible.value = true
}

const addDay = () => {
  form.route_days.push({
    day_no: form.route_days.length + 1, title: '', content: '', meals: '', accommodation: '', traffic: ''
  })
}

const save = async () => {
  if (!form.name) { ElMessage.warning('请填写线路名称'); return }
  if (!form.days || form.days < 1) { ElMessage.warning('请填写有效天数'); return }
  if (form.price == null) { ElMessage.warning('请填写价格'); return }
  saving.value = true
  try {
    const gallery = form.galleryText
      ? form.galleryText.split(/[\n,]/).map(s => s.trim()).filter(Boolean)
      : []
    const payload = {
      ...form,
      cost_price: form.cost_price || 0,
      gallery,
      route_days: form.route_days.map(d => ({ ...d }))
    }
    delete payload.galleryText
    if (isEdit.value) {
      await api.updateRoute(editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await api.createRoute(payload)
      ElMessage.success('已新增')
    }
    formVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally { saving.value = false }
}

const toggleStatus = async (row) => {
  const next = row.status === 'active' ? 'inactive' : 'active'
  try {
    await api.updateRoute(row.id, { status: next })
    ElMessage.success(next === 'active' ? '已上架' : '已下架')
    await load()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  }
}

const remove = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除线路「${row.name}」？该操作不可恢复。`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await api.deleteRoute(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

onMounted(load)
</script>
