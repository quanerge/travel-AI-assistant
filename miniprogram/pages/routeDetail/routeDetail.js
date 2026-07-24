// pages/routeDetail/routeDetail.js
const api = require('../../utils/api')
const app = getApp()
const { resolveCover } = require('../../utils/cover')

Page({
  data: {
    id: null,
    route: null,
    expandedDay: -1,
    favorited: false
  },

  onLoad(options) {
    const id = options.id
    this.setData({ id })
    api.getRouteDetail(id).then(r => {
      if (!r) { wx.showToast({ title: '线路不存在', icon: 'none' }); return }
      r = Object.assign({}, r, { cover: resolveCover(r.cover) })
      // 图集为空时用封面兜底，保证轮播有内容
      if (!r.gallery || !r.gallery.length) r.gallery = r.cover ? [r.cover] : ['']
      this.setData({ route: r })
      wx.setNavigationBarTitle({ title: r.name })
      this.loadFav()
    })
  },

  loadFav() {
    const uid = app.globalData.userId
    if (uid && this.data.route) {
      api.getFavorites(uid).then(list => {
        this.setData({ favorited: list.some(x => x.id === this.data.route.id) })
      }).catch(() => {})
    }
  },

  toggleDay(e) {
    const i = e.currentTarget.dataset.i
    this.setData({ expandedDay: this.data.expandedDay === i ? -1 : i })
  },

  toggleFav() {
    const uid = app.globalData.userId
    if (!uid) { wx.showToast({ title: '请先登录后再收藏', icon: 'none' }); return }
    if (!this.data.route) return
    api.toggleFavorite({ user_id: uid, route_id: this.data.route.id }).then(r => {
      this.setData({ favorited: r.favorited })
      wx.showToast({ title: r.favorited ? '已收藏' : '已取消', icon: 'none' })
    })
  },

  goSignup() {
    wx.navigateTo({ url: '/pages/signup/signup?routeId=' + this.data.id })
  },

  goConsult() {
    wx.navigateTo({ url: '/pages/consult/consult?routeId=' + this.data.id })
  },

  // 分享卡片（需求 14 / 7.8）：好友点击可直达线路详情
  onShareAppMessage() {
    const r = this.data.route || {}
    return {
      title: '【顾问推荐】' + (r.name || '精选线路') + ' ¥' + (r.price || '') + '，已有' + (r.signup_count || 0) + '人报名',
      path: '/pages/routeDetail/routeDetail?id=' + this.data.id,
      imageUrl: resolveCover(r.cover)
    }
  }
})
