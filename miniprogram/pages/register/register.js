// pages/register/register.js
const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    form: { nickname: '', phone: '', wechat_no: '', travel_preference: '', budget_range: '', birthday: '' },
    submitting: false
  },

  input(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ ['form.' + field]: e.detail.value })
  },

  // 日期选择器返回 "YYYY-MM-DD"，存原始值，提交时转 MM-DD
  onBirthdayChange(e) {
    this.setData({ 'form.birthday': e.detail.value })
  },

  submit() {
    const f = this.data.form
    if (!f.nickname) { wx.showToast({ title: '请填写昵称', icon: 'none' }); return }
    if (!/^1\d{10}$/.test(f.phone)) { wx.showToast({ title: '请填写正确手机号', icon: 'none' }); return }

    const payload = Object.assign({}, f)
    // 生日：YYYY-MM-DD -> MM-DD（仅保留月日，用于纪念日提醒）
    if (payload.birthday && payload.birthday.length >= 10) {
      payload.birthday = payload.birthday.slice(5, 10)
    } else {
      delete payload.birthday
    }
    const uid = app.globalData.userId
    if (uid) payload.user_id = uid
    // 把微信身份(openid)一并上报，便于后端把客户与静默登录绑定，实现退出后自动恢复
    if (app.globalData.openid) payload.openid = app.globalData.openid
    this.setData({ submitting: true })
    api.registerCustomer(payload).then(res => {
      const userInfo = {
        nickName: res.nickname || f.nickname,
        phone: res.phone || f.phone,
        userId: res.user_id || res.userId,
        customerId: res.customer_id || res.customerId,
        birthday: res.birthday || null,
        wechat_no: res.wechat_no || null
      }
      app.login(userInfo)
      wx.showToast({
        title: res.already_registered ? '已注册，已登录' : '注册成功',
        icon: 'success'
      })
      setTimeout(() => { wx.navigateBack() }, 800)
    }).catch(err => {
      const msg = (err && (err.detail || err.message)) || '注册失败'
      wx.showToast({ title: msg, icon: 'none' })
    }).finally(() => {
      this.setData({ submitting: false })
    })
  }
})
