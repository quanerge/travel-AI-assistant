// pages/register/register.js
const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    form: { nickname: '', phone: '', wechat_no: '', travel_preference: '', birthday: '' },
    submitting: false,
    checked: false   // 防「已注册拦截」重复 toast
  },

  // 已注册用户（含退出后静默登录自动恢复）不应再看到注册表单：直接跳走。
  // 静默登录是异步的，onLoad 时可能尚未完成，故 onShow 再补判一次。
  onLoad() {
    this._checkRegistered()
  },

  onShow() {
    if (!this.data.checked) this._checkRegistered()
    // 老用户退出后再进「登录/注册」：主动触发微信静默登录，命中已注册客户即自动恢复，无需重新填表
    if (!app.globalData.isLogin) this._autoWechatLogin()
  },

  // 微信一键登录：复用本地持久化 openid + 新 code 调后端，
  // 后端返回 customer_id（该微信已注册过客户）即弹确认框让用户确认登录，
  // 确认后再写入登录态；取消则留在表单换绑/注册新手机号，避免静默误绑。
  _autoWechatLogin() {
    if (this._autoDone) return
    this._autoDone = true
    const storedOpenid = wx.getStorageSync('openid') || ''
    wx.login({
      success: (res) => {
        if (!res.code) return
        const body = { code: res.code }
        if (storedOpenid) body.openid = storedOpenid
        api.wxLogin(body).then(r => {
          app.globalData.openid = r.openid
          wx.setStorageSync('openid', r.openid)
          if (r.token) {
            app.globalData.userToken = r.token
            wx.setStorageSync('userToken', r.token)
          }
          app.globalData.userId = r.userId || r.user_id
          if (r.customer_id) {
            // 命中已注册客户：弹确认框让用户确认是否以此微信账号登录，
            // 取消则留在表单（可换绑/注册新手机号），避免静默登录造成误绑。
            const nick = r.nickname || '微信用户'
            const phone = r.phone || ''
            const phoneShow = phone
              ? '（' + phone.replace(/^(\d{3})\d{4}(\d{4})$/, '$1****$2') + '）'
              : ''
            wx.showModal({
              title: '登录确认',
              content: '微信用户：' + nick + phoneShow + '\n确认以此账号登录？',
              confirmText: '确认登录',
              cancelText: '换账号',
              success: (modal) => {
                if (!modal.confirm) return
                app.login({
                  nickName: nick,
                  phone,
                  openid: r.openid,
                  userId: r.user_id || r.userId,
                  customerId: r.customer_id,
                  birthday: r.birthday || null,
                  wechat_no: r.wechat_no || null
                })
                this.setData({ checked: true })
                wx.showToast({ title: '登录成功', icon: 'success' })
                setTimeout(() => {
                  const pages = getCurrentPages()
                  if (pages.length > 1) wx.navigateBack()
                  else wx.reLaunch({ url: '/pages/index/index' })
                }, 600)
              }
            })
          }
          // 无 customer_id：真新用户，留在表单完善资料（提交时会带上 openid 完成绑定）
        }).catch(() => {})
      }
    })
  },

  _checkRegistered() {
    const info = app.globalData.userInfo
    if (app.globalData.isLogin && info && info.customerId) {
      this.setData({ checked: true })
      wx.showToast({ title: '您已注册，自动登录', icon: 'none' })
      setTimeout(() => {
        const pages = getCurrentPages()
        if (pages.length > 1) wx.navigateBack()
        // 极边缘：注册页作为首页入口时，重新启动到首页（若首页路径不同请调整此处）
        else wx.reLaunch({ url: '/pages/index/index' })
      }, 600)
    }
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
  },

  // 微信手机号一键注册：用户点 getPhoneNumber 授权真实手机号 -> 后端解出号码 ->
  // 自动建客户并登录（免填表）。一次点击即完成注册，对应后端 /api/auth/wx-phone-register。
  onGetPhone(e) {
    const d = e.detail || {}
    // 调试：把原始返回打到控制台，便于排查"点了没反应"（多为 appid 无权限 / 模拟器未配测试号）
    console.log('[onGetPhone] detail:', JSON.stringify(d))
    // 微信返回失败/用户拒绝：把真实原因暴露出来，避免"点击无反应"的错觉；引导走手动表单
    if (d.errMsg && d.errMsg.indexOf('ok') === -1) {
      const reason = (d.errMsg.split('fail').pop() || '').trim() || '该账号无权限'
      wx.showToast({ title: '手机号授权不可用：' + reason, icon: 'none' })
      return
    }
    const phoneCode = d.code
    if (!phoneCode) {
      wx.showToast({ title: '未能获取手机号，请手动填写', icon: 'none' })
      return
    }
    this.setData({ submitting: true })
    // 取 wx.login code 一并发送，后端据此权威解析 openid（演示环境用存储 openid 兜底）
    wx.login({
      success: (res) => {
        const body = { phone_code: phoneCode }
        if (res.code) body.code = res.code
        const storedOpenid = wx.getStorageSync('openid') || ''
        if (storedOpenid) body.openid = storedOpenid
        api.wxPhoneRegister(body).then(r => {
          app.login({
            nickName: r.nickname || '微信用户',
            phone: r.phone || '',
            openid: r.openid,
            userId: r.user_id || r.userId,
            customerId: r.customer_id,
            birthday: r.birthday || null,
            wechat_no: r.wechat_no || null
          })
          this.setData({ checked: true })
          wx.showToast({ title: r.already_registered ? '已注册，已登录' : '注册成功', icon: 'success' })
          setTimeout(() => {
            const pages = getCurrentPages()
            if (pages.length > 1) wx.navigateBack()
            else wx.reLaunch({ url: '/pages/index/index' })
          }, 700)
        }).catch(err => {
          const msg = (err && (err.detail || err.message)) || '注册失败'
          wx.showToast({ title: msg, icon: 'none' })
        }).finally(() => {
          this.setData({ submitting: false })
        })
      },
      fail: () => {
        this.setData({ submitting: false })
        wx.showToast({ title: '微信登录失败，请手动填写', icon: 'none' })
      }
    })
  }
})
