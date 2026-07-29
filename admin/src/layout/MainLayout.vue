<template>
  <el-container style="height:100%">
    <el-aside width="200px" style="background:#001529">
      <div style="color:#fff;font-size:18px;font-weight:700;padding:18px 16px;">旅途管家</div>
      <div style="color:#7a8ba5;font-size:12px;padding:0 16px 14px;letter-spacing:1px;">管理后台 {{ appVersion }}</div>
      <el-menu
        background-color="#001529"
        text-color="#fff"
        active-text-color="#1677ff"
        :default-active="activeMenu"
        router
      >
        <el-menu-item index="/dashboard"><el-icon><DataLine /></el-icon>数据看板</el-menu-item>
        <el-menu-item index="/routes"><el-icon><MapLocation /></el-icon>线路管理</el-menu-item>
        <el-menu-item index="/orders"><el-icon><Tickets /></el-icon>订单管理</el-menu-item>
        <el-menu-item index="/customers"><el-icon><User /></el-icon>客户 CRM</el-menu-item>
        <el-menu-item index="/revenue"><el-icon><Money /></el-icon>收益管理</el-menu-item>
        <el-menu-item index="/banners"><el-icon><Picture /></el-icon>Banner 管理</el-menu-item>
        <el-menu-item index="/consults"><el-icon><ChatDotRound /></el-icon>智能需求单</el-menu-item>
        <el-menu-item index="/chat"><el-icon><ChatLineRound /></el-icon>客服消息</el-menu-item>
        <el-menu-item v-if="isSuper" index="/users"><el-icon><UserFilled /></el-icon>用户管理</el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon>系统设置</el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header style="background:#fff;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #eee">
        <span style="font-weight:600">{{ currentTitle }}</span>
        <el-dropdown @command="onCommand">
          <span style="cursor:pointer">{{ admin?.username || '管理员' }} ▾</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth } from '../store/auth'
import { api } from '../api'
import {
  DataLine, MapLocation, Tickets, User, Money, ChatDotRound, Picture,
  UserFilled, Setting, ChatLineRound
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const admin = auth.get()
// 版本号由后端 /version 接口返回；拉取前/失败时使用兜底值，避免界面空白
const appVersion = ref('V1.3')
const isSuper = computed(() => admin?.role === 'super')
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '')
const onCommand = (c) => {
  if (c === 'logout') {
    auth.clear()
    router.push('/login')
  }
}

onMounted(async () => {
  try {
    const res = await api.getVersion()
    if (res && res.version) appVersion.value = res.version
  } catch (e) {
    // 保留兜底版本号，不影响其它功能
  }
})
</script>
