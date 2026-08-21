// pages/guideDetail/guideDetail.js —— 目的地攻略原文阅读页（维基导游，不做 AI 加工）
const api = require('../../utils/api')

Page({
  data: {
    id: null,
    guide: null,
    loading: true,
    showRaw: false
  },

  onLoad(options) {
    const id = options.id
    this.setData({ id })
    api.getRecommendGuide(id).then(g => {
      if (!g) {
        wx.showToast({ title: '攻略不存在', icon: 'none' })
        return
      }
      this.setData({ guide: g })
      wx.setNavigationBarTitle({ title: (g.mode === 'ai' ? g.ai_name : g.title) + ' · 攻略' })
    }).catch(() => {
      wx.showToast({ title: '加载失败', icon: 'none' })
    }).finally(() => this.setData({ loading: false }))
  },

  // 展开/收起维基导游原文
  toggleRaw() {
    this.setData({ showRaw: !this.data.showRaw })
  },

  // 复制维基导游原文链接（CC BY-SA 署名；小程序无法直接跳外部浏览器）
  copyLink() {
    const url = this.data.guide && this.data.guide.source_url
    if (!url) return
    wx.setClipboardData({
      data: url,
      success: () => wx.showToast({ title: '链接已复制', icon: 'none' })
    })
  }
})
