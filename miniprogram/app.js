// app.js
const config = require('./utils/config')
App({
  globalData: {
    userInfo: null,
    openid: null,
    userId: null,
    userToken: null,
    isLogin: false,
    advisor: null   // 启动后由 /api/config/advisor 拉取，覆盖 config.js 兜底值
  },

  onLaunch() {
    const cached = wx.getStorageSync('userInfo')
    if (cached) {
      this.globalData.userInfo = cached
      this.globalData.isLogin = true
      this.globalData.openid = cached.openid || null
      this.globalData.userId = cached.userId || null
    }
    // 恢复用户 JWT（鉴权用）
    const token = wx.getStorageSync('userToken')
    if (token) this.globalData.userToken = token
    // 微信静默登录：拿 code 换 openid，打通后端用户（MVP 兜底实现）
    this.wxLoginSilent()
    // 拉取顾问联系方式（一键拨号 / 复制微信用），失败则保留 config.js 兜底值
    const api = require('./utils/api')
    api.getAdvisor().then(a => {
      if (a) this.globalData.advisor = Object.assign({}, config.advisor, a)
    }).catch(() => {})
  },

  // 静默登录：wx.login 取 code -> 后端 /api/auth/wx-login -> 存 openid/userId/token
  // 关键修复：复用本地持久化 openid（保证跨启动身份稳定），若后端返回关联客户则自动恢复登录态，
  // 这样用户退出后再打开小程序无需重新注册即可自动登录。
  wxLoginSilent() {
    const api = require('./utils/api')
    const storedOpenid = wx.getStorageSync('openid') || ''
    wx.login({
      success: (res) => {
        if (!res.code) return
        const body = { code: res.code }
        if (storedOpenid) body.openid = storedOpenid
        api.wxLogin(body).then(r => {
          this.globalData.openid = r.openid
          this.globalData.userId = r.userId || r.user_id
          // 持久化 openid，下次启动复用，保证身份稳定
          wx.setStorageSync('openid', r.openid)
          // 持久化用户 JWT，后续收藏等接口携带鉴权
          if (r.token) {
            this.globalData.userToken = r.token
            wx.setStorageSync('userToken', r.token)
          }
          if (r.customer_id) {
            // 该微信身份已注册过客户 -> 自动恢复登录态，无需重新注册
            this.login({
              nickName: r.nickname || '微信用户',
              phone: r.phone || '',
              openid: r.openid,
              userId: r.user_id || r.userId,
              customerId: r.customer_id,
              birthday: r.birthday || null,
              wechat_no: r.wechat_no || null
            })
          } else if (this.globalData.isLogin && this.globalData.userInfo) {
            // 已登录用户关联 userId，便于收藏/下单
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
    if (userInfo.token) {
      this.globalData.userToken = userInfo.token
      wx.setStorageSync('userToken', userInfo.token)
    }
    wx.setStorageSync('userInfo', userInfo)
  },

  // 退出登录：清除本地登录态（微信身份 openid 与 userToken 仍保留，下次启动静默登录自动恢复）
  logout() {
    this.globalData.userInfo = null
    this.globalData.isLogin = false
    this.globalData.userId = null
    wx.removeStorageSync('userInfo')
    wx.removeStorageSync('userToken')
    this.globalData.userToken = null
  }
})
