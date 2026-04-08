import { createRouter, createWebHistory } from 'vue-router'

import ManageView from '../views/ManageView.vue'
import MonitorView from '../views/MonitorView.vue'
import BackupView from '../views/BackupView.vue'
import LogsView from '../views/LogsView.vue'

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
