// pages/signup/signup.js
const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    route: null,
    form: { name: '', phone: '', person_count: 1, departure_date: '', remark: '' },
    submitted: false
  },

  onLoad(options) {
    if (options.routeId) {
      api.getRouteDetail(options.routeId).then(r => {
        if (r) this.setData({ route: r })
      })
    }
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
  },

  dateChange(e) {
    this.setData({ ['form.departure_date']: e.detail.value })
  },

  submit() {
    const f = this.data.form
    if (!f.name) { wx.showToast({ title: '请填写姓名', icon: 'none' }); return }
    if (!/^1\d{10}$/.test(f.phone)) { wx.showToast({ title: '请填写正确手机号', icon: 'none' }); return }
    if (!f.departure_date) { wx.showToast({ title: '请选择出发日期', icon: 'none' }); return }

    const uid = app.globalData.userId
    const payload = Object.assign({ route_id: this.data.route ? this.data.route.id : null, user_id: uid || null }, f)
    api.submitSignup(payload).then(() => {
      this.setData({ submitted: true })
    })
  },

  goOrders() { wx.navigateTo({ url: '/pages/orders/orders' }) }
})
