<template>
  <el-card class="page-card">
    <div style="display:flex;justify-content:space-between;margin-bottom:12px">
      <span style="font-weight:600">智能需求单 / 咨询记录</span>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="channel" label="渠道" width="100" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column label="手机" width="170">
        <template #default="{ row }">
          <span>{{ revealed[row.id] ? row.phone : maskPhone(row.phone) }}</span>
          <el-button link type="primary" size="small" @click="toggleReveal(row.id)">
            {{ revealed[row.id] ? '隐藏' : '显示' }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="线路" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">{{ row.route_name || '—' }}</template>
      </el-table-column>
      <el-table-column prop="content" label="需求内容" min-width="200" show-overflow-tooltip />
      <el-table-column label="顾问回复" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.reply_content || '—' }}</template>
      </el-table-column>
      <el-table-column label="附件" width="80" align="center">
        <template #default="{ row }">{{ row.attachments ? row.attachments.length : 0 }} 张</template>
      </el-table-column>
      <el-table-column label="行程" width="80" align="center">
        <template #default="{ row }">{{ row.itinerary ? row.itinerary.length : 0 }} 天</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="提交时间" min-width="180" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="openReply(row)">回复/生成方案</el-button>
          <el-button size="small" type="danger" @click="del(row)">删除</el-button>
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

    <el-dialog v-model="replyDialog" title="回复 / 生成方案" width="620px">
      <el-form :model="replyForm" label-width="90px">
        <el-form-item label="当前状态">
          <el-tag :type="statusType(replyForm.status)">{{ statusText(replyForm.status) }}</el-tag>
        </el-form-item>
        <el-form-item label="方案/回复">
          <el-input v-model="replyForm.reply_content" type="textarea" :rows="5"
            placeholder="填写给客户的方案说明、行程建议等" />
        </el-form-item>

        <!-- P3：行程卡片编辑 -->
        <el-form-item label="行程卡片">
          <div class="iti-edit-wrap">
            <div v-for="(it, idx) in replyForm.itinerary" :key="idx" class="iti-edit">
              <div class="iti-edit-row">
                <el-input v-model.number="replyForm.itinerary[idx].day" type="number" placeholder="天" style="width:90px" />
                <el-input v-model="replyForm.itinerary[idx].title" placeholder="标题，如：抵达大理" style="flex:1" />
                <el-button link type="danger" @click="removeIti(idx)">删除</el-button>
              </div>
              <el-input v-model="replyForm.itinerary[idx].desc" type="textarea" :rows="2"
                placeholder="当天安排说明" />
            </div>
            <el-button link type="primary" @click="addIti">+ 添加行程卡片</el-button>
          </div>
        </el-form-item>

        <!-- P3：方案附件上传 -->
        <el-form-item label="方案附件">
          <el-upload
            v-model:file-list="attachmentFiles"
            :action="uploadAction"
            :headers="uploadHeaders"
            list-type="picture-card"
            :on-success="onUploadSuccess"
            :on-remove="onUploadRemove"
            accept="image/*"
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
          <div class="tip">支持 jpg/png/webp/gif，单张 ≤5MB，客户可在「我的咨询」查看</div>
        </el-form-item>

        <el-form-item label="处理状态">
          <el-select v-model="replyForm.status" style="width:100%">
            <el-option label="待处理" value="pending" />
            <el-option label="方案已出（待客户确认）" value="replied" />
            <el-option label="已处理 / 已成交" value="done" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="replyDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveReply">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { api } from '../api'
import { maskPhone } from '../utils/mask'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
// 手机号脱敏：默认掩码，点击「显示」才暴露完整号码
const revealed = reactive({})
function toggleReveal(id) {
  revealed[id] = !revealed[id]
}
const statusText = (s) => (s === 'pending' ? '待处理' : (s === 'replied' ? '方案已出' : (s === 'done' ? '已处理' : s)))
const statusType = (s) => (s === 'pending' ? 'warning' : (s === 'replied' ? 'primary' : 'success'))

// 回复/生成方案对话框
const replyDialog = ref(false)
const saving = ref(false)
const replyForm = reactive({ id: null, reply_content: '', status: 'pending', attachments: [], itinerary: [] })
// 附件上传：el-upload 维护的预览列表（含 uid/url）
const attachmentFiles = ref([])
const uploadAction = '/api/upload/file'
const uploadHeaders = computed(() => {
  const admin = JSON.parse(localStorage.getItem('admin') || 'null')
  return admin && admin.token ? { Authorization: 'Bearer ' + admin.token } : {}
})
function onUploadSuccess(res) {
  if (res && res.url) replyForm.attachments.push(res.url)
}
function onUploadRemove(file) {
  const url = file.response ? file.response.url : file.url
  replyForm.attachments = replyForm.attachments.filter((u) => u !== url)
}
function addIti() {
  replyForm.itinerary.push({ day: replyForm.itinerary.length + 1, title: '', desc: '' })
}
function removeIti(idx) {
  replyForm.itinerary.splice(idx, 1)
}

function openReply(row) {
  replyForm.id = row.id
  replyForm.reply_content = row.reply_content || ''
  replyForm.status = row.status
  replyForm.attachments = row.attachments ? [...row.attachments] : []
  replyForm.itinerary = row.itinerary ? JSON.parse(JSON.stringify(row.itinerary)) : []
  // 回填附件预览列表
  attachmentFiles.value = (replyForm.attachments || []).map((u, i) => ({ uid: -i - 1, url: u, name: '附件' + (i + 1) }))
  replyDialog.value = true
}
async function saveReply() {
  if (!replyForm.reply_content) {
    ElMessage.warning('请填写方案/回复内容')
    return
  }
  saving.value = true
  try {
    await api.updateConsult(replyForm.id, {
      reply_content: replyForm.reply_content,
      status: replyForm.status,
      attachments: replyForm.attachments,
      itinerary: replyForm.itinerary,
    })
    ElMessage.success('已保存，客户将在「我的咨询」看到方案/行程/附件')
    replyDialog.value = false
    load()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

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

// 删除咨询/需求单（软删除：列表不再展示，但数据可追溯）
function del(row) {
  ElMessageBox.confirm(
    `确认删除需求单 #${row.id}（${row.name || '匿名'}）？删除后列表不再显示，但保留数据可追溯。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  ).then(() => api.deleteConsult(row.id))
    .then(() => {
      ElMessage.success('已删除')
      load()
    })
    .catch((e) => {
      if (e !== 'cancel' && e !== 'close') {
        ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
      }
    })
}
</script>

<style scoped>
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.iti-edit-wrap { width: 100%; }
.iti-edit { border: 1px solid #f0f0f0; border-radius: 8px; padding: 10px; margin-bottom: 10px; }
.iti-edit-row { display: flex; gap: 8rpx; align-items: center; margin-bottom: 8rpx; }
.tip { font-size: 12px; color: #9ca3af; margin-top: 6px; }
</style>
