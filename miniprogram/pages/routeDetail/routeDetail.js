// pages/routeDetail/routeDetail.js
const api = require('../../utils/api')
const app = getApp()
const { resolveCover } = require('../../utils/cover')

Page({
  data: {
    id: null,
    route: null,
    expandedDay: -1,
    favorited: false,
    reviews: [],
    avgRating: 0,
    reviewCount: 0,
    highlight: null,        // AI 亮点解读（概览/必看/美食/风光/贴士）
    highlightLoading: false
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
      this.loadReviews()
      this.loadHighlight(id)
    })
  },

  loadHighlight(id) {
    this.setData({ highlightLoading: true })
    api.getRouteHighlight(id).then(h => {
      // 仅展示对客户端有用的字段（share_text 是顾问可发送全文，小程序不展示）
      if (h && (h.overview || (h.must_see && h.must_see.length))) {
        this.setData({ highlight: h })
      }
    }).catch(() => {}).finally(() => {
      this.setData({ highlightLoading: false })
    })
  },

  onShow() {
    // 从写评价/分享等页面返回时，重载评价区（刚提交的评价即时可见）
    if (this.data.id) this.loadReviews()
  },

  loadFav() {
    const uid = app.globalData.userId
    if (uid && this.data.route) {
      api.getFavorites(uid).then(list => {
        this.setData({ favorited: list.some(x => x.id === this.data.route.id) })
      }).catch(() => {})
    }
  },

  loadReviews() {
    if (!this.data.id) return
    api.getReviews(this.data.id).then(res => {
      const list = (res.items || []).slice(0, 3).map(x => Object.assign({}, x, {
        // 晒图可能是后端相对路径，需补全域名前缀（与封面一致）
        images: (x.images || []).map(resolveCover)
      }))
      this.setData({
        reviews: list,
        avgRating: res.avg_rating || 0,
        reviewCount: res.total || 0
      })
    }).catch(() => {})
  },

  goWriteReview() {
    const uid = app.globalData.userId
    if (!uid) { wx.showToast({ title: '请先登录后再评价', icon: 'none' }); return }
    wx.navigateTo({ url: '/pages/reviewEdit/reviewEdit?routeId=' + this.data.id })
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
      // 收藏即表达意向 → 自动把该线路亮点推送进「我的推荐」（顾问零操作）
      if (r.favorited) this._pushRecommend()
    })
  },

  // 自动分发：客户一产生意向（收藏/咨询/报名）即把该线路 AI 亮点推入「我的推荐」
  _pushRecommend() {
    const uid = app.globalData.userId
    if (!uid || !this.data.route) return
    api.pushRecommend(this.data.route.id).catch(() => {})
  },

  goSignup() {
    this._pushRecommend()
    wx.navigateTo({ url: '/pages/signup/signup?routeId=' + this.data.id })
  },

  goConsult() {
    this._pushRecommend()
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
