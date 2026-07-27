// pages/profile/profile.js
const app = getApp()
const api = require('../../utils/api')

Page({
  data: {
    form: { nickname: '', phone: '', wechat_no: '', birthday: '' },
    birthdayValue: '1990-01-01',
    saving: false
  },

  onLoad() {
    const ui = app.globalData.userInfo || {}
    const birthday = ui.birthday || ''
    this.setData({
      form: {
        nickname: ui.nickName || '',
        phone: ui.phone || '',
        wechat_no: ui.wechat_no || '',
        birthday
      },
      birthdayValue: birthday ? '1990-' + birthday : '1990-01-01'
    })
  },

  input(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ ['form.' + field]: e.detail.value })
  },

  onBirthdayChange(e) {
    const md = e.detail.value.slice(5, 10)  // "MM-DD"
    this.setData({ 'form.birthday': md, birthdayValue: '1990-' + md })
  },

  save() {
    const f = this.data.form
    if (!f.nickname) { wx.showToast({ title: '请填写昵称', icon: 'none' }); return }
    if (f.phone && !/^1\d{10}$/.test(f.phone)) { wx.showToast({ title: '手机号格式不正确', icon: 'none' }); return }

    const cid = app.globalData.userInfo && app.globalData.userInfo.customerId
    if (!cid) { wx.showToast({ title: '未登录', icon: 'none' }); return }

    // 仅提交非空字段，避免覆盖后端已有值
    const payload = {}
    if (f.nickname) payload.name = f.nickname
    if (f.phone) payload.phone = f.phone
    if (f.wechat_no) payload.wechat_no = f.wechat_no
    if (f.birthday) payload.birthday = f.birthday

    this.setData({ saving: true })
    api.updateCustomer(cid, payload).then(() => {
      // 写回本地登录态，供"我的"页实时回显
      const ui = app.globalData.userInfo
      ui.nickName = f.nickname
      if (f.phone) ui.phone = f.phone
      if (f.wechat_no) ui.wechat_no = f.wechat_no
      if (f.birthday) ui.birthday = f.birthday
      app.globalData.userInfo = ui
      wx.setStorageSync('userInfo', ui)
      wx.showToast({ title: '已保存', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 600)
    }).catch(err => {
      const msg = (err && (err.detail || err.message)) || '保存失败'
      wx.showToast({ title: msg, icon: 'none' })
    }).finally(() => this.setData({ saving: false }))
  }
})
