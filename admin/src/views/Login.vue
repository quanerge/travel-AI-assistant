<template>
  <div style="height:100%;display:flex;align-items:center;justify-content:center;background:#1677ff">
    <el-card style="width:360px">
      <h2 style="text-align:center;margin-top:0">旅途管家 · 管理后台</h2>
      <el-form :model="form" @submit.prevent="onSubmit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="管理员账号" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-button type="primary" style="width:100%" :loading="loading" @click="onSubmit">登录</el-button>
      </el-form>
      <p style="color:#999;font-size:12px;text-align:center;margin-bottom:0">
        演示账号：admin / admin123
      </p>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { auth } from '../store/auth'

const router = useRouter()
const form = ref({ username: 'admin', password: 'admin123' })
const loading = ref(false)

const onSubmit = async () => {
  loading.value = true
  try {
    const admin = await api.login(form.value.username, form.value.password)
    auth.set(admin)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    ElMessage.error('登录失败：账号或密码错误')
  } finally {
    loading.value = false
  }
}
</script>
