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
  // 客户删除自己的订单（软删除；管理员可在后台删任意单）
  deleteOrder(id) {
    return useMock ? mock.deleteOrder(id) : request('/orders/' + id + '/delete', 'POST', {})
  },
  submitConsult(payload) {
    return useMock ? mock.submitConsult(payload) : request('/consult', 'POST', payload)
  },
  // 小程序用户查看自己的咨询/需求单及顾问回复
  getMyConsults() {
    return useMock ? mock.getMyConsults() : request('/consult/mine')
  },
  // 当前用户「顾问已回复、未查看」的咨询数量（用于未读红点）
  getConsultUnread() {
    return useMock ? Promise.resolve({ count: 0 }) : request('/consult/unread-count')
  },
  // 客户查看方案后标记已读（消除红点）
  markConsultRead(id) {
    return useMock ? Promise.resolve({}) : request('/consult/' + id + '/read', 'POST', {})
  },
  // 软删除自己的咨询/需求单（已转订单的不允许删）
  deleteConsult(id) {
    return useMock ? mock.deleteConsult(id) : request('/consult/' + id + '/delete', 'POST', {})
  },
  // P3：小程序「对此方案下单」——把需求单一键转为订单
  toOrder(consultId, payload) {
    return useMock ? mock.toOrder(consultId, payload) : request('/consult/' + consultId + '/to-order', 'POST', payload)
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
  // 收藏切换 / 列表（身份由请求头 JWT 决定，无需传 user_id）
  toggleFavorite(payload) {
    return useMock ? mock.toggleFavorite(payload) : request('/favorites', 'POST', payload)
  },
  getFavorites() {
    return useMock ? mock.getFavorites() : request('/favorites')
  }
}

module.exports = api
