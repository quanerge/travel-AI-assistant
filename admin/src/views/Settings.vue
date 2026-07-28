<template>
  <el-card class="page-card">
    <el-tabs v-model="tab">
      <!-- 环境与安全 -->
      <el-tab-pane label="环境与安全" name="env">
        <div v-loading="loading">
          <el-descriptions title="运行环境" :column="2" border style="margin-bottom:20px">
            <el-descriptions-item label="系统版本">{{ info.version || '-' }}</el-descriptions-item>
            <el-descriptions-item label="数据库类型">{{ info.db_type || '-' }}</el-descriptions-item>
            <el-descriptions-item label="当前角色">{{ info.current_role === 'super' ? '超级管理员' : '顾问' }}</el-descriptions-item>
            <el-descriptions-item label="CORS 策略">{{ info.cors_policy || '-' }}</el-descriptions-item>
          </el-descriptions>

          <h4 style="margin:8px 0">安全配置状态</h4>
          <el-alert
            v-if="!info.jwt_secret_configured"
            type="warning" :closable="false" show-icon
            title="JWT 密钥使用默认值"
            description="当前 JWT_SECRET 为代码内置默认值，存在被伪造 token 的风险。生产环境务必通过环境变量设置强随机值。"
            style="margin-bottom:12px"
          />
          <el-alert
            v-if="!info.phone_key_configured"
            type="warning" :closable="false" show-icon
            title="手机号加密密钥使用默认值"
            description="当前 PHONE_ENCRYPT_KEY 为默认值。手机号以 enc: 前缀可逆加密存储，生产环境请设置独立强密钥（更换密钥将导致历史密文无法解密）。"
            style="margin-bottom:12px"
          />
          <el-table :data="secRows" border style="margin-top:8px">
            <el-table-column prop="item" label="配置项" width="220" />
            <el-table-column label="状态">
              <template #default="{ row }">
                <el-tag :type="row.ok ? 'success' : 'danger'" size="small">
                  {{ row.ok ? '已配置' : '需修改' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="note" label="说明" min-width="220" />
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 上线合规清单 -->
      <el-tab-pane label="上线合规清单" name="compliance">
        <el-alert type="info" :closable="false" show-icon
          title="以下为上线前需人工完成的合规/资质项（系统无法自动代劳）" style="margin-bottom:16px" />
        <el-table :data="checklist" border>
          <el-table-column prop="item" label="检查项" width="200" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.done ? 'success' : 'info'" size="small">
                {{ row.done ? '已具备' : '待完成' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="note" label="说明 / 操作路径" min-width="260" />
        </el-table>
      </el-tab-pane>

      <!-- 备份与运维 -->
      <el-tab-pane label="备份与运维" name="ops">
        <el-alert type="warning" :closable="false" show-icon
          title="数据备份提醒" style="margin-bottom:16px"
          description="当前使用 SQLite，数据库文件为项目根目录 lvguanjia.db。建议每日定时备份该文件；切换 MySQL 后请配置数据库自动备份。" />
        <ul class="ops-list">
          <li>修改密钥（JWT_SECRET / PHONE_ENCRYPT_KEY）后必须重启后端服务方能生效。</li>
          <li>PHONE_ENCRYPT_KEY 一旦变更，此前加密存储的手机号将无法解密，请在低峰期、备份后操作。</li>
          <li>管理员账号通过「用户管理」页维护；首个超管账号由 seed 脚本初始化（admin / admin123）。</li>
          <li>正式发布小程序需完成微信认证并配置 request 合法域名（HTTPS）。</li>
        </ul>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../api'

const tab = ref('env')
const loading = ref(false)
const info = reactive({
  version: '', db_type: '', current_role: '', cors_policy: '',
  jwt_secret_configured: false, phone_key_configured: false
})

const secRows = computed(() => [
  { item: 'JWT 密钥 (JWT_SECRET)', ok: !!info.jwt_secret_configured, note: '用于签发管理员/用户 token，生产须为强随机值' },
  { item: '手机号加密密钥 (PHONE_ENCRYPT_KEY)', ok: !!info.phone_key_configured, note: '用于手机号可逆加密存储，满足个保法要求' },
  { item: 'CORS 策略', ok: info.cors_policy !== '开放(*)', note: '生产建议限制为前端域名白名单' }
])

const checklist = [
  { item: '隐私政策 / 用户协议', done: false, note: '小程序须提供隐私政策链接，并在后台公示数据使用说明' },
  { item: 'ICP 备案 / 公安备案', done: false, note: '服务器域名需完成 ICP 备案' },
  { item: '微信小程序认证', done: false, note: '企业主体认证，否则无法开通支付与部分接口' },
  { item: '微信支付商户号', done: false, note: '开通微信支付需绑定商户号（当前定金为线下确认）' },
  { item: 'request 合法域名', done: false, note: '小程序后台配置 HTTPS 合法域名' }
]

const load = async () => {
  loading.value = true
  try {
    const s = await api.getSettings()
    Object.assign(info, s)
  } catch (e) {
    // 忽略，保留默认值
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.ops-list { padding-left: 20px; line-height: 2; color: #555; }
</style>
