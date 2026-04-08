<template>
  <PanelCard>
    <h3>备份记录页面</h3>
    <input v-model="note" placeholder="备份备注" />
    <button @click="onCreateBackup">创建备份</button>
    <button class="secondary" @click="loadBackups">刷新列表</button>

    <table>
      <thead><tr><th>ID</th><th>名称</th><th>状态</th><th>备注</th><th>创建时间</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="b in backups" :key="b.id">
          <td>{{ b.id }}</td>
          <td>{{ b.backup_name }}</td>
          <td>{{ b.status }}</td>
          <td>{{ b.note }}</td>
          <td>{{ b.create_time }}</td>
          <td><button @click="onRestoreBackup(b.id)">恢复</button></td>
        </tr>
      </tbody>
    </table>
  </PanelCard>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import PanelCard from '../components/PanelCard.vue'
import { createBackup, getBackups, restoreBackup } from '../api/devops'

const note = ref('')
const backups = ref([])

async function loadBackups() {
  const res = await getBackups()
  backups.value = res.data || []
}

async function onCreateBackup() {
  await createBackup(note.value)
  note.value = ''
  await loadBackups()
}

async function onRestoreBackup(id) {
  await restoreBackup(id)
  await loadBackups()
}

onMounted(loadBackups)
</script>
