// pages/consult/consult.js
const api = require('../../utils/api')

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

  submitMsg() {
    const f = this.data.form
    if (!f.content) { wx.showToast({ title: '请填写咨询内容', icon: 'none' }); return }
    api.submitConsult(Object.assign({ channel: '在线留言', route_id: this.data.routeId }, f)).then(() => {
      wx.showToast({ title: '已提交，顾问尽快回复', icon: 'none' })
      this.setData({ form: { name: '', phone: '', content: '' } })
    })
  },

  callPhone() { wx.makePhoneCall({ phoneNumber: '4000000000' }) }
})
