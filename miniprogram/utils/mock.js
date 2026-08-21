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
function deleteOrder(id) {
  return Promise.resolve({ id, is_deleted: true })
}
function submitConsult(payload) {
  return Promise.resolve(Object.assign({ id: ++orderSeq, status: 'pending_confirm' }, payload))
}
function getMyConsults() {
  // 演示用：带一条已回复、含附件与行程卡片的需求单，便于预览 P2/P3 效果
  return Promise.resolve([
    {
      id: 1, channel: '智能需求单', status: 'replied',
      name: '张女士', phone: '13800001111',
      content: '想带父母去云南，7 天左右，节奏慢一点，预算 3000/人。',
      route_name: '云南8日深度游',
      reply_content: '已为您定制大理+丽江慢节奏 8 日方案，含洱海民宿与玉龙雪山，详见行程卡片与附件报价单。',
      reply_at: '2026-07-29 10:20', customer_read_at: null, created_at: '2026-07-28 21:05',
      attachments: ['https://picsum.photos/seed/quote1/600/400', 'https://picsum.photos/seed/quote2/600/400'],
      itinerary: [
        { day: 1, title: '抵达大理', desc: '专车接机，入住洱海民宿，自由漫步双廊。' },
        { day: 2, title: '洱海环湖', desc: '骑行环海，打卡小普陀，含早晚餐。' },
        { day: 3, title: '前往丽江', desc: '动车至丽江，游览古城，晚上观赏《丽江千古情》。' }
      ]
    }
  ])
}
function getConsultUnread() {
  return Promise.resolve({ count: 1 })
}
function markConsultRead() {
  return Promise.resolve({})
}
function deleteConsult(id) {
  return Promise.resolve({ id, is_deleted: true })
}
function toOrder(consultId, payload) {
  return Promise.resolve({ id: ++orderSeq, order_no: 'NO' + Date.now(), status: 'pending_confirm', route_id: 1, name: '张女士', phone: '13800001111', person_count: payload && payload.person_count || 2, total_amount: 5998 })
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

// 微信手机号一键注册（演示模式）：无真实手机号，造一条占位档案供 UI 联调
function wxPhoneRegister(payload) {
  const openid = payload.openid || payload.code || ('mock_' + Date.now())
  const phone = '13800000000'
  let c = mockCustomers.find(x => x.openid && x.openid === openid)
  if (c) {
    return Promise.resolve({ userId: c.userId, customer_id: c.customerId, nickname: c.nickName, phone: c.phone, birthday: c.birthday, wechat_no: c.wechat_no, already_registered: true })
  }
  c = { userId: mockCustomers.length + 1, customerId: mockCustomers.length + 1, nickName: '微信用户', phone: phone, birthday: null, wechat_no: null, openid }
  mockCustomers.push(c)
  return Promise.resolve({ userId: c.userId, customer_id: c.customerId, nickname: c.nickName, phone: c.phone, birthday: c.birthday, wechat_no: c.wechat_no, already_registered: false })
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

// ---- 优惠券演示数据（最小闭环）----
const coupons = [
  { id: 1, code: 'CP2026NEW', title: '新客立减 200', amount: 200, condition: '满3000可用', applicable: 'all', expire_at: '2026-12-31T23:59:59', status: 'active' },
  { id: 2, code: 'CPSUMMER', title: '夏季专线立减 300', amount: 300, condition: '满5000可用', applicable: 'all', expire_at: '2026-09-30T23:59:59', status: 'active' }
]
const myCoupons = []  // 用户已领取的券（演示内存）
function getCoupons() {
  return Promise.resolve(coupons.filter(c => c.status === 'active').map(c =>
    Object.assign({}, c, { claimed: !!myCoupons.find(m => m.code === c.code) })
  ))
}
function claimCoupon(id) {
  const t = coupons.find(c => c.id === Number(id))
  if (!t) return Promise.resolve({ id: 0 })
  const owned = myCoupons.find(c => c.code === t.code)
  if (owned) return Promise.resolve(owned)
  const c = Object.assign({ id: 1000 + myCoupons.length + 1, user_id: 1, status: 'unused' }, t)
  myCoupons.push(c)
  return Promise.resolve(c)
}
function getMyCoupons() { return Promise.resolve(myCoupons) }

// ---- AI 多轮对话演示（最小闭环，无真实大模型）----
const aiConversations = []
const aiMessages = []   // { conversation_id, role, content }
let aiConvSeq = 1
function aiChat(payload) {
  const msg = payload.message || ''
  let convId = payload.conversation_id
  if (!convId) {
    convId = aiConvSeq++
    aiConversations.push({ id: convId, title: msg.slice(0, 20), created_at: new Date().toISOString(), updated_at: new Date().toISOString() })
  }
  aiMessages.push({ conversation_id: convId, role: 'user', content: msg })
  const reply = '【演示模式】关于「' + msg + '」：建议先确认出行人数、天数与预算，再结合现有云南/新疆/川西线路做规划；如需精确报价或签证/机票代订，可转人工顾问。'
  aiMessages.push({ conversation_id: convId, role: 'assistant', content: reply })
  return Promise.resolve({ conversation_id: convId, reply, disclaimer: '以上为 AI 建议，仅供参考。' })
}
function getAiConversations() { return Promise.resolve(aiConversations) }
function aiHistory(conversationId) {
  return Promise.resolve(aiMessages.filter(m => m.conversation_id === Number(conversationId)))
}

// ---- 线路评价晒图演示（功能①）----
const reviews = [
  { id: 1, user_id: 1, route_id: 1, rating: 5, content: '行程安排很合理，导游专业，爸妈玩得特别开心！', images: ['https://picsum.photos/seed/rv1/300/300'], nickname: '李阿姨', avatar: '', created_at: '2026-07-20 10:00' },
  { id: 2, user_id: 2, route_id: 1, rating: 4, content: '洱海很美，就是最后一天行程稍微有点赶。', images: ['https://picsum.photos/seed/rv2/300/300', 'https://picsum.photos/seed/rv3/300/300'], nickname: '王先生', avatar: '', created_at: '2026-07-18 15:30' },
  { id: 3, user_id: 3, route_id: 2, rating: 5, content: '新疆太壮观了，物超所值，下次还来。', images: [], nickname: '赵女士', avatar: '', created_at: '2026-07-10 09:00' }
]
function getReviews(routeId) {
  const list = reviews.filter(r => r.route_id === Number(routeId))
  const avg = list.length ? list.reduce((s, r) => s + r.rating, 0) / list.length : 0
  return Promise.resolve({ total: list.length, avg_rating: Math.round(avg * 10) / 10, page: 1, size: 10, items: list })
}
function submitReview(payload) {
  const r = Object.assign({ id: reviews.length + 1, user_id: 1, nickname: '我', avatar: '', status: 'approved', created_at: new Date().toISOString() }, payload)
  reviews.unshift(r)
  return Promise.resolve(r)
}
function getMyReviews() {
  return Promise.resolve({ total: 0, page: 1, size: 10, items: [] })
}

// ---- 线路亮点自动分发（顾问零操作闭环）----
const recommends = [
  {
    id: 1, route_id: 1, route_name: '云南8日深度游', route_cover: 'https://picsum.photos/seed/yunnan/400/300',
    route_days: 8, route_price: 2999, route_destination: '云南', status: 'pending',
    highlight: {
      overview: '大理丽江香格里拉慢节奏深度游，适合带父母同行的轻松线路。',
      must_see: ['洱海双廊', '玉龙雪山', '丽江古城', '香格里拉普达措'],
      food: ['过桥米线', '野生菌火锅', '汽锅鸡'],
      scenery: ['洱海日出', '雪山倒影', '虎跳峡'],
      tips: ['高原注意防晒', '建议提前15天报名', '带好保暖衣物']
    },
    created_at: '2026-08-10 09:00'
  },
  {
    id: 2, route_id: 2, route_name: '新疆15日深度游', route_cover: 'https://picsum.photos/seed/xinjiang/400/300',
    route_days: 15, route_price: 3999, route_destination: '新疆', status: 'accepted',
    highlight: {
      overview: '天山南北大环线，一次看遍雪山湖泊沙漠，适合摄影与自驾爱好者。',
      must_see: ['天山天池', '喀纳斯', '禾木村', '赛里木湖'],
      food: ['大盘鸡', '手抓饭', '烤包子'],
      scenery: ['喀纳斯秋色', '禾木晨雾', '赛里木湖蓝'],
      tips: ['与内地2小时时差', '昼夜温差大', '备好防晒']
    },
    created_at: '2026-08-08 14:00', accepted_at: '2026-08-09 10:30'
  }
]
function pushRecommend(routeId) {
  // 幂等：同线路只保留一条 pending
  let rec = recommends.find(r => r.route_id === Number(routeId) && r.status !== 'declined')
  if (!rec) {
    const route = routes.find(r => r.id === Number(routeId))
    rec = {
      id: recommends.length + 1, route_id: Number(routeId),
      route_name: route ? route.name : '精选线路',
      route_cover: route ? route.cover : '', route_days: route ? route.days : 0,
      route_price: route ? route.price : 0, route_destination: route ? route.destination : '',
      status: 'pending',
      highlight: {
        overview: (route ? route.description : '') || '为您精选的线路，详情可咨询顾问。',
        must_see: (route && route.route_days || []).slice(0, 4).map(d => '第' + d.day_no + '天 ' + d.title),
        food: ['当地特色餐'], scenery: [route ? route.destination + '风光' : '自然人文风光'],
        tips: ['具体行程与价格以顾问确认方案为准']
      },
      created_at: new Date().toISOString().slice(0, 16).replace('T', ' ')
    }
    recommends.push(rec)
  }
  return Promise.resolve(rec)
}
function getMyRecommends() {
  return Promise.resolve(recommends.filter(r => r.status !== 'declined'))
}

module.exports = {
  getRoutes, getRouteDetail, getBanners, submitSignup, submitPlan,
  getOrders, getOrderDetail, deleteOrder, submitConsult, registerCustomer,
  wxLogin, wxPhoneRegister, updateCustomer, toggleFavorite, getFavorites, routes,
  getMyConsults, getConsultUnread, markConsultRead, toOrder, deleteConsult,
  getCoupons, claimCoupon, getMyCoupons,
  aiChat, getAiConversations, aiHistory,
  getReviews, submitReview, getMyReviews,
  pushRecommend, getMyRecommends
}
