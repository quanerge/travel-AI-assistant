// pages/signup/signup.js
const api = require('../../utils/api')
const app = getApp()

// 后端 expire_at 存的是 UTC 时间(无时区标记),JSON 序列化后前端 new Date() 会按本地时区解析,
// 中国区会偏差约 8 小时,导致"优惠券是否可用"误判。统一按 UTC 解析保证判断准确。
function toUtc(s) {
  if (!s) return null
  return new Date(s.endsWith('Z') ? s : s + 'Z')
}

Page({
  data: {
    route: null,
    form: { name: '', phone: '', person_count: 1, departure_date: '', remark: '' },
    submitted: false,
    coupons: [],
    selectedCoupon: null,
    discount: 0,
    baseAmount: 0,
    payable: 0
  },

  onLoad(options) {
    if (options.routeId) {
      api.getRouteDetail(options.routeId).then(r => {
        if (r) {
          this.setData({ route: r })
          this._calc()
        }
      })
    }
    if (app.globalData.isLogin) this._loadCoupons()
  },

  _loadCoupons() {
    api.getMyCoupons().then(list => {
      const now = Date.now()
      const usable = (list || []).filter(c =>
        c.status === 'unused' && (!c.expire_at || toUtc(c.expire_at).getTime() > now)
      )
      this.setData({ coupons: usable })
    }).catch(() => {})
  },

  _calc() {
    const r = this.data.route
    if (!r) return
    const base = r.price * this.data.form.person_count
    const discount = this.data.selectedCoupon ? this.data.selectedCoupon.amount : 0
    this.setData({ baseAmount: base, payable: Math.max(0, base - discount), discount })
  },

  input(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ ['form.' + field]: e.detail.value })
  },

  stepPerson(e) {
    const d = Number(e.currentTarget.dataset.d)
    let n = this.data.form.person_count + d
    if (n < 1) n = 1
    if (n > 20) n = 20
    this.setData({ ['form.person_count']: n })
    this._calc()
  },

  dateChange(e) {
    this.setData({ ['form.departure_date']: e.detail.value })
  },

  openCoupons() {
    if (!this.data.coupons.length) {
      wx.showToast({ title: '暂无可用的优惠券', icon: 'none' })
      return
    }
    const items = this.data.coupons.map(c => ('¥' + c.amount + ' ' + c.title))
    items.push('不使用优惠券')
    wx.showActionSheet({
      itemList: items,
      success: (res) => {
        if (res.tapIndex === items.length - 1) {
          this.setData({ selectedCoupon: null })
          this._calc()
          return
        }
        this.setData({ selectedCoupon: this.data.coupons[res.tapIndex] })
        this._calc()
      }
    })
  },

  submit() {
    const f = this.data.form
    if (!f.name) { wx.showToast({ title: '请填写姓名', icon: 'none' }); return }
    if (!/^1\d{10}$/.test(f.phone)) { wx.showToast({ title: '请填写正确手机号', icon: 'none' }); return }
    if (!f.departure_date) { wx.showToast({ title: '请选择出发日期', icon: 'none' }); return }

    const uid = app.globalData.userId
    const payload = Object.assign({ route_id: this.data.route ? this.data.route.id : null, user_id: uid || null }, f)
    if (this.data.selectedCoupon) payload.coupon_id = this.data.selectedCoupon.id
    api.submitSignup(payload).then(() => {
      this.setData({ submitted: true })
    })
  },

  goOrders() { wx.navigateTo({ url: '/pages/orders/orders' }) }
})
