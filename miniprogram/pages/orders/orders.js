// pages/orders/orders.js
const api = require('../../utils/api')
const config = require('../../utils/config')

// 客户仅可删除「尚未产生资金往来」的订单（待确认/待付定金且未付定金）
function canDelete(o) {
  if (!o) return false
  return !o.deposit_paid && ['pending_confirm', 'pending_deposit'].includes(o.status)
}

Page({
  data: { orders: [], statusMap: config.orderStatusMap },

  onShow() {
    api.getOrders().then(list => {
      const orders = (list || []).map(o => Object.assign({}, o, { canDelete: canDelete(o) }))
      this.setData({ orders: orders.sort((a, b) => b.id - a.id) })
    })
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/orderDetail/orderDetail?id=' + e.currentTarget.dataset.id })
  },

  // 删除自己的订单（已确认/已付定金的不可删，需联系顾问）
  deleteOrder(e) {
    const id = e.currentTarget.dataset.id
    const item = this.data.orders.find(x => x.id === id)
    if (!item) return
    if (!item.canDelete) {
      wx.showToast({ title: '已确认/已付定金，无法删除', icon: 'none' })
      return
    }
    wx.showModal({
      title: '删除订单',
      content: '确认删除这条订单记录？删除后将从列表移除（保留可追溯）。',
      success: (r) => {
        if (!r.confirm) return
        api.deleteOrder(id)
          .then(() => {
            wx.showToast({ title: '已删除', icon: 'none' })
            this.onShow()
          })
          .catch(err => {
            wx.showToast({ title: (err && err.detail) || '删除失败', icon: 'none' })
          })
      }
    })
  }
})
