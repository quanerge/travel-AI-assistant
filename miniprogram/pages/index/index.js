// pages/index/index.js
const api = require('../../utils/api')
const { resolveCover } = require('../../utils/cover')
const advisorUtil = require('../../utils/advisor')

// 后端 cover 为空时，按目的地兜底到本地示例图（仅本机调试用，正式环境应以 CDN 链接为准）
const DEST_COVER = [
  { keyword: '云南', cover: '/images/yunnan.jpg' },
  { keyword: '新疆', cover: '/images/xinjiang.jpg' },
  { keyword: '川西', cover: '/images/sichuan.jpg' }
]
const INTENSITY_LABEL = { easy: '轻松', normal: '适中', moderate: '较累', challenge: '挑战' }
function withFallbackCover(list) {
  return (list || []).map(r => {
    let cover = r.cover
    if (!cover) {
      const m = DEST_COVER.find(d => (r.destination || '').indexOf(d.keyword) >= 0)
      cover = m ? m.cover : ''
    }
    return Object.assign({}, r, {
      cover: resolveCover(cover),
      intensity_label: INTENSITY_LABEL[r.intensity_level] || '适中'
    })
  })
}

Page({
  data: {
    advisor: {},
    banners: [],
    hotRoutes: []
  },

  // 顾问信息来自后端 /api/config/advisor（兜底 config.js），避免写死占位号
  loadAdvisor() {
    this.setData({ advisor: advisorUtil.getAdvisor() })
  },

  onLoad() {
    this.loadAdvisor()
    api.getRoutes().then(list => {
      const fixed = withFallbackCover(list)
      this.setData({ hotRoutes: fixed, _routes: list })
      this.enrichBanners()
    })
    api.getBanners().then(b => {
      this.setData({ _banners: b || [] })
      this.enrichBanners()
    }).catch(() => {})
  },

  // 把后台配置的 Banner 与线路详情合并，保证轮播图 / 标题 / 跳转齐全（需求 7.1）
  enrichBanners() {
    const b = this.data._banners
    const routes = this.data._routes
    if (!b || !routes) return
    const map = {}
    routes.forEach(r => { map[r.id] = r })
    const banners = b.map(x => {
      const r = map[x.routeId] || {}
      return {
        id: x.routeId,
        name: x.title || r.name,
        cover: x.image,
        destination: r.destination,
        days: r.days,
        price: r.price
      }
    })
    this.setData({ banners })
  },

  goRoute(e) {
    const id = e.currentTarget.dataset.id
    if (!id) { this.goRoutes(); return }
    wx.navigateTo({ url: '/pages/routeDetail/routeDetail?id=' + id })
  },

  goRoutes() {
    wx.switchTab({ url: '/pages/routes/routes' })
  },

  goPlan() {
    wx.switchTab({ url: '/pages/plan/plan' })
  },

  goOrders() {
    wx.navigateTo({ url: '/pages/orders/orders' })
  },

  goConsult() {
    wx.navigateTo({ url: '/pages/consult/consult' })
  },

  goAiChat() {
    wx.navigateTo({ url: '/pages/ai-chat/ai-chat' })
  },

  // 图片加载失败 → 仅标记 _imgErr，保留 cover 原值（不永久清空，避免一次瞬态错误就再也看不到图）
  onImgError(e) {
    const id = Number(e.currentTarget.dataset.id)
    const mark = key => {
      const arr = this.data[key].map(r => (r.id === id ? Object.assign({}, r, { _imgErr: true }) : r))
      this.setData({ [key]: arr })
    }
    mark('hotRoutes')
    mark('banners')
  },
  // 图片加载成功 → 清除失败标记，确保后续能正常显示
  onImgLoad(e) {
    const id = Number(e.currentTarget.dataset.id)
    const clear = key => {
      const arr = this.data[key].map(r => (r._imgErr ? Object.assign({}, r, { _imgErr: false }) : r))
      this.setData({ [key]: arr })
    }
    clear('hotRoutes')
    clear('banners')
  },
  onShow() {
    this.loadAdvisor()
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 0 })
    }
  }
})
