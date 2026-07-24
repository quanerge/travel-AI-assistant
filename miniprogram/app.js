// app.js
App({
  globalData: {
    userInfo: null,
    openid: null,
    userId: null,
    isLogin: false
  },

  onLaunch() {
    const cached = wx.getStorageSync('userInfo')
    if (cached) {
      this.globalData.userInfo = cached
      this.globalData.isLogin = true
      this.globalData.openid = cached.openid || null
      this.globalData.userId = cached.userId || null
    }
    // 微信静默登录：拿 code 换 openid，打通后端用户（MVP 兜底实现）
    this.wxLoginSilent()
  },

  // 静默登录：wx.login 取 code -> 后端 /api/auth/wx-login -> 存 openid/userId
  wxLoginSilent() {
    const api = require('./utils/api')
    wx.login({
      success: (res) => {
        if (!res.code) return
        api.wxLogin({ code: res.code }).then(r => {
          this.globalData.openid = r.openid
          this.globalData.userId = r.userId || r.user_id
          // 已登录用户关联 userId，便于收藏/下单
          if (this.globalData.isLogin && this.globalData.userInfo) {
            this.globalData.userInfo.openid = r.openid
            this.globalData.userInfo.userId = r.userId || r.user_id
            wx.setStorageSync('userInfo', this.globalData.userInfo)
          }
        }).catch(() => {})
      }
    })
  },

  // 注册/登录成功后写入登录态
  login(userInfo) {
    this.globalData.userInfo = userInfo
    this.globalData.isLogin = true
    if (userInfo.openid) this.globalData.openid = userInfo.openid
    if (userInfo.userId) this.globalData.userId = userInfo.userId
    wx.setStorageSync('userInfo', userInfo)
  },

  // 退出登录：清除本地登录态
  logout() {
    this.globalData.userInfo = null
    this.globalData.isLogin = false
    this.globalData.openid = null
    this.globalData.userId = null
    wx.removeStorageSync('userInfo')
  }
})
