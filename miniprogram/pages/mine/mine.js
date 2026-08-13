// pages/mine/mine.js
const app = getApp()
const api = require('../../utils/api')

Page({
  data: {
    userInfo: null, isLogin: false,
    birthday: '', birthdayTip: '', birthdaySoon: false,
    unreadCount: 0
  },

  onShow() {
    const ui = app.globalData.userInfo
    const birthday = (ui && ui.birthday) || ''
    const off = this._birthdayOffset(birthday)
    let tip = ''
    let soon = false
    if (off === 0) { tip = '🎉 今天是你的生日！'; soon = true }
    else if (off === 1) { tip = '🎂 明天是你的生日'; soon = true }
    this.setData({
      userInfo: ui,
      isLogin: app.globalData.isLogin,
      birthday,
      birthdayTip: tip,
      birthdaySoon: soon
    })
    // 拉取未读咨询数（顾问已回复但未查看），用于红点提示
    if (app.globalData.isLogin) {
      api.getConsultUnread().then(r => this.setData({ unreadCount: (r && r.count) || 0 })).catch(() => {})
    } else {
      this.setData({ unreadCount: 0 })
    }
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 3 })
    }
  },

  // 计算生日相对今天的偏移：0=今天, 1=明天, -1=非临近
  _birthdayOffset(mmdd) {
    if (!mmdd || mmdd.length !== 5) return -1
    const now = new Date()
    for (let i = 0; i <= 1; i++) {
      const d = new Date(now.getTime())
      d.setDate(now.getDate() + i)
      const m = ('0' + (d.getMonth() + 1)).slice(-2)
      const day = ('0' + d.getDate()).slice(-2)
      if ((m + '-' + day) === mmdd) return i
    }
    return -1
  },

  goProfile() { wx.navigateTo({ url: '/pages/profile/profile' }) },
  goRegister() { wx.navigateTo({ url: '/pages/register/register' }) },
  goOrders() { wx.navigateTo({ url: '/pages/orders/orders' }) },
  goConsult() { wx.navigateTo({ url: '/pages/consult/consult' }) },
  goPlan() { wx.switchTab({ url: '/pages/plan/plan' }) },
  goFavorites() { wx.navigateTo({ url: '/pages/favorites/favorites' }) },
  goAbout() { wx.navigateTo({ url: '/pages/about/about' }) },
  goCoupons() { wx.navigateTo({ url: '/pages/coupons/coupons' }) },
  goMyConsult() { wx.navigateTo({ url: '/pages/myConsult/myConsult' }) },

  logout() {
    wx.showModal({
      title: '提示',
      content: '确定退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          app.logout()
          this.setData({ userInfo: null, isLogin: false, birthday: '', birthdayTip: '', birthdaySoon: false })
          wx.showToast({ title: '已退出登录', icon: 'none' })
        }
      }
    })
  }
})
