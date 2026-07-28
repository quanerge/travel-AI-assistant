import axios from 'axios'

// 开发：走 Vite 代理（/api -> 127.0.0.1:8000）；生产：nginx 反向代理。
const http = axios.create({ baseURL: '/api', timeout: 10000 })

// 请求拦截：携带 JWT（后端受保护接口校验 Authorization: Bearer <token>）
http.interceptors.request.use((config) => {
  const admin = JSON.parse(localStorage.getItem('admin') || 'null')
  if (admin && admin.token) config.headers['Authorization'] = 'Bearer ' + admin.token
  return config
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('admin')
      // 避免重复跳转
      if (location.hash !== '#/login') location.hash = '#/login'
    }
    return Promise.reject(err)
  }
)

export const api = {
  login: (username, password) =>
    http.post('/admin/login', { username, password }),

  dashboard: () => http.get('/admin/dashboard'),

  listRoutes: (params) => http.get('/routes', { params }),
  getRoute: (id) => http.get(`/routes/${id}`),
  createRoute: (data) => http.post('/routes', data),
  updateRoute: (id, data) => http.put(`/routes/${id}`, data),
  deleteRoute: (id) => http.delete(`/routes/${id}`),

  listOrders: (params) => http.get('/orders', { params }),
  getOrder: (id) => http.get(`/orders/${id}`),
  confirmOrder: (id) => http.post(`/orders/${id}/confirm`),
  confirmDeposit: (id) => http.post(`/orders/${id}/confirm-deposit`),
  completeOrder: (id) => http.post(`/orders/${id}/complete`),

  listBanners: () => http.get('/banners'),
  listBannersAdmin: () => http.get('/banners/admin'),
  createBanner: (data) => http.post('/banners/admin', data),
  updateBanner: (id, data) => http.put(`/banners/admin/${id}`, data),
  deleteBanner: (id) => http.delete(`/banners/admin/${id}`),

  listCustomers: (params) => http.get('/customers', { params }),
  createCustomer: (data) => http.post('/customers', data),
  updateCustomer: (id, data) => http.put(`/customers/${id}`, data),
  getFollowUps: (id) => http.get(`/customers/${id}/follow-ups`),
  addFollowUp: (id, content) => http.post(`/customers/${id}/follow-ups`, { content }),

  listConsults: () => http.get('/consult'),
  getMe: () => http.get('/auth/me'),

  // 系统设置
  getSettings: () => http.get('/admin/settings'),

  // 用户管理（仅超管）
  listUsers: () => http.get('/admin/users'),
  createUser: (data) => http.post('/admin/users', data),
  resetUserPassword: (id, password) => http.put(`/admin/users/${id}/password`, { password }),
  updateUserRole: (id, role) => http.put(`/admin/users/${id}/role`, { role }),
  updateUserStatus: (id, status) => http.put(`/admin/users/${id}/status`, { status }),
  deleteUser: (id) => http.delete(`/admin/users/${id}`)
}

export default http
