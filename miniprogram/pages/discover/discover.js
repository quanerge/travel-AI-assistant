// pages/discover/discover.js —— 发现：目的地攻略（维基导游原文）
const api = require('../../utils/api')

Page({
  data: {
    list: [],
    loading: true
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 3 })
    }
    this.load()
  },

  load() {
    api.getRecommendRoutes().then(list => {
      this.setData({ list: list || [], loading: false })
    }).catch(() => this.setData({ loading: false }))
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/guideDetail/guideDetail?id=' + e.currentTarget.dataset.id })
  }
})
