import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './styles.css'

// Vue 应用挂载入口：统一注册状态管理与路由。
const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
