import { createRouter, createWebHashHistory } from 'vue-router'
import { auth } from '../store/auth'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  {
    path: '/',
    component: () => import('../layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '数据看板' } },
      { path: 'routes', name: 'Routes', component: () => import('../views/Routes.vue'), meta: { title: '线路管理' } },
      { path: 'orders', name: 'Orders', component: () => import('../views/Orders.vue'), meta: { title: '订单管理' } },
      { path: 'customers', name: 'Customers', component: () => import('../views/Customers.vue'), meta: { title: '客户 CRM' } },
      { path: 'revenue', name: 'Revenue', component: () => import('../views/Revenue.vue'), meta: { title: '收益管理' } },
      { path: 'banners', name: 'Banners', component: () => import('../views/Banners.vue'), meta: { title: 'Banner 管理' } },
      { path: 'coupons', name: 'Coupons', component: () => import('../views/Coupons.vue'), meta: { title: '优惠券' } },
      { path: 'consults', name: 'Consults', component: () => import('../views/Consults.vue'), meta: { title: '智能需求单' } },
      { path: 'reviews', name: 'Reviews', component: () => import('../views/ReviewManage.vue'), meta: { title: '评价管理' } },
      { path: 'users', name: 'Users', component: () => import('../views/Users.vue'), meta: { title: '用户管理' } },
      { path: 'settings', name: 'Settings', component: () => import('../views/Settings.vue'), meta: { title: '系统设置' } },
      { path: 'chat', name: 'Chat', component: () => import('../views/Chat.vue'), meta: { title: '客服消息' } }
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 路由守卫：未登录跳登录页
router.beforeEach((to) => {
  if (to.path !== '/login' && !auth.isLogin()) {
    return '/login'
  }
  if (to.path === '/login' && auth.isLogin()) {
    return '/'
  }
})

export default router
