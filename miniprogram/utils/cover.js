// utils/cover.js
// 统一处理封面图地址，使「后端本地上传的 /static/... 资源」在小程序里也能显示：
//   - 完整 http(s) 外链：原样返回
//   - /images/...：小程序安装包内的本地示例图，原样返回（不补前缀）
//   - 其它以 / 开头的相对路径（如 /static/covers/xxx.jpg）：补上后端地址前缀
//   - 空值：返回空串（页面会回退到文字占位 / 目的地兜底图）
const config = require('./config')
const IMG_BASE = config.baseUrl.replace(/\/api\/?$/, '') // http://127.0.0.1:8000

function resolveCover(cover) {
  if (!cover) return ''
  if (/^https?:\/\//.test(cover)) return cover
  if (cover.indexOf('/images/') === 0) return cover
  if (cover.indexOf('/') === 0) return IMG_BASE + cover
  return cover
}

module.exports = { resolveCover, IMG_BASE }
