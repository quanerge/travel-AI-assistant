// utils/request.js —— wx.request Promise 封装
const { baseUrl } = require('./config')

function request(path, method = 'GET', data = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: baseUrl + path,
      method,
      data,
      header: { 'content-type': 'application/json' },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data)
        else reject(res.data || { message: '请求失败' })
      },
      fail: (err) => reject(err)
    })
  })
}

module.exports = { request }
