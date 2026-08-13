// pages/about/about.js
const advisorUtil = require('../../utils/advisor')
Page({
  data: { advisor: {} },
  onLoad() { this.setData({ advisor: advisorUtil.getAdvisor() }) },
  onShow() { this.setData({ advisor: advisorUtil.getAdvisor() }) },
  callAdvisor() { advisorUtil.callAdvisor() },
  copyWechat() { advisorUtil.copyWechat() },
  goPrivacy() { wx.navigateTo({ url: '/pages/privacy/privacy' }) }
})
