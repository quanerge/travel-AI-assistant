// pages/favorites/favorites.js
const api = require('../../utils/api')
const app = getApp()
const { resolveCover } = require('../../utils/cover')

Page({
  data: { list: [] },

  onShow() { this.load() },

  load() {
    const uid = app.globalData.userId
    if (!uid) { this.setData({ list: [] }); return }
    api.getFavorites().then(list => {
      this.setData({ list: list.map(x => Object.assign({}, x, { cover: resolveCover(x.cover) })) })
    }).catch(() => {})
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/routeDetail/routeDetail?id=' + e.currentTarget.dataset.id })
  }
})
