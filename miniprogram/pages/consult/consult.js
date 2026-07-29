// pages/consult/consult.js
const api = require('../../utils/api')
const config = require('../../utils/config')

const faqs = [
  { q: '多少钱？', a: '线路价格见详情页，含/不含项已明确标注。' },
  { q: '什么时候出发？', a: '固定团期或私人定制日期，报名时选择出发日期。' },
  { q: '包含哪些费用？', a: '详见每条线路的「费用说明」。' },
  { q: '几个人成团？', a: '每条线路标注成团人数，达到即发团。' }
]

Page({
  data: { faqs, open: -1, form: { name: '', phone: '', content: '' }, routeId: null },

  onLoad(options) {
    if (options.routeId) this.setData({ routeId: options.routeId })
  },

  toggle(e) {
    const i = e.currentTarget.dataset.i
    this.setData({ open: this.data.open === i ? -1 : i })
  },

  input(e) {
    const f = e.currentTarget.dataset.field
    this.setData({ ['form.' + f]: e.detail.value })
  },

  // P2：提交前请求一次性订阅消息授权，便于顾问回复时微信推送通知（用户可拒，不影响提交）
  _requestSubscribe() {
    const tmpl = config.subscribeTemplateId
    if (!tmpl) return
    wx.requestSubscribeMessage({
      tmplIds: [tmpl],
      fail: () => {}  // 用户拒绝时静默：仍按「我的咨询」站内红点触达
    })
  },

  submitMsg() {
    const f = this.data.form
    if (!f.content) { wx.showToast({ title: '请填写咨询内容', icon: 'none' }); return }
    // 请求授权（异步，不阻塞提交）
    this._requestSubscribe()
    api.submitConsult(Object.assign({ channel: '在线留言', route_id: this.data.routeId }, f)).then(() => {
      wx.showToast({ title: '已提交，顾问尽快回复', icon: 'none' })
      this.setData({ form: { name: '', phone: '', content: '' } })
      // 跳转「我的咨询」，便于用户后续查看顾问方案
      wx.navigateTo({ url: '/pages/myConsult/myConsult' })
    })
  },

  callPhone() { wx.makePhoneCall({ phoneNumber: '4000000000' }) }
})
