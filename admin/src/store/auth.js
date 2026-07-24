// 极简登录态管理：登录信息存 localStorage，避免引入 Pinia 增加依赖。
export const auth = {
  get() {
    return JSON.parse(localStorage.getItem('admin') || 'null')
  },
  set(admin) {
    localStorage.setItem('admin', JSON.stringify(admin))
  },
  clear() {
    localStorage.removeItem('admin')
  },
  isLogin() {
    return !!this.get()
  }
}
