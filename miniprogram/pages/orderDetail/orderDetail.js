// pages/orderDetail/orderDetail.js
const api = require('../../utils/api')
const config = require('../../utils/config')

// 与需求 7.5 一致的步骤
const steps = ['pending_confirm', 'confirmed', 'pending_deposit', 'deposit_received', 'success', 'completed']

Page({
  data: { order: null, statusMap: config.orderStatusMap, steps, stepIndex: 0 },

  onLoad(options) {
    api.getOrderDetail(options.id).then(o => {
      if (!o) { wx.showToast({ title: '订单不存在', icon: 'none' }); return }
      this.setData({ order: o, stepIndex: Math.max(0, steps.indexOf(o.status)) })
    })
  },

  callAdvisor() {
    wx.makePhoneCall({ phoneNumber: '4000000000' })
  }
})
