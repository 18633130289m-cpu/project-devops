<template>
  <PanelCard>
    <h3>日志查看页面</h3>
    <select v-model="filename">
      <option value="access.log">access.log</option>
      <option value="error.log">error.log</option>
    </select>
    <input v-model="limit" placeholder="行数" style="width: 90px" />
    <button @click="loadLogs">读取日志</button>
    <pre>{{ lines.join('\n') }}</pre>
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'

import PanelCard from '../components/PanelCard.vue'
import { getLogs } from '../api/devops'

const filename = ref('access.log')
const limit = ref(200)
const lines = ref([])

// 按文件名和行数读取后端日志内容。
async function loadLogs() {
  const res = await getLogs(filename.value, limit.value)
  lines.value = res.lines || []
}
</script>
