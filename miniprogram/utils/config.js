// utils/config.js
// 数据来源切换：useMock=false 时走真实后端（部署/联调必须用 false）；true 仅用于无后端预览。
// baseUrl 说明（微信小程序请求域名必须是 https 且已在 MP 后台配置合法域名，否则真机/发布会被拦截）：
//   - 开发者工具模拟器（与后端同机）：http://127.0.0.1:8000/api 可用（project.config.json 已设 urlCheck:false）
//   - 真机预览/调试：改成电脑局域网 IP，如 http://192.168.x.x:8000/api，并在开发者工具勾选「不校验合法域名」
//   - 正式发布：必须 https 且 ICP 备案域名，并在微信公众平台「开发-开发设置-服务器域名」配置 request 合法域名
module.exports = {
  useMock: false,
  baseUrl: 'http://10.28.100.143:8000/api', // 模拟器联调（同机 127.0.0.1 最稳）；真机预览改局域网 IP；发布改 https 域名
  // 微信订阅消息模板 ID（P2 推送用）：在微信公众平台「订阅消息」申请模板，字段需含
  // 事项(thing1)、处理人(name2)、时间(time3)。留空则提交时不请求授权、也不推送。
  subscribeTemplateId: '',
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
