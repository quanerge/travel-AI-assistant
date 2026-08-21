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

// 本地「已领」兜底集合：即使后端 claimed 偶发未生效，也能稳定显示「已领」，杜绝闪烁回退
const CLAIMED_KEY = 'claimedCouponIds'
function loadClaimedIds() {
  try { return new Set(wx.getStorageSync(CLAIMED_KEY) || []) } catch (e) { return new Set() }
}
function saveClaimedIds(set) {
  try { wx.setStorageSync(CLAIMED_KEY, [...set]) } catch (e) {}
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
    const claimedIds = loadClaimedIds()
    api.getCoupons().then(list => {
      const claimable = (list || []).map(c => Object.assign({}, c, {
        _applicable: applicableText(c.applicable),
        _expire: fmtExpire(c.expire_at),
        _claimed: !!(c.claimed || claimedIds.has(c.id))
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
      // 持久化「已领」，与后端 claimed 双重兜底，确保状态永不回退
      const claimedIds = loadClaimedIds()
      claimedIds.add(Number(id))
      saveClaimedIds(claimedIds)
      // 仅本地标记该项为已领（不再整列重拉覆盖，避免闪烁回退）
      const claimable = (this.data.claimable || []).map(c =>
        c.id === id ? Object.assign({}, c, { _claimed: true }) : c
      )
      this.setData({ claimable })
      // 同步刷新「我的优惠券」，让已领券出现在我的券列表
      this.loadMine()
    }).catch(err => {
      wx.showToast({ title: (err && err.detail) || (err && err.message) || '领取失败', icon: 'none' })
    })
  }
})
