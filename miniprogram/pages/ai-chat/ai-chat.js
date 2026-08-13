// pages/ai-chat/ai-chat.js
const api = require('../../utils/api')
const md = require('../../utils/markdown')

Page({
  data: {
    messages: [],        // { role: 'user'|'assistant', content }
    conversations: [],   // 会话列表（含 id/title�?
    currentId: null,     // 当前会话 id（null = 新对话）
    draft: '',
    loading: false,
    scrollAnchor: ''
  },

  onLoad() {
    this.loadConversations()
  },

  // 拉取会话列表，若有历史则自动进入最近一�?
  loadConversations() {
    api.aiConversations().then(list => {
      const conversations = list || []
      this.setData({ conversations })
      if (conversations.length && this.data.currentId == null) {
        this.selectConv({ currentTarget: { dataset: { id: conversations[0].id } } })
      }
    }).catch(() => {})
  },

  // 选中历史会话 �? 回放消息
  selectConv(e) {
    const id = Number(e.currentTarget.dataset.id)
    this.setData({ currentId: id, messages: [], loading: true })
    api.aiHistory(id).then(list => {
      const messages = (list || []).map(m => {
        const o = { role: m.role, content: m.content }
        if (m.role === 'assistant') o.blocks = md.parseBlocks(m.content)
        return o
      })
      this.setData({ messages, loading: false })
      this.scrollBottom(messages.length)
    }).catch(() => {
      this.setData({ messages: [], loading: false })
    })
  },

  // 开新对话：清空当前会话与消�?
  newConv() {
    this.setData({ currentId: null, messages: [], draft: '' })
  },

  onInput(e) {
    this.setData({ draft: e.detail.value })
  },

  send() {
    const text = (this.data.draft || '').trim()
    if (!text || this.data.loading) return

    const sendingId = this.data.currentId
    const userMsg = { role: 'user', content: text }
    const messages = this.data.messages.concat(userMsg)
    this.setData({ messages, draft: '', loading: true })
    this.scrollBottom(messages.length)

    api.aiChat({ message: text, conversation_id: sendingId })
      .then(res => {
        const replyContent = res.reply || ''
        const reply = { role: 'assistant', content: replyContent, blocks: md.parseBlocks(replyContent) }
        const next = this.data.messages.concat(reply)
        this.setData({
          messages: next,
          loading: false,
          currentId: res.conversation_id || sendingId
        })
        this.scrollBottom(next.length)
        // 刷新会话列表（标�?/排序可能变化�?
        this.loadConversations()
      })
      .catch(err => {
        this.setData({ loading: false })
        const detail = (err && err.detail) ? String(err.detail) : (err && err.message) ? err.message : 'AI 回复失败'
        console.error('[AI chat] 失败�?', err)
        wx.showToast({
          title: detail.slice(0, 40),
          icon: 'none'
        })
      })
  },

  // 滚动到底部：用最后一条消息的 id 作为锚点
  scrollBottom(len) {
    if (len > 0) {
      this.setData({ scrollAnchor: 'm' + (len - 1) })
    }
  }
})
