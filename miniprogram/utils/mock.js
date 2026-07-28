// utils/mock.js —— MVP 本地演示数据（与需求文档 7.2 / 7.3 示例一致）
const routes = [
  {
    id: 1, name: '云南8日深度游', category: '国内游', cover: 'https://picsum.photos/seed/yunnan/400/300',
    days: 8, departure: '上海', destination: '云南', price: 2999,
    rating: 4.9, signup_count: 18, group_size: 20,
    description: '大理丽江香格里拉，慢节奏深度体验。',
    gallery: [], route_days: [
      { day_no: 1, title: '抵达大理', content: '接机，入住洱海民宿', meals: '晚', accommodation: '洱海民宿', traffic: '飞机' },
      { day_no: 2, title: '洱海环湖', content: '骑行环海，双廊古镇', meals: '早/晚', accommodation: '洱海民宿', traffic: '商务车' }
    ],
    fee_included: '住宿、门票、当地交通、部分餐食',
    fee_excluded: '往返大交通、个人消费',
    notice: '高原注意防晒，建议提前 15 天报名。'
  },
  {
    id: 2, name: '新疆15日深度游', category: '国内游', cover: 'https://picsum.photos/seed/xinjiang/400/300',
    days: 15, departure: '上海', destination: '新疆', price: 3999,
    rating: 4.8, signup_count: 28, group_size: 20,
    description: '天山南北大环线，一次看遍雪山湖泊沙漠。',
    gallery: [], route_days: [
      { day_no: 1, title: '乌鲁木齐', content: '集合日，自由活动', meals: '无', accommodation: '乌市四星', traffic: '飞机' },
      { day_no: 2, title: '天山天池', content: '天池景区，雪山倒影', meals: '早/晚', accommodation: '乌市四星', traffic: '大巴' }
    ],
    fee_included: '住宿、门票、用车、导游',
    fee_excluded: '往返大交通、午餐、自费项目',
    notice: '新疆与内地有 2 小时时差，行程宽松安排。'
  },
  {
    id: 3, name: '川西自驾7日', category: '短途游', cover: 'https://picsum.photos/seed/sichuan/400/300',
    days: 7, departure: '成都', destination: '川西', price: 2680,
    rating: 4.7, signup_count: 12, group_size: 15,
    description: '色达稻城亚丁，自驾摄影天堂。',
    gallery: [], route_days: [
      { day_no: 1, title: '成都集合', content: '租车，行前说明', meals: '晚', accommodation: '成都', traffic: '自驾' }
    ],
    fee_included: '领队、住宿、保险',
    fee_excluded: '车辆油费、门票、餐食',
    notice: '高原路段，需备红景天。'
  }
]

const banners = [
  { id: 1, image: 'https://picsum.photos/seed/yunnan/600/300', title: '云南8日深度游', routeId: 1 },
  { id: 2, image: 'https://picsum.photos/seed/xinjiang/600/300', title: '新疆15日深度游', routeId: 2 },
  { id: 3, image: 'https://picsum.photos/seed/sichuan/600/300', title: '川西自驾7日', routeId: 3 }
]

let orderSeq = 1000
const orders = []
const favSet = new Set()  // key: `${user_id}:${route_id}`
// 本地记忆已注册客户：模拟后端把客户与微信 openid 绑定（实现退出后自动恢复）
const mockCustomers = []  // { userId, customerId, nickName, phone, openid }

function getRoutes() { return Promise.resolve(routes) }
function getRouteDetail(id) {
  return Promise.resolve(routes.find(r => r.id === Number(id)) || null)
}
function getBanners() { return Promise.resolve(banners) }
function submitSignup(payload) {
  const route = routes.find(r => r.id === Number(payload.route_id))
  const total = route ? route.price * (payload.person_count || 1) : null
  const o = Object.assign({ id: ++orderSeq, order_no: 'NO' + Date.now(), status: 'pending_confirm', deposit_paid: false, total_amount: total }, payload)
  orders.push(o)
  return Promise.resolve(o)
}
function submitPlan(payload) {
  const c = Object.assign({ id: ++orderSeq, channel: '智能需求单', status: 'pending_confirm', content: JSON.stringify(payload) }, payload)
  return Promise.resolve(c)
}
function getOrders() { return Promise.resolve(orders) }
function getOrderDetail(id) {
  return Promise.resolve(orders.find(o => o.id === Number(id)) || null)
}
function submitConsult(payload) {
  return Promise.resolve(Object.assign({ id: ++orderSeq, status: 'pending_confirm' }, payload))
}
function registerCustomer(payload) {
  const openid = payload.openid || ''
  // 按手机号或 openid 去重，模拟幂等注册
  let c = mockCustomers.find(x => (payload.phone && x.phone === payload.phone) || (openid && x.openid === openid))
  if (c) {
    return Promise.resolve({ userId: c.userId, customerId: c.customerId, nickName: c.nickName, phone: c.phone, birthday: c.birthday, wechat_no: c.wechat_no, already_registered: true })
  }
  c = {
    userId: mockCustomers.length + 1,
    customerId: mockCustomers.length + 1,
    nickName: payload.nickname || '新客户',
    phone: payload.phone || '',
    openid: openid,
    birthday: payload.birthday || '',
    wechat_no: payload.wechat_no || ''
  }
  mockCustomers.push(c)
  return Promise.resolve({ userId: c.userId, customerId: c.customerId, nickName: c.nickName, phone: c.phone, birthday: c.birthday, wechat_no: c.wechat_no, already_registered: false })
}
function wxLogin(payload) {
  const openid = payload.openid || payload.code
  // 若此微信身份已注册过客户，返回客户信息，前端据此自动恢复登录态
  const c = mockCustomers.find(x => x.openid && x.openid === openid)
  if (c) {
    return Promise.resolve({ userId: c.userId, openid: openid, customer_id: c.customerId, nickname: c.nickName, phone: c.phone, birthday: c.birthday, wechat_no: c.wechat_no })
  }
  return Promise.resolve({ userId: 1, openid: openid })
}
// 小程序"我的"页编辑资料（如生日/手机/微信）：按 customerId 更新本地记忆
function updateCustomer(customerId, payload) {
  const c = mockCustomers.find(x => x.customerId === Number(customerId))
  if (c) {
    if (payload.birthday !== undefined) c.birthday = payload.birthday
    if (payload.wechat_no !== undefined) c.wechat_no = payload.wechat_no
    if (payload.phone !== undefined) c.phone = payload.phone
    if (payload.name !== undefined) c.nickName = payload.name
  }
  const out = c || {}
  return Promise.resolve({
    customerId: customerId,
    birthday: payload.birthday !== undefined ? payload.birthday : (out.birthday || ''),
    wechat_no: payload.wechat_no !== undefined ? payload.wechat_no : (out.wechat_no || ''),
    phone: payload.phone !== undefined ? payload.phone : (out.phone || ''),
    name: payload.name !== undefined ? payload.name : (out.nickName || '')
  })
}
function toggleFavorite(payload) {
  const key = String(payload.route_id)
  let favorited
  if (favSet.has(key)) { favSet.delete(key); favorited = false }
  else { favSet.add(key); favorited = true }
  return Promise.resolve({ favorited })
}
function getFavorites() {
  const ids = [...favSet].map(k => Number(k))
  return Promise.resolve(routes.filter(r => ids.indexOf(r.id) >= 0))
}

module.exports = {
  getRoutes, getRouteDetail, getBanners, submitSignup, submitPlan,
  getOrders, getOrderDetail, submitConsult, registerCustomer,
  wxLogin, updateCustomer, toggleFavorite, getFavorites, routes
}
