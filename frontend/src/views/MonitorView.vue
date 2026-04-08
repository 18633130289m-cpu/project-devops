<template>
  <PanelCard>
    <h3>监控面板</h3>
    <button @click="loadMetrics">刷新监控</button>
    <button class="secondary" @click="loadHealth">健康检查</button>

    <div class="grid" style="margin-top: 10px">
      <div class="card">CPU 负载: {{ metrics.cpu_load ?? '-' }}</div>
      <div class="card">内存占用: {{ metrics.memory_used_percent ?? '-' }}%</div>
      <div class="card">磁盘占用: {{ metrics.disk_used_percent ?? '-' }}%</div>
      <div class="card">
        服务状态:
        <span :class="store.healthOk ? 'ok' : 'warn'">{{ store.healthOk ? 'OK' : 'DEGRADED' }}</span>
      </div>
    </div>

    <h4>历史记录</h4>
    <table>
      <thead><tr><th>CPU</th><th>MEM%</th><th>DISK%</th><th>状态</th><th>时间</th></tr></thead>
      <tbody>
        <tr v-for="r in history" :key="`${r.create_time}-${r.cpu_load}`">
          <td>{{ r.cpu_load }}</td><td>{{ r.memory_used_percent }}</td><td>{{ r.disk_used_percent }}</td><td>{{ r.service_status }}</td><td>{{ r.create_time }}</td>
        </tr>
      </tbody>
    </table>
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'

import PanelCard from '../components/PanelCard.vue'
import { getHealth, getMetrics } from '../api/devops'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const metrics = ref({})
const history = ref([])

// 刷新监控快照与历史表。
async function loadMetrics() {
  const res = await getMetrics()
  metrics.value = res.current || {}
  history.value = res.history || []
}

// 独立健康检查，结果写入 Pinia。
async function loadHealth() {
  const res = await getHealth()
  store.setHealth(res)
}
</script>
