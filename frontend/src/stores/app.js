import { defineStore } from 'pinia'

// 全局状态：跨页面共享服务健康状态。
export const useAppStore = defineStore('app', {
  state: () => ({
    healthOk: false,
    lastHealth: null,
  }),
  actions: {
    setHealth(payload) {
      this.lastHealth = payload
      this.healthOk = payload?.mysql === 'connected' && payload?.redis === 'connected'
    },
  },
})
