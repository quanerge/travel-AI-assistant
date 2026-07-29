<template>
  <el-card class="page-card">
    <div style="display:flex;justify-content:space-between;margin-bottom:12px">
      <span style="font-weight:600">智能需求单 / 咨询记录</span>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="channel" label="渠道" width="100" />
      <el-table-column prop="content" label="需求内容" min-width="260" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'pending' ? 'warning' : 'success'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="提交时间" min-width="180" />
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
import { ref, onMounted } from 'vue'
import { api } from '../api'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await api.listConsults({ page: page.value, pageSize: pageSize.value })
    rows.value = res.rows
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function onPage(p) {
  page.value = p
  load()
}
</script>

<style scoped>
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
