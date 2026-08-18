import axios from 'axios'

// 开发：走 Vite 代理（/api -> 127.0.0.1:8000）；生产：nginx 反向代理。
const http = axios.create({ baseURL: '/api', timeout: 10000 })

// 记录最近一次各列表接口返回的总条数（从响应头 X-Total-Count 读取），
// 供前端分页条渲染。保持响应拦截仍返回 res.data，避免改动其它调用方。
const _totals = {}
http.interceptors.request.use((config) => {
  const admin = JSON.parse(localStorage.getItem('admin') || 'null')
  if (admin && admin.token) config.headers['Authorization'] = 'Bearer ' + admin.token
  return config
})

http.interceptors.response.use(
  (res) => {
    const ct = res.headers['x-total-count']
    if (ct != null) _totals[res.config.url] = Number(ct)
    return res.data
  },
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('admin')
      // 避免重复跳转
      if (location.hash !== '#/login') location.hash = '#/login'
    }
    return Promise.reject(err)
  }
)

// 将前端分页参数 { page, pageSize } 映射为后端接受的 { page, page_size }
function withPage(params) {
  const p = { ...(params || {}) }
  if (p.pageSize != null) {
    p.page_size = p.pageSize
    delete p.pageSize
  }
  return p
}

// 列表接口统一返回 { rows, total }，total 取自 X-Total-Count 响应头（缺省回退数组长度）
function listRes(url, params) {
  return http.get(url, { params: withPage(params) }).then((data) => ({
    rows: data,
    total: _totals[url] != null ? _totals[url] : data.length,
  }))
}

export const api = {
  login: (username, password) =>
    http.post('/admin/login', { username, password }),

  dashboard: () => http.get('/admin/dashboard'),

  // 收益管理（统一口径：与 Dashboard 累计利润一致，支持时间范围筛选）
  getRevenue: (params) => http.get('/admin/revenue', { params }),

  listRoutes: (params) => listRes('/routes', params),
  getRoute: (id) => http.get(`/routes/${id}`),
  createRoute: (data) => http.post('/routes', data),
  updateRoute: (id, data) => http.put(`/routes/${id}`, data),
  deleteRoute: (id) => http.delete(`/routes/${id}`),

  listOrders: (params) => listRes('/orders', params),
  getOrder: (id) => http.get(`/orders/${id}`),
  deleteOrder: (id) => http.post(`/orders/${id}/delete`),
  confirmOrder: (id) => http.post(`/orders/${id}/confirm`),
  confirmDeposit: (id) => http.post(`/orders/${id}/confirm-deposit`),
  confirmBalance: (id) => http.post(`/orders/${id}/confirm-balance`),
  completeOrder: (id) => http.post(`/orders/${id}/complete`),

  listBanners: () => http.get('/banners'),
  listBannersAdmin: (params) => listRes('/banners/admin', params),
  createBanner: (data) => http.post('/banners/admin', data),
  updateBanner: (id, data) => http.put(`/banners/admin/${id}`, data),
  deleteBanner: (id) => http.delete(`/banners/admin/${id}`),

  // 优惠券（后台管理模板与发放）
  listCoupons: (params) => listRes('/coupons/admin', params),
  createCoupon: (data) => http.post('/coupons/admin', data),
  updateCoupon: (id, data) => http.put(`/coupons/admin/${id}`, data),
  deleteCoupon: (id) => http.delete(`/coupons/admin/${id}`),

  listCustomers: (params) => listRes('/customers', params),
  createCustomer: (data) => http.post('/customers', data),
  updateCustomer: (id, data) => http.put(`/customers/${id}`, data),
  getFollowUps: (id) => http.get(`/customers/${id}/follow-ups`),
  addFollowUp: (id, content) => http.post(`/customers/${id}/follow-ups`, { content }),
  deleteCustomer: (id) => http.post(`/customers/${id}/delete`),
  restoreCustomer: (id) => http.post(`/customers/${id}/restore`),
  toggleKeyCustomer: (id) => http.post(`/customers/${id}/toggle-key`),

  listConsults: (params) => listRes('/consult', params),
  updateConsult: (id, data) => http.put(`/consult/${id}`, data),
  deleteConsult: (id) => http.post(`/consult/${id}/delete`),
  getMe: () => http.get('/auth/me'),

  // 评价管理（功能①收尾：全站查看 / 审核 / 下架 / 删除）
  listReviewsAdmin: (params) => listRes('/reviews/admin', params),
  updateReviewStatus: (id, status) => http.post(`/reviews/${id}/status`, { status }),

  // 后端应用版本（公开接口，无需登录；用于管理后台左侧版本号展示）
  getVersion: () => http.get('/version'),

  // 客服消息回传（微信客服 → 管理后台）
  chatSessions: () => http.get('/admin/chat/sessions'),
  chatMessages: (openid) => http.get('/admin/chat/messages', { params: { openid } }),
  chatReply: (openid, content) => http.post('/admin/chat/reply', { openid, content }),
  chatRead: (openid) => http.post('/admin/chat/read', { openid }),

  // 系统设置
  getSettings: () => http.get('/admin/settings'),

  // AI 智能提取（线路管理「粘贴自动填充」）
  aiExtract: (text) => http.post('/ai/extract', { text }),

  // AI 线路亮点介绍（顾问为客户选定线路后生成可发送的亮点/景点/美食/风光）
  aiRouteHighlight: (payload) => http.post('/ai/route-highlight', payload),

  // 批量亮点群发：对一批客户就同一条线路各自生成个性化介绍（返回每条可发送全文）
  aiRouteHighlightBatch: (payload) => http.post('/ai/route-highlight/batch', payload),

  // 客户意向（线路亮点自动分发）：顾问零操作查看谁接受了推荐
  listRecommendAdmin: (params) => listRes('/recommend/admin', params),

  // 用户管理（仅超管）
  listUsers: (params) => listRes('/admin/users', params),
  createUser: (data) => http.post('/admin/users', data),
  resetUserPassword: (id, password) => http.put(`/admin/users/${id}/password`, { password }),
  updateUserRole: (id, role) => http.put(`/admin/users/${id}/role`, { role }),
  updateUserStatus: (id, status) => http.put(`/admin/users/${id}/status`, { status }),
  deleteUser: (id) => http.delete(`/admin/users/${id}`)
}

export default http
