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
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const loading = ref(false)
const rows = ref([])

onMounted(load)

async function load() {
  loading.value = true
  try {
    rows.value = await api.listConsults()
  } finally {
    loading.value = false
  }
}
</script>
