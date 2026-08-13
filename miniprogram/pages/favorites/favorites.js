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
  },

  // 图片加载失败 → 仅标记 _imgErr，保留 cover 原值
  onImgError(e) {
    const id = Number(e.currentTarget.dataset.id)
    const list = this.data.list.map(r => (r.id === id ? Object.assign({}, r, { _imgErr: true }) : r))
    this.setData({ list })
  },
  onImgLoad(e) {
    const id = Number(e.currentTarget.dataset.id)
    const list = this.data.list.map(r => (r._imgErr ? Object.assign({}, r, { _imgErr: false }) : r))
    this.setData({ list })
  }
})
