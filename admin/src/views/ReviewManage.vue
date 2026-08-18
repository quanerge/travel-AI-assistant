<template>
  <el-card class="page-card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <span style="font-weight:600">线路评价管理</span>
      <el-button @click="load">刷新</el-button>
    </div>

    <!-- 筛选 -->
    <div class="filters">
      <el-input v-model.number="filters.routeId" placeholder="线路 ID" style="width:120px"
        clearable @keyup.enter="load" />
      <el-select v-model="filters.rating" placeholder="星级" style="width:120px" clearable>
        <el-option label="5 星" :value="5" />
        <el-option label="4 星" :value="4" />
        <el-option label="3 星" :value="3" />
        <el-option label="2 星" :value="2" />
        <el-option label="1 星" :value="1" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" style="width:120px" clearable>
        <el-option label="全部" value="" />
        <el-option label="公开" value="approved" />
        <el-option label="已下架" value="hidden" />
        <el-option label="已删除" value="deleted" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="id" label="ID" width="64" />
      <el-table-column prop="nickname" label="评价人" width="110" />
      <el-table-column prop="route_name" label="线路" min-width="160" show-overflow-tooltip />
      <el-table-column label="星级" width="150">
        <template #default="{ row }">
          <el-rate :model-value="row.rating" disabled />
        </template>
      </el-table-column>
      <el-table-column prop="content" label="评价内容" min-width="220" show-overflow-tooltip />
      <el-table-column label="晒图" width="100" align="center">
        <template #default="{ row }">
          <span v-if="!row.images || !row.images.length" style="color:#bbb">无</span>
          <el-image
            v-else
            style="width:46px;height:46px;border-radius:6px"
            :src="row.images[0]"
            :preview-src-list="row.images"
            :initial-index="0"
            fit="cover"
            hide-on-click-modal
          />
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="提交时间" min-width="170" />
      <el-table-column label="操作" width="190" fixed="right" class-name="op-col">
        <template #default="{ row }">
          <el-button v-if="row.status === 'approved'" size="small" type="warning"
            @click="changeStatus(row, 'hidden')">下架</el-button>
          <el-button v-if="row.status === 'hidden'" size="small" type="success"
            @click="changeStatus(row, 'approved')">恢复公开</el-button>
          <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
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

const filters = reactive({ routeId: null, rating: null, status: '' })

const statusText = (s) => ({ approved: '公开', hidden: '已下架', deleted: '已删除' }[s] || s)
const statusType = (s) => ({ approved: 'success', hidden: 'warning', deleted: 'info' }[s] || 'info')

function resetFilters() {
  filters.routeId = null
  filters.rating = null
  filters.status = ''
  page.value = 1
  load()
}

onMounted(load)

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, pageSize: pageSize.value }
    if (filters.routeId) params.route_id = filters.routeId
    if (filters.rating) params.rating = filters.rating
    if (filters.status) params.status = filters.status
    const res = await api.listReviewsAdmin(params)
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

async function changeStatus(row, status) {
  const action = status === 'hidden' ? '下架' : (status === 'approved' ? '恢复公开' : '删除')
  try {
    await api.updateReviewStatus(row.id, status)
    ElMessage.success(`已${action}`)
    load()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  }
}

function remove(row) {
  ElMessageBox.confirm(
    `确认删除评价 #${row.id}（${row.nickname || '匿名'} / ${row.route_name}）？删除后全站不可见（软删，数据可追溯）。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  ).then(() => changeStatus(row, 'deleted'))
    .catch((e) => {
      if (e !== 'cancel' && e !== 'close') {
        ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
      }
    })
}
</script>

<style scoped>
.filters { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
