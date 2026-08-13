// utils/advisor.js —— 顾问联系方式统一读取与操作（功能2：一键直连真人顾问）
// 优先取后端 /api/config/advisor 拉到的 globalData，回退到 config.js 兜底值。
const config = require('./config')

function getAdvisor() {
  const app = getApp()
  const fromGlobal = app && app.globalData && app.globalData.advisor
  return Object.assign({}, config.advisor || {}, fromGlobal || {})
}

// 一键拨号（号码为空时友好提示，避免拨通失败/写死占位号）
function callAdvisor() {
  const a = getAdvisor()
  if (!a.phone) {
    wx.showToast({ title: '暂未配置顾问电话', icon: 'none' })
    return
  }
  wx.makePhoneCall({ phoneNumber: String(a.phone) })
}

// 复制微信号到剪贴板
function copyWechat() {
  const a = getAdvisor()
  if (!a.wechat) {
    wx.showToast({ title: '暂未配置顾问微信', icon: 'none' })
    return
  }
  wx.setClipboardData({
    data: a.wechat,
    success: () => wx.showToast({ title: '微信号已复制', icon: 'none' })
  })
}

module.exports = { getAdvisor, callAdvisor, copyWechat }
