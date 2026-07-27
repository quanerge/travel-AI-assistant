// utils/api.js —— 统一数据访问：mock 与后端自动切换
const config = require('./config')
const { request } = require('./request')
const mock = require('./mock')

const useMock = config.useMock

const api = {
  getRoutes() {
    return useMock ? mock.getRoutes() : request('/routes')
  },
  getRouteDetail(id) {
    return useMock ? mock.getRouteDetail(id) : request('/routes/' + id)
  },
  submitSignup(payload) {
    return useMock ? mock.submitSignup(payload) : request('/orders', 'POST', payload)
  },
  submitPlan(payload) {
    return useMock ? mock.submitPlan(payload) : request('/consult', 'POST', payload)
  },
  getOrders() {
    return useMock ? mock.getOrders() : request('/orders')
  },
  getOrderDetail(id) {
    return useMock ? mock.getOrderDetail(id) : request('/orders/' + id)
  },
  submitConsult(payload) {
    return useMock ? mock.submitConsult(payload) : request('/consult', 'POST', payload)
  },
  registerCustomer(payload) {
    return useMock ? mock.registerCustomer(payload) : request('/customers/register', 'POST', payload)
  },
  // 更新客户资料（小程序"我的"页编辑生日等）
  updateCustomer(customerId, payload) {
    return useMock ? mock.updateCustomer(customerId, payload) : request('/customers/' + customerId, 'PUT', payload)
  },
  // 微信静默登录（wx.login code -> openid）
  wxLogin(payload) {
    return useMock ? mock.wxLogin(payload) : request('/auth/wx-login', 'POST', payload)
  },
  // 首页 Banner 轮播
  getBanners() {
    return useMock ? mock.getBanners() : request('/banners')
  },
  // 收藏切换 / 列表
  toggleFavorite(payload) {
    return useMock ? mock.toggleFavorite(payload) : request('/favorites', 'POST', payload)
  },
  getFavorites(user_id) {
    return useMock ? mock.getFavorites(user_id) : request('/favorites?user_id=' + user_id)
  }
}

module.exports = api
