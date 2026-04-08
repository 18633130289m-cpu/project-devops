import { defineStore } from 'pinia'

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
