Component({
  data: {
    selected: 0,
    list: [
      { pagePath: '/pages/index/index', text: '首页', icon: '/images/tab/home.png', iconOn: '/images/tab/home_on.png' },
      { pagePath: '/pages/routes/routes', text: '线路', icon: '/images/tab/route.png', iconOn: '/images/tab/route_on.png' },
      { pagePath: '/pages/plan/plan', text: '智能规划', icon: '/images/tab/plan.png', iconOn: '/images/tab/plan_on.png' },
      { pagePath: '/pages/mine/mine', text: '我的', icon: '/images/tab/mine.png', iconOn: '/images/tab/mine_on.png' }
    ]
  },
  methods: {
    switchTab(e) {
      const idx = e.currentTarget.dataset.index
      const url = this.data.list[idx].pagePath
      wx.switchTab({ url })
    }
  }
})
