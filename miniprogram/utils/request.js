// utils/request.js —— wx.request Promise 封装
const { baseUrl } = require('./config')

function request(path, method = 'GET', data = {}) {
  const token = wx.getStorageSync('userToken') || ''
  const header = { 'content-type': 'application/json' }
  // 携带小程序用户 JWT（若已登录），后端据此鉴权并定位用户身份
  if (token) header['Authorization'] = 'Bearer ' + token
  return new Promise((resolve, reject) => {
    wx.request({
      url: baseUrl + path,
      method,
      data,
      header,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data)
        else reject(res.data || { message: '请求失败' })
      },
      fail: (err) => reject(err)
    })
  })
}

module.exports = { request }
