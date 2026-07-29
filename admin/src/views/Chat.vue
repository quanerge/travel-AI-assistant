<template>
  <div class="chat-page">
    <!-- 左侧会话列表 -->
    <div class="chat-side">
      <div class="side-head">
        <span class="side-title">客服会话</span>
        <el-input v-model="kw" size="small" placeholder="搜索昵称/手机" clearable class="side-search" />
      </div>
      <div class="session-list">
        <div
          v-for="s in filteredSessions"
          :key="s.openid"
          class="session"
          :class="{ active: s.openid === activeOpenid }"
          @click="openSession(s)"
        >
          <div class="avatar">{{ (s.nickname || '微').slice(0, 1) }}</div>
          <div class="session-main">
            <div class="session-top">
              <span class="name">{{ s.nickname || ('微信用户 ' + s.openid.slice(-4)) }}</span>
              <span class="time">{{ fmt(s.last_at) }}</span>
            </div>
            <div class="session-bottom">
              <span class="last">{{ s.last_content || '（无消息）' }}</span>
              <span v-if="s.unread" class="badge">{{ s.unread }}</span>
            </div>
            <div v-if="s.phone" class="phone">手机：{{ s.phone }}</div>
          </div>
        </div>
        <div v-if="!filteredSessions.length" class="empty">暂无会话</div>
      </div>
    </div>

    <!-- 右侧消息区 -->
    <div class="chat-main">
      <template v-if="activeOpenid">
        <div class="chat-head">{{ activeName }}</div>
        <div class="msg-list" ref="msgBox">
          <div v-for="m in messages" :key="m.id" class="msg-row" :class="m.direction">
            <div class="bubble">{{ m.content }}</div>
            <div class="msg-time">{{ fmt(m.created_at) }}</div>
          </div>
        </div>
        <div class="reply-box">
          <el-input
            v-model="draft"
            type="textarea"
            :rows="3"
            placeholder="输入回复内容，回车发送（Shift+Enter 换行）"
            @keydown.enter.exact.prevent="send"
          />
          <el-button type="primary" :disabled="!draft.trim()" @click="send">发送</el-button>
        </div>
      </template>
      <div v-else class="chat-empty">请选择左侧会话</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import { ElMessage } from 'element-plus'

const sessions = ref([])
const activeOpenid = ref('')
const messages = ref([])
const draft = ref('')
const kw = ref('')
const msgBox = ref(null)
let timer = null

const filteredSessions = computed(() => {
  const k = kw.value.trim()
  if (!k) return sessions.value
  return sessions.value.filter(
    (s) => (s.nickname || '').includes(k) || (s.phone || '').includes(k)
  )
})

const activeName = computed(() => {
  const s = sessions.value.find((x) => x.openid === activeOpenid.value)
  if (!s) return ''
  return s.nickname || '微信用户 ' + s.openid.slice(-4)
})

function fmt(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const p = (n) => (n < 10 ? '0' : '') + n
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function loadSessions() {
  try {
    const data = await api.chatSessions()
    sessions.value = data || []
  } catch (e) {
    // 鉴权失败等：静默保留旧列表
  }
}

async function openSession(s) {
  activeOpenid.value = s.openid
  try {
    messages.value = await api.chatMessages(s.openid)
  } catch (e) {
    messages.value = []
  }
  try {
    await api.chatRead(s.openid)
  } catch (e) {
    // 忽略标记已读失败
  }
  const item = sessions.value.find((x) => x.openid === s.openid)
  if (item) item.unread = 0
  scrollBottom()
}

function scrollBottom() {
  nextTick(() => {
    if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
  })
}

async function send() {
  const content = draft.value.trim()
  if (!content || !activeOpenid.value) return
  try {
    await api.chatReply(activeOpenid.value, content)
    messages.value.push({
      id: Date.now(),
      direction: 'out',
      content,
      created_at: new Date().toISOString(),
    })
    draft.value = ''
    const item = sessions.value.find((x) => x.openid === activeOpenid.value)
    if (item) {
      item.last_content = content
      item.last_at = new Date().toISOString()
    }
    scrollBottom()
  } catch (e) {
    ElMessage.error('发送失败，请重试')
  }
}

// 轻量轮询：每 12s 刷新会话列表与当前会话消息（保留草稿与当前选中）
async function onPoll() {
  await loadSessions()
  if (activeOpenid.value) {
    try {
      messages.value = await api.chatMessages(activeOpenid.value)
    } catch (e) {
      // 忽略
    }
    const it = sessions.value.find((x) => x.openid === activeOpenid.value)
    if (it) it.unread = 0
    scrollBottom()
  }
}

onMounted(() => {
  loadSessions()
  timer = setInterval(onPoll, 12000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.chat-page {
  display: flex;
  height: 100%;
  background: #f5f7fa;
  overflow: hidden;
}
.chat-side {
  width: 300px;
  flex: 0 0 300px;
  border-right: 1px solid #e8eaed;
  background: #fff;
  display: flex;
  flex-direction: column;
}
.side-head {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}
.side-title {
  font-weight: 600;
  font-size: 15px;
  display: block;
  margin-bottom: 8px;
}
.side-search {
  width: 100%;
}
.session-list {
  flex: 1;
  overflow-y: auto;
}
.session {
  display: flex;
  padding: 12px;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
}
.session:hover {
  background: #fafafa;
}
.session.active {
  background: #eef5ff;
}
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #1677ff;
  color: #fff;
  text-align: center;
  line-height: 40px;
  font-size: 16px;
  flex: 0 0 40px;
  margin-right: 10px;
}
.session-main {
  flex: 1;
  min-width: 0;
}
.session-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.name {
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.time {
  font-size: 12px;
  color: #999;
  flex: 0 0 auto;
  margin-left: 8px;
}
.session-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}
.last {
  color: #888;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.badge {
  background: #f5222d;
  color: #fff;
  border-radius: 10px;
  font-size: 12px;
  padding: 0 6px;
  margin-left: 8px;
  flex: 0 0 auto;
}
.phone {
  font-size: 12px;
  color: #aaa;
  margin-top: 2px;
}
.empty {
  text-align: center;
  color: #bbb;
  padding: 40px 0;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-head {
  padding: 14px 20px;
  background: #fff;
  border-bottom: 1px solid #e8eaed;
  font-weight: 600;
}
.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.msg-row {
  display: flex;
  flex-direction: column;
  max-width: 70%;
}
.msg-row.in {
  align-self: flex-start;
  align-items: flex-start;
}
.msg-row.out {
  align-self: flex-end;
  align-items: flex-end;
}
.bubble {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}
.msg-row.in .bubble {
  background: #fff;
  border: 1px solid #e8eaed;
}
.msg-row.out .bubble {
  background: #1677ff;
  color: #fff;
}
.msg-time {
  font-size: 11px;
  color: #bbb;
  margin-top: 4px;
}
.reply-box {
  border-top: 1px solid #e8eaed;
  background: #fff;
  padding: 12px 16px;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.reply-box .el-textarea {
  flex: 1;
}
.chat-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #bbb;
}
</style>
