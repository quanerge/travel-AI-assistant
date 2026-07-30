// pages/plan/plan.js —— 智能行程规划/线路设计（MVP：需求提交，由顾问人工回执）
const api = require('../../utils/api')

// 目的地：下拉单选（默认空，需选择）
const destinations = ['云南', '新疆', '西藏', '四川', '海南', '境外']
// 预算：下拉单选（可不选，默认"不限"）
const budgetOptions = ['不限', '3000以内', '3000-6000', '6000-10000', '10000以上']
const interests = ['自然', '美食', '摄影', '亲子', '人文', '自驾']

Page({
  data: {
    destinations, budgetOptions,
    interestList: interests.map(n => ({ name: n, on: false })),
    // 步进器边界
    minDays: 1, maxDays: 30,
    minPerson: 1, maxPerson: 20,
    // picker 选中索引
    destIndex: 0,
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
    submitCount: 0
  },

  // 目的地下拉
  onDest(e) {
    const i = Number(e.detail.value)
    this.setData({ destIndex: i, 'form.destination': this.data.destinations[i] })
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

  // 再次提交：保留已填字段，回到表单（便于微调后补交另一份需求）
  submitAgain() {
    this.setData({ submitted: false, submitting: false })
  }
})
