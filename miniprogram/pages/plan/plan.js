// pages/plan/plan.js —— MVP：智能需求提交（替代 AI 自动规划，见需求 7.3）
const api = require('../../utils/api')

const destinations = ['不限', '云南', '新疆', '西藏', '四川', '境外']
const dayOptions = ['不限', '3-5天', '6-8天', '9-15天', '15天以上']
const personOptions = ['1人', '夫妻2人', '亲子3人', '朋友4人+']
const budgetOptions = ['不限', '3000以内', '3000-6000', '6000-10000', '10000以上']
const interests = ['自然', '美食', '摄影', '亲子', '人文', '自驾']

Page({
  data: {
    destinations, dayOptions, personOptions, budgetOptions,
    interestList: interests.map(n => ({ name: n, on: false })),
    form: { destination: '不限', days: '不限', person: '夫妻2人', budget: '不限', interest: [] },
    submitted: false,
    submitting: false,
    submitCount: 0
  },

  pick(e) {
    const { field, value } = e.currentTarget.dataset
    this.setData({ ['form.' + field]: value })
  },

  toggleInterest(e) {
    const name = e.currentTarget.dataset.name
    const list = this.data.interestList.map(it =>
      it.name === name ? Object.assign({}, it, { on: !it.on }) : it
    )
    const interest = list.filter(it => it.on).map(it => it.name)
    this.setData({ interestList: list, 'form.interest': interest })
  },

  submit() {
    if (this.data.submitting) return
    const f = this.data.form
    if (f.interest.length === 0) {
      wx.showToast({ title: '请至少选择一个兴趣', icon: 'none' }); return
    }
    const content = `目的地：${f.destination}；时间：${f.days}；人数：${f.person}；预算：${f.budget}；兴趣：${f.interest.join('、')}`
    this.setData({ submitting: true })
    wx.showLoading({ title: '提交中', mask: true })
    api.submitPlan(Object.assign({ channel: '智能规划', content }, f))
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
