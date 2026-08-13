// pages/routes/routes.js
const api = require('../../utils/api')
const { resolveCover } = require('../../utils/cover')

const categories = ['全部', '国内游', '短途游', '境外游']

// 行程天数区间（单选）
const dayRanges = [
  { v: 'all', label: '不限' },
  { v: 'd3', label: '3天及以内' },
  { v: 'd46', label: '4-6天' },
  { v: 'd710', label: '7-10天' },
  { v: 'd10', label: '10天以上' }
]
// 价格区间（单选）
const priceRanges = [
  { v: 'all', label: '不限' },
  { v: 'p3k', label: '3000以下' },
  { v: 'p36', label: '3000-6000' },
  { v: 'p610', label: '6000-10000' },
  { v: 'p10k', label: '10000以上' }
]
// 强度等级（适老化核心维度：海拔、走路多少、适不适合年纪，比天数/价格更影响决策）
const intensityOptions = [
  { v: 'all', label: '不限' },
  { v: 'easy', label: '轻松' },
  { v: 'normal', label: '适中' },
  { v: 'moderate', label: '较累' },
  { v: 'challenge', label: '挑战' }
]
const intensityLabelMap = { easy: '轻松', normal: '适中', moderate: '较累', challenge: '挑战' }

// 天数/价格区间断言（避免手动填两个数，改选项式）
function dayTest(v) {
  return {
    all: () => true,
    d3: x => x.days <= 3,
    d46: x => x.days >= 4 && x.days <= 6,
    d710: x => x.days >= 7 && x.days <= 10,
    d10: x => x.days >= 11
  }[v] || (() => true)
}
function priceTest(v) {
  return {
    all: () => true,
    p3k: x => x.price < 3000,
    p36: x => x.price >= 3000 && x.price <= 6000,
    p610: x => x.price > 6000 && x.price <= 10000,
    p10k: x => x.price > 10000
  }[v] || (() => true)
}
function intensityTest(v) {
  if (!v || v === 'all') return () => true
  return x => (x.intensity_level || 'normal') === v
}

Page({
  data: {
    categories,
    dayRanges,
    priceRanges,
    intensityOptions,
    departureOptions: ['不限'],
    activeCat: '全部',
    keyword: '',
    list: [],
    allRoutes: [],           // 原始全量，筛选基于此（避免每次搜索都请求网络）
    filters: { dayRange: 'all', priceRange: 'all', departure: '不限', intensity: 'all' },
    showFilters: false,      // 筛选面板默认收起，节省页面空间
    filterSummary: '全部',
    activeCount: 0
  },

  onLoad() {
    this.load()
  },

  // 拉取全量线路，并提取出发地候选
  load() {
    api.getRoutes().then(list => {
      const depSet = {}
      list.forEach(x => { if (x.departure) depSet[x.departure] = true })
      const departureOptions = ['不限', ...Object.keys(depSet)]
      this.setData({ allRoutes: list, departureOptions }, () => this.applyFilters())
    })
  },

  // 本地筛选（纯前端，不重发请求）
  applyFilters() {
    const { allRoutes, activeCat, keyword, filters, dayRanges, priceRanges, intensityOptions } = this.data
    const kw = (keyword || '').trim()
    const dTest = dayTest(filters.dayRange)
    const pTest = priceTest(filters.priceRange)
    const iTest = intensityTest(filters.intensity)
    let r = allRoutes
    if (activeCat !== '全部') r = r.filter(x => x.category === activeCat)
    if (kw) r = r.filter(x => (x.name || '').indexOf(kw) >= 0 || (x.destination || '').indexOf(kw) >= 0)
    r = r.filter(dTest).filter(pTest).filter(iTest)
    if (filters.departure && filters.departure !== '不限') {
      r = r.filter(x => (x.departure || '') === filters.departure)
    }
    // 计算已选筛选摘要（用于折叠态单行展示）
    const parts = []
    let count = 0
    if (filters.dayRange !== 'all') {
      const it = dayRanges.find(d => d.v === filters.dayRange)
      if (it) { parts.push(it.label); count++ }
    }
    if (filters.priceRange !== 'all') {
      const it = priceRanges.find(d => d.v === filters.priceRange)
      if (it) { parts.push(it.label); count++ }
    }
    if (filters.intensity !== 'all') {
      const it = intensityOptions.find(d => d.v === filters.intensity)
      if (it) { parts.push(it.label); count++ }
    }
    if (filters.departure && filters.departure !== '不限') {
      parts.push(filters.departure); count++
    }
    this.setData({
      list: r.map(x => Object.assign({}, x, {
        cover: resolveCover(x.cover),
        intensity_label: intensityLabelMap[x.intensity_level] || '适中'
      })),
      filterSummary: parts.length ? parts.join(' · ') : '全部',
      activeCount: count
    })
  },

  // 折叠/展开筛选面板
  toggleFilters() {
    this.setData({ showFilters: !this.data.showFilters })
  },

  onSearch(e) {
    this.setData({ keyword: e.detail.value }, () => this.applyFilters())
  },

  pickDay(e) {
    this.setData({ 'filters.dayRange': e.currentTarget.dataset.v }, () => this.applyFilters())
  },

  pickPrice(e) {
    this.setData({ 'filters.priceRange': e.currentTarget.dataset.v }, () => this.applyFilters())
  },

  pickDeparture(e) {
    this.setData({ 'filters.departure': e.currentTarget.dataset.v }, () => this.applyFilters())
  },

  pickIntensity(e) {
    this.setData({ 'filters.intensity': e.currentTarget.dataset.v }, () => this.applyFilters())
  },

  switchCat(e) {
    this.setData({ activeCat: e.currentTarget.dataset.cat }, () => this.applyFilters())
  },

  resetFilters() {
    this.setData({
      activeCat: '全部',
      keyword: '',
      filters: { dayRange: 'all', priceRange: 'all', departure: '不限', intensity: 'all' }
    }, () => this.applyFilters())
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/routeDetail/routeDetail?id=' + e.currentTarget.dataset.id })
  },

  // 图片加载失败 → 仅标记 _imgErr，保留 cover 原值（与首页一致）
  onImgError(e) {
    const id = Number(e.currentTarget.dataset.id)
    const list = this.data.list.map(r => (r.id === id ? Object.assign({}, r, { _imgErr: true }) : r))
    this.setData({ list })
  },
  // 图片加载成功 → 清除失败标记
  onImgLoad(e) {
    const id = Number(e.currentTarget.dataset.id)
    const list = this.data.list.map(r => (r._imgErr ? Object.assign({}, r, { _imgErr: false }) : r))
    this.setData({ list })
  },
  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1 })
    }
  }
})
