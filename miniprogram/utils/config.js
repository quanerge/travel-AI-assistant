// utils/config.js
// 数据来源切换：MVP 默认使用本地 mock，便于无后端直接预览；
// 后端就绪后把 useMock 改为 false 并填写 baseUrl（需为微信合法域名）。
module.exports = {
  useMock: true,
  baseUrl: 'http://127.0.0.1:8000/api', // 模拟器联调（同机 127.0.0.1 最稳）；真机预览需改回电脑局域网 IP 并勾选"不校验合法域名"；发布时改回 https 域名
  // 订单状态字典（与后端、需求文档 7.5 一致）
  orderStatusMap: {
    pending_confirm: '待确认',
    confirmed: '已确认',
    pending_deposit: '待付定金',
    deposit_received: '定金已收',
    success: '报名成功',
    completed: '完成'
  }
}
