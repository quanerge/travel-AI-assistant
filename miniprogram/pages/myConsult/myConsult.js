// pages/myConsult/myConsult.js
const api = require('../../utils/api')
const config = require('../../utils/config')

// 把后端返回的相对静态路径（/static/...）补全为小程序可加载的绝对地址
function absUrl(p) {
  if (!p) return p
  if (/^https?:\/\//.test(p)) return p
  const host = (config.baseUrl || '').replace(/\/api$/, '')
  return host + p
}

function statusText(s) {
  if (s === 'pending') return '待处理'
  if (s === 'replied') return '方案已出'
  if (s === 'done') return '已处理'
  return s || ''
}

Page({
  data: { list: [], openId: null, loading: false, convertingId: null },

  onShow() { this.load() },

  load() {
    this.setData({ loading: true })
    api.getMyConsults()
      .then(list => this.setData({
        list: (list || []).map(x => Object.assign({}, x, {
          statusText: statusText(x.status),
          attachments: (x.attachments || []).map(absUrl)
        })),
        loading: false
      }))
      .catch(() => this.setData({ loading: false }))
  },

  // 展开查看详情；若顾问已回复且本人尚未读，则顺带标记已读（消除红点）
  toggle(e) {
    const id = e.currentTarget.dataset.id
    const item = this.data.list.find(x => x.id === id)
    if (this.data.openId !== id && item && item.reply_at && !item.customer_read_at) {
      api.markConsultRead(id).catch(() => {})
      const list = this.data.list.map(x =>
        x.id === id ? Object.assign({}, x, { customer_read_at: Date.now() }) : x
      )
      this.setData({ list })
    }
    this.setData({ openId: this.data.openId === id ? null : id })
  },

  // P3：对此方案一键下单
  toOrder(e) {
    const id = e.currentTarget.dataset.id
    const item = this.data.list.find(x => x.id === id)
    if (!item) return
    wx.showModal({
      title: '对此方案下单',
      content: '将依据该需求单（线路/联系人）生成正式订单，提交后由顾问确认。是否继续？',
      success: (r) => {
        if (!r.confirm) return
        this.setData({ convertingId: id })
        api.toOrder(id, { person_count: 1, remark: '需求单一键转订单' })
          .then(() => {
            wx.showToast({ title: '订单已生成，顾问将确认', icon: 'none' })
            this.load()
          })
          .catch(err => {
            wx.showToast({ title: (err && err.detail) || '下单失败', icon: 'none' })
          })
          .then(() => this.setData({ convertingId: null }))
      }
    })
  },

  // 预览附件大图
  previewImage(e) {
    const urls = e.currentTarget.dataset.urls || []
    const current = e.currentTarget.dataset.src
    if (urls.length) wx.previewImage({ urls, current })
  },

  // 删除自己的咨询（已转订单的不可删）
  deleteConsult(e) {
    const id = e.currentTarget.dataset.id
    const item = this.data.list.find(x => x.id === id)
    if (!item) return
    if (item.status === 'done') {
      wx.showToast({ title: '已转订单，无法删除', icon: 'none' })
      return
    }
    wx.showModal({
      title: '删除咨询',
      content: '确认删除这条咨询记录？删除后将从列表移除（保留可追溯）。',
      success: (r) => {
        if (!r.confirm) return
        api.deleteConsult(id)
          .then(() => {
            wx.showToast({ title: '已删除', icon: 'none' })
            this.load()
          })
          .catch(err => {
            wx.showToast({ title: (err && err.detail) || '删除失败', icon: 'none' })
          })
      }
    })
  },

  goConsult() { wx.navigateTo({ url: '/pages/consult/consult' }) }
})
