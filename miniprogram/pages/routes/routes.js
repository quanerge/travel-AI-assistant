// pages/routes/routes.js
const api = require('../../utils/api')
const { resolveCover } = require('../../utils/cover')

const categories = ['全部', '国内游', '短途游', '境外游']

Page({
  data: {
    categories,
    activeCat: '全部',
    keyword: '',
    list: [],
    filters: { minDays: '', maxDays: '', departure: '', priceMin: '', priceMax: '' }
  },

  onLoad() {
    this.load()
  },

  load() {
    api.getRoutes().then(list => {
      const { activeCat, keyword, filters } = this.data
      let r = list
      if (activeCat !== '全部') r = r.filter(x => x.category === activeCat)
      if (keyword) r = r.filter(x => x.name.indexOf(keyword) >= 0 || x.destination.indexOf(keyword) >= 0)
      if (filters.minDays) r = r.filter(x => x.days >= Number(filters.minDays))
      if (filters.maxDays) r = r.filter(x => x.days <= Number(filters.maxDays))
      if (filters.departure) r = r.filter(x => x.departure.indexOf(filters.departure) >= 0)
      if (filters.priceMin) r = r.filter(x => x.price >= Number(filters.priceMin))
      if (filters.priceMax) r = r.filter(x => x.price <= Number(filters.priceMax))
      this.setData({ list: r.map(x => Object.assign({}, x, { cover: resolveCover(x.cover) })) })
    })
  },

  onSearch(e) {
    this.setData({ keyword: e.detail.value }, () => this.load())
  },

  onFilter(e) {
    const f = e.currentTarget.dataset.f
    this.setData({ ['filters.' + f]: e.detail.value }, () => this.load())
  },

  switchCat(e) {
    this.setData({ activeCat: e.currentTarget.dataset.cat }, () => this.load())
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/routeDetail/routeDetail?id=' + e.currentTarget.dataset.id })
  },

  onImgError(e) {
    const id = Number(e.currentTarget.dataset.id)
    const list = this.data.list.map(r => (r.id === id ? Object.assign({}, r, { cover: '' }) : r))
    this.setData({ list })
  }
})
