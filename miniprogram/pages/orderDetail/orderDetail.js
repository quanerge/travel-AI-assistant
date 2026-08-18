// pages/orderDetail/orderDetail.js
const api = require('../../utils/api')
const config = require('../../utils/config')
const advisorUtil = require('../../utils/advisor')

// 基础步骤（与需求 7.5 一致）；带尾款的订单额外插入「待付尾款」节点
const baseSteps = ['pending_confirm', 'confirmed', 'deposit_received', 'completed']

// 根据订单是否有未收尾款，动态拼装步骤条：
// - 有尾款：… → 定金已收 → 待付尾款 → 完成
// - 无尾款（定金即全款）：… → 定金已收 → 完成
function buildSteps(order) {
  const s = ['pending_confirm', 'confirmed', 'deposit_received']
  if ((order.balance_amount || 0) > 0 && !order.balance_paid) s.push('balance_pending')
  s.push('completed')
  return s
}

Page({
  data: { order: null, route: null, advisor: {}, statusMap: config.orderStatusMap, steps: baseSteps, stepIndex: 0 },

  onLoad(options) {
    this.setData({ advisor: advisorUtil.getAdvisor() })
    api.getOrderDetail(options.id).then(o => {
      if (!o) { wx.showToast({ title: '订单不存在', icon: 'none' }); return }
      const steps = buildSteps(o)
      this.setData({ order: o, steps, stepIndex: Math.max(0, steps.indexOf(o.status)) })
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
    advisorUtil.callAdvisor()
  },

  copyWechat() {
    advisorUtil.copyWechat()
  }
})
