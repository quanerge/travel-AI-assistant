// pages/coupons/coupons.js —— 领券中心 + 我的优惠券
const api = require('../../utils/api')

function fmtExpire(s) {
  if (!s) return '长期'
  return String(s).replace('T', ' ').slice(0, 16)
}
function applicableText(a) {
  if (!a || a === 'all') return '全场通用'
  if (a.indexOf('route:') === 0) return '指定线路'
  if (a.indexOf('category:') === 0) return '指定分类'
  return a
}
function statusText(s) {
  return { unused: '可用', used: '已使用', expired: '已过期' }[s] || s
}

Page({
  data: { tab: 'center', claimable: [], mine: [] },

  onShow() { this.load() },

  switchTab(e) {
    const t = e.currentTarget.dataset.t
    this.setData({ tab: t })
    if (t === 'mine') this.loadMine()
  },

  load() {
    api.getCoupons().then(list => {
      const claimable = (list || []).map(c => Object.assign({}, c, {
        _applicable: applicableText(c.applicable),
        _expire: fmtExpire(c.expire_at)
      }))
      this.setData({ claimable })
    }).catch(() => {})
    this.loadMine()
  },

  loadMine() {
    api.getMyCoupons().then(list => {
      const mine = (list || []).map(c => Object.assign({}, c, {
        _status: statusText(c.status),
        _applicable: applicableText(c.applicable),
        _expire: fmtExpire(c.expire_at)
      }))
      this.setData({ mine })
    }).catch(() => {})
  },

  onClaim(e) {
    const id = e.currentTarget.dataset.id
    api.claimCoupon(id).then(() => {
      wx.showToast({ title: '领取成功', icon: 'success' })
      this.loadMine()
    }).catch(err => {
      wx.showToast({ title: (err && err.detail) || '领取失败', icon: 'none' })
    })
  }
})
