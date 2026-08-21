// utils/config.js
// 数据来源切换：useMock=false 时走真实后端（部署/联调必须用 false）；true 仅用于无后端预览。
// baseUrl 说明（微信小程序请求域名必须是 https 且已在 MP 后台配置合法域名，否则真机/发布会被拦截）：
//   - 开发者工具模拟器（与后端同机）：http://127.0.0.1:8000/api 可用（project.config.json 已设 urlCheck:false）
//   - 真机预览/调试：改成电脑局域网 IP，如 http://192.168.x.x:8000/api，并在开发者工具勾选「不校验合法域名」
//   - 正式发布：必须 https 且 ICP 备案域名，并在微信公众平台「开发-开发设置-服务器域名」配置 request 合法域名
module.exports = {
  useMock: false,
  // ⚠️ 必须与「管理后台 CRM 后端」地址完全一致！否则小程序注册发到别的库 → CRM 查不到；连不到后端则注册直接失败。
  //   这个地址 = 你打开 CRM 后台时后端实际所在的 host（看浏览器地址栏/网络请求）。本项目后端实际部署在 10.28.100.143。
  //     - 真机预览/调试（手机扫码）：必须用电脑局域网 IP，如下的 10.28.100.143；⚠️ 绝不能填 127.0.0.1（真机上它指向手机自己，连不到电脑后端 → 注册失败）。
  //     - 开发者工具模拟器（与后端同机）：可用 http://127.0.0.1:8000/api；
  //     - 正式发布：必须 https + ICP 备案域名，并在微信公众平台「开发设置-服务器域名」配置 request 合法域名。
  //   判断口诀：CRM 后台后端在哪个地址，这里就填哪个（结尾带 /api）。两边不一致是「注册失败 / CRM 看不到」的头号原因。
  baseUrl: 'https://hitting-artificial-addresses-rounds.trycloudflare.com/api',  // ⚠️临时开发隧道(Cloudflare Quick Tunnel)->本地8000；URL每次重启随机，过期需重跑 start_tunnel.bat 并改回此处。正式发布改回已备案 https 域名。
  // 微信订阅消息模板 ID（P2 推送用）：在微信公众平台「订阅消息」申请模板，字段需含
  // 事项(thing1)、处理人(name2)、时间(time3)。留空则提交时不请求授权、也不推送。
  subscribeTemplateId: '',
  // 顾问联系方式（前端兜底；若后端 /api/config/advisor 已配置则以其为准，启动时自动拉取）
  // ⚠️ 把下面的值替换成你的真实顾问信息（phone 必须是纯数字，wx.makePhoneCall 才能拨通）
  advisor: {
    name: '小旅顾问',
    phone: '',            // 真实手机号，如 '13800000000'
    wechat: '',           // 真实微信号
    avatar: '',
    intro: '资深旅游顾问，提供一对一行程规划与报名服务',
    worktime: '9:00 - 21:00'
  },
  // 订单状态字典（与后端、需求文档 7.5 一致）
  orderStatusMap: {
    pending_confirm: '待确认',
    confirmed: '已确认',
    pending_deposit: '待付定金',
    deposit_received: '定金已收',
    balance_pending: '待付尾款',
    success: '报名成功',
    completed: '完成'
  }
}
