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
  },
  // 第二阶段：AI 行程自动规划（大模型在后端调用，小程序只传偏好）
  aiPlan(payload) {
    return useMock ? mock.aiPlan(payload) : request('/ai/plan', 'POST', payload)
  },
  // 优惠券：领券中心（可领模板）/ 领取 / 我的券
  getCoupons() {
    return useMock ? mock.getCoupons() : request('/coupons')
  },
  claimCoupon(id) {
    return useMock ? mock.claimCoupon(id) : request('/coupons/' + id + '/claim', 'POST', {})
  },
  getMyCoupons() {
    return useMock ? mock.getMyCoupons() : request('/coupons/mine')
  },
  // AI 多轮对话：发消息 / 会话列表 / 历史
  aiChat(payload) {
    return useMock ? mock.aiChat(payload) : request('/ai/chat', 'POST', payload)
  },
  aiConversations() {
    return useMock ? mock.getAiConversations() : request('/ai/conversations')
  },
  aiHistory(conversationId) {
    return useMock ? mock.aiHistory(conversationId) : request('/ai/chat/history?conversation_id=' + conversationId)
  },
  // 顾问联系方式（公开接口；mock 模式回退 config.js 兜底值）
  getAdvisor() {
    return useMock ? Promise.resolve(config.advisor) : request('/config/advisor')
  },
  // 会员信息（功能4：激活 member 表）；mock 模式返回普通会员默认值
  getMember() {
    if (useMock) {
      return Promise.resolve({ level: 'normal', level_name: '普通会员', points: 0, total_points: 0, rights: 'AI 行程规划 / 专属顾问咨询', is_member: false })
    }
    return request('/members/me')
  },
  // 线路评价晒图（功能①）
  getReviews(routeId, page = 1) {
    return useMock ? mock.getReviews(routeId) : request('/reviews?route_id=' + routeId + '&page=' + page)
  },
  // AI 亮点解读（公开端点：读线路缓存或即时生成并缓存，无需登录）
  getRouteHighlight(id) {
    return useMock ? Promise.resolve(null) : request('/routes/' + id + '/highlight')
  },
  submitReview(payload) {
    return useMock ? mock.submitReview(payload) : request('/reviews', 'POST', payload)
  },
  getMyReviews() {
    return useMock ? mock.getMyReviews() : request('/reviews/mine')
  },
  // 线路亮点自动分发：客户意向行为（收藏/咨询/下单）自动推送，确认接受后回写状态（顾问零操作）
  pushRecommend(routeId) {
    return useMock ? mock.pushRecommend(routeId) : request('/recommend', 'POST', { route_id: routeId })
  },
  getMyRecommends() {
    return useMock ? mock.getMyRecommends() : request('/recommend/mine')
  },
  acceptRecommend(id) {
    return useMock ? Promise.resolve({ id, status: 'accepted' }) : request('/recommend/' + id + '/accept', 'POST', {})
  },
  declineRecommend(id) {
    return useMock ? Promise.resolve({ id, status: 'declined' }) : request('/recommend/' + id + '/decline', 'POST', {})
  },
  // 晒图上传：wx.uploadFile 到用户鉴权端点；mock 模式直接返回占位图
  uploadReviewImage(filePath) {
    if (useMock) return Promise.resolve({ url: 'https://picsum.photos/seed/rv' + Date.now() + '/300/300' })
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('userToken') || ''
      wx.uploadFile({
        url: config.baseUrl + '/upload/user-image',
        filePath,
        name: 'file',
        header: token ? { Authorization: 'Bearer ' + token } : {},
        success: (res) => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try { resolve(JSON.parse(res.data)) }
            catch (e) { reject({ message: '上传结果解析失败' }) }
          } else reject({ message: '上传失败 HTTP ' + res.statusCode })
        },
        fail: (err) => reject({ message: (err && err.errMsg) || '上传失败' })
      })
    })
  }
}

module.exports = api
