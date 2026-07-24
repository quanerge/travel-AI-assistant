// pages/orders/orders.js
const api = require('../../utils/api')
const config = require('../../utils/config')

Page({
  data: { orders: [], statusMap: config.orderStatusMap },

  onShow() {
    api.getOrders().then(list => {
      this.setData({ orders: list.sort((a, b) => b.id - a.id) })
    })
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/orderDetail/orderDetail?id=' + e.currentTarget.dataset.id })
  }
})
