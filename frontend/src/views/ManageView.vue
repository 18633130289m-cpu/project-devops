<template>
  <PanelCard>
    <h3>留言管理</h3>
    <input v-model="messageContent" placeholder="输入留言内容" />
    <button @click="onCreateMessage">发布留言</button>

    <div style="margin-top: 10px">
      <input v-model="query.keyword" placeholder="关键词" />
      <input v-model="query.start_time" placeholder="开始时间 2026-04-01 00:00:00" />
      <input v-model="query.end_time" placeholder="结束时间 2026-04-30 23:59:59" />
      <input v-model="query.limit" placeholder="条数" style="width: 90px" />
      <button class="secondary" @click="loadMessages">查询</button>
    </div>
    <p class="muted">数据来源：{{ messageSource }}</p>

    <table>
      <thead><tr><th>ID</th><th>内容</th><th>时间</th></tr></thead>
      <tbody>
        <tr v-for="m in messages" :key="m.id">
          <td>{{ m.id }}</td>
          <td>{{ m.content }}</td>
          <td>{{ m.create_time }}</td>
        </tr>
      </tbody>
    </table>
  </PanelCard>

  <PanelCard>
    <h3>用户管理</h3>
    <input v-model="userForm.username" placeholder="用户名" />
    <input v-model="userForm.password" type="password" placeholder="密码" />
    <select v-model="userForm.role">
      <option value="admin">admin</option>
      <option value="operator">operator</option>
      <option value="viewer">viewer</option>
    </select>
    <button @click="onCreateUser">新增用户</button>
    <button class="secondary" @click="loadUsers">刷新用户</button>

    <table>
      <thead><tr><th>ID</th><th>用户名</th><th>角色</th><th>状态</th><th>创建时间</th></tr></thead>
      <tbody>
        <tr v-for="u in users" :key="u.id">
          <td>{{ u.id }}</td>
          <td>{{ u.username }}</td>
          <td>{{ u.role }}</td>
          <td>{{ u.is_active }}</td>
          <td>{{ u.create_time }}</td>
        </tr>
      </tbody>
    </table>
  </PanelCard>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import PanelCard from '../components/PanelCard.vue'
import { createMessage, createUser, getMessages, getUsers } from '../api/devops'

const messageContent = ref('')
const query = ref({ keyword: '', start_time: '', end_time: '', limit: 20 })
const messages = ref([])
const messageSource = ref('-')

const userForm = ref({ username: '', password: '', role: 'viewer' })
const users = ref([])

// 按筛选条件查询留言。
async function loadMessages() {
  const res = await getMessages(query.value)
  messages.value = res.data || []
  messageSource.value = res.source || '-'
}

// 新建留言后刷新列表。
async function onCreateMessage() {
  if (!messageContent.value) return
  await createMessage(messageContent.value)
  messageContent.value = ''
  await loadMessages()
}

// 获取用户列表（后端自带缓存）。
async function loadUsers() {
  const res = await getUsers()
  users.value = res.data || []
}

// 新建用户后回填默认表单并刷新列表。
async function onCreateUser() {
  await createUser(userForm.value)
  userForm.value = { username: '', password: '', role: 'viewer' }
  await loadUsers()
}

onMounted(async () => {
  await loadMessages()
  await loadUsers()
})
</script>
