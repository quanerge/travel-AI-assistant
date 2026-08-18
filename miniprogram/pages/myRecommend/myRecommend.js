// pages/myRecommend/myRecommend.js
const api = require('../../utils/api')
const { resolveCover } = require('../../utils/cover')

Page({
  data: {
    list: [],
    loading: false
  },

  onShow() {
    this.load()
  },

  load() {
    this.setData({ loading: true })
    api.getMyRecommends().then(list => {
      const items = (list || []).map(x => Object.assign({}, x, {
        cover: resolveCover(x.route_cover),
        statusLabel: { pending: '待确认', accepted: '已接受', declined: '暂不感兴趣' }[x.status] || x.status
      }))
      this.setData({ list: items })
    }).catch(() => {
      wx.showToast({ title: '加载失败', icon: 'none' })
    }).finally(() => {
      this.setData({ loading: false })
    })
  },

  accept(e) {
    const id = e.currentTarget.dataset.id
    wx.showLoading({ title: '提交中' })
    api.acceptRecommend(id).then(() => {
      wx.showToast({ title: '已接受，顾问将为您跟进', icon: 'success' })
      this.load()
    }).catch(() => {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }).finally(() => wx.hideLoading())
  },

  decline(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '提示',
      content: '确定暂不感兴趣吗？',
      success: (res) => {
        if (res.confirm) {
          api.declineRecommend(id).then(() => this.load()).catch(() => {})
        }
      }
    })
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/routeDetail/routeDetail?id=' + id })
  }
})
