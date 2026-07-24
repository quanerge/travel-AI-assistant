// pages/mine/mine.js
const app = getApp()

Page({
  data: { userInfo: null, isLogin: false },

  onShow() {
    this.setData({
      userInfo: app.globalData.userInfo,
      isLogin: app.globalData.isLogin
    })
  },

  goRegister() { wx.navigateTo({ url: '/pages/register/register' }) },
  goOrders() { wx.navigateTo({ url: '/pages/orders/orders' }) },
  goConsult() { wx.navigateTo({ url: '/pages/consult/consult' }) },
  goPlan() { wx.switchTab({ url: '/pages/plan/plan' }) },
  goFavorites() { wx.navigateTo({ url: '/pages/favorites/favorites' }) },
  goAbout() { wx.navigateTo({ url: '/pages/about/about' }) },

  logout() {
    wx.showModal({
      title: '提示',
      content: '确定退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          app.logout()
          this.setData({ userInfo: null, isLogin: false })
          wx.showToast({ title: '已退出登录', icon: 'none' })
        }
      }
    })
  }
})
