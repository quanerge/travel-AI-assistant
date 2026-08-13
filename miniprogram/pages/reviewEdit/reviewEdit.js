// pages/reviewEdit/reviewEdit.js —— 写评价（功能①评价晒图）
const api = require('../../utils/api')
const app = getApp()
const { resolveCover } = require('../../utils/cover')

Page({
  data: {
    routeId: null,
    rating: 5,
    content: '',
    images: [],     // 提交给后端的相对路径（/static/reviews/...）
    previews: []    // 编辑器内预览用的完整地址（已补 baseUrl 前缀）
  },

  onLoad(options) {
    this.setData({ routeId: options.routeId ? Number(options.routeId) : null })
    const uid = app.globalData.userId
    if (!uid) {
      wx.showToast({ title: '请先登录', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
    }
  },

  setRating(e) {
    this.setData({ rating: Number(e.currentTarget.dataset.v) })
  },

  onContent(e) {
    this.setData({ content: e.detail.value })
  },

  chooseImage() {
    const remain = 3 - this.data.images.length
    if (remain <= 0) return
    wx.chooseImage({
      count: remain,
      sourceType: ['album', 'camera'],
      success: (res) => {
        const files = res.tempFilePaths
        wx.showLoading({ title: '上传中' })
        Promise.all(files.map(f => api.uploadReviewImage(f)))
          .then(results => {
            wx.hideLoading()
            const urls = results.map(r => r.url)
            const previews = results.map(r => resolveCover(r.url))
            this.setData({
              images: this.data.images.concat(urls),
              previews: this.data.previews.concat(previews)
            })
          })
          .catch(() => {
            wx.hideLoading()
            wx.showToast({ title: '图片上传失败', icon: 'none' })
          })
      }
    })
  },

  submit() {
    if (!this.data.routeId) { wx.showToast({ title: '缺少线路信息', icon: 'none' }); return }
    wx.showLoading({ title: '提交中' })
    api.submitReview({
      route_id: this.data.routeId,
      rating: this.data.rating,
      content: this.data.content,
      images: this.data.images
    }).then(() => {
      wx.hideLoading()
      wx.showToast({ title: '评价成功', icon: 'success' })
      setTimeout(() => wx.navigateBack(), 800)
    }).catch(() => {
      wx.hideLoading()
      wx.showToast({ title: '提交失败，请重试', icon: 'none' })
    })
  }
})
