// pages/orderDetail/orderDetail.js
const api = require('../../utils/api')
const config = require('../../utils/config')

// 与需求 7.5 一致的步骤
const steps = ['pending_confirm', 'confirmed', 'pending_deposit', 'deposit_received', 'success', 'completed']

Page({
  data: { order: null, route: null, statusMap: config.orderStatusMap, steps, stepIndex: 0 },

  onLoad(options) {
    api.getOrderDetail(options.id).then(o => {
      if (!o) { wx.showToast({ title: '订单不存在', icon: 'none' }); return }
      this.setData({ order: o, stepIndex: Math.max(0, steps.indexOf(o.status)) })
      // 拉取该订单所属线路的详情（名称/目的地/行程/费用说明），订单页默认不返回
      if (o.route_id) {
        api.getRouteDetail(o.route_id).then(r => {
          if (r) this.setData({ route: r })
        }).catch(() => {})
      }
    })
  },

  // 跳转到线路完整详情页（含图集、每日行程展开）
  goRouteDetail() {
    const r = this.data.route
    if (r && r.id) wx.navigateTo({ url: '/pages/routeDetail/routeDetail?id=' + r.id })
  },

  callAdvisor() {
    wx.makePhoneCall({ phoneNumber: '4000000000' })
  }
})
