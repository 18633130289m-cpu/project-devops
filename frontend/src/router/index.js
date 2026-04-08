import { createRouter, createWebHistory } from 'vue-router'

import ManageView from '../views/ManageView.vue'
import MonitorView from '../views/MonitorView.vue'
import BackupView from '../views/BackupView.vue'
import LogsView from '../views/LogsView.vue'

// 页面路由：默认跳转到管理页，便于首次使用。
export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/manage' },
    { path: '/manage', component: ManageView },
    { path: '/monitor', component: MonitorView },
    { path: '/backup', component: BackupView },
    { path: '/logs', component: LogsView },
  ],
})
