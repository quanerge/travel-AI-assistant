// pages/plan/plan.js —— 智能行程规划/线路设计（MVP：需求提交，由顾问人工回执）
const api = require('../../utils/api')

// 目的地：自由输入 + 热门快捷标签（覆盖国内省份/城市与主流出境方向，可填任意目的地）
const destChips = ['云南', '新疆', '西藏', '四川', '海南', '北京', '西安', '贵州', '广西', '福建', '内蒙古', '港澳台', '日本', '东南亚', '欧洲', '澳洲']
// 预算：下拉单选（可不选，默认"不限"）
const budgetOptions = ['不限', '3000以内', '3000-6000', '6000-10000', '10000以上']
const interests = ['自然', '美食', '摄影', '亲子', '人文', '自驾']

Page({
  data: {
    budgetOptions,
    destChips,
    interestList: interests.map(n => ({ name: n, on: false })),
    // 步进器边界
    minDays: 1, maxDays: 30,
    minPerson: 1, maxPerson: 20,
    // picker 选中索引
    budgetIndex: 0,
    form: {
      destination: '',   // 空 = 未选，提交时需校验
      days: 5,            // 最少天数（数字）
      person: 2,          // 出行人数（数字）
      budget: '不限',
      interest: [],
      name: '',           // 联系人姓名（用于一键转订单，避免缺字段无法下单）
      phone: ''           // 手机号（用于一键转订单 + 方案通知）
    },
    submitted: false,
    submitting: false,
    submitCount: 0,
    aiLoading: false
  },

  // 目的地：自由输入（可填任意目的地）
  onDestInput(e) {
    this.setData({ 'form.destination': e.detail.value.trim() })
  },
  // 目的地：点选热门标签（再次点击同一项则清空，便于改为手输）
  pickDestChip(e) {
    const v = e.currentTarget.dataset.v
    this.setData({ 'form.destination': this.data.form.destination === v ? '' : v })
  },

  // 预算下拉
  onBudget(e) {
    const i = Number(e.detail.value)
    this.setData({ budgetIndex: i, 'form.budget': this.data.budgetOptions[i] })
  },

  // 最少天数步进
  stepDays(e) {
    const d = Number(e.currentTarget.dataset.d)
    const { days, minDays, maxDays } = this.data
    const next = days + d
    if (next < minDays || next > maxDays) return
    this.setData({ 'form.days': next })
  },

  // 出行人数步进
  stepPerson(e) {
    const d = Number(e.currentTarget.dataset.d)
    const { person, minPerson, maxPerson } = this.data
    const next = person + d
    if (next < minPerson || next > maxPerson) return
    this.setData({ 'form.person': next })
  },

  toggleInterest(e) {
    const name = e.currentTarget.dataset.name
    const list = this.data.interestList.map(it =>
      it.name === name ? Object.assign({}, it, { on: !it.on }) : it
    )
    const interest = list.filter(it => it.on).map(it => it.name)
    this.setData({ interestList: list, 'form.interest': interest })
  },

  // 联系人姓名
  onName(e) {
    this.setData({ 'form.name': e.detail.value })
  },

  // 手机号
  onPhone(e) {
    this.setData({ 'form.phone': e.detail.value })
  },

  submit() {
    if (this.data.submitting) return
    const f = this.data.form
    if (!f.destination) {
      wx.showToast({ title: '请选择目的地', icon: 'none' }); return
    }
    if (!f.name || !f.phone) {
      wx.showToast({ title: '请填写联系人和手机号', icon: 'none' }); return
    }
    if (!/^1\d{10}$/.test(f.phone)) {
      wx.showToast({ title: '手机号格式有误', icon: 'none' }); return
    }
    if (f.interest.length === 0) {
      wx.showToast({ title: '请至少选择一个兴趣', icon: 'none' }); return
    }
    const content = `目的地：${f.destination}；最少天数：${f.days}天；出行人数：${f.person}人；预算：${f.budget}；兴趣：${f.interest.join('、')}；联系人：${f.name}；手机：${f.phone}`
    this.setData({ submitting: true })
    wx.showLoading({ title: '提交中', mask: true })
    api.submitPlan(Object.assign({ channel: '智能规划', content, name: f.name, phone: f.phone }, f))
      .then(() => {
        wx.hideLoading()
        this.setData({ submitted: true, submitCount: this.data.submitCount + 1 })
      })
      .catch((err) => {
        wx.hideLoading()
        this.setData({ submitting: false })
        console.error('提交需求单失败', err)
        const msg = (err && err.detail) ? err.detail : (typeof err === 'string' ? err : '提交失败，请检查网络')
        wx.showModal({
          title: '提交失败',
          content: '无法连接到后端服务。\n请确认：\n1) 后端已启动（:8000 在运行）\n2) 开发者工具已勾选"不校验合法域名"\n3) 真机预览时 127.0.0.1 无法访问电脑，请用模拟器或改用电脑 IP',
          showCancel: false
        })
      })
  },

  goHome() { wx.switchTab({ url: '/pages/index/index' }) },

  // 第二阶段：AI 行程自动规划。大模型在后端调用，结果写入咨询表，
  // 小程序跳「我的咨询」查看（复用需求单闭环：行程卡片 + 方案正文 + 未读红点）。
  aiGenerate() {
    if (this.data.aiLoading) return
    const f = this.data.form
    if (!f.destination) {
      wx.showToast({ title: '请先选择目的地', icon: 'none' }); return
    }
    if (f.interest.length === 0) {
      wx.showToast({ title: '请至少选择一个兴趣', icon: 'none' }); return
    }
    this.setData({ aiLoading: true })
    wx.showLoading({ title: 'AI 规划中...', mask: true })
    api.aiPlan({
      destination: f.destination,
      days: f.days,
      people: f.person,
      budget: f.budget,
      preferences: f.interest.join('、')
    }).then((res) => {
      wx.hideLoading()
      this.setData({ aiLoading: false })
      wx.showToast({ title: '已生成，去查看', icon: 'success' })
      // 跳「我的咨询」查看 AI 方案（复用现有咨询详情渲染行程卡片）
      setTimeout(() => {
        wx.switchTab({ url: '/pages/mine/mine' })
        wx.navigateTo({ url: '/pages/myConsult/myConsult' })
      }, 600)
    }).catch((err) => {
      wx.hideLoading()
      this.setData({ aiLoading: false })
      console.error('AI 规划失败', err)
      const msg = (err && err.detail) ? err.detail : (typeof err === 'string' ? err : 'AI 规划失败，请稍后再试')
      wx.showModal({ title: 'AI 规划失败', content: String(msg), showCancel: false })
    })
  },

  // 再次提交：保留已填字段，回到表单（便于微调后补交另一份需求）
  submitAgain() {
    this.setData({ submitted: false, submitting: false })
  },
  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 })
    }
  }
})
