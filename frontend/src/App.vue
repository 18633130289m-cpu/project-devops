<template>
  <div class="app-wrap">
    <header class="app-header">
      <h1>DevOps 运维控制台</h1>
      <p class="muted">Vue + Pinia + Vue Router + Flask API</p>
    </header>

    <nav class="tabs">
      <RouterLink to="/manage" class="tab">管理页面</RouterLink>
      <RouterLink to="/monitor" class="tab">监控面板</RouterLink>
      <RouterLink to="/backup" class="tab">备份记录页面</RouterLink>
      <RouterLink to="/logs" class="tab">日志查看页面</RouterLink>
    </nav>

    <RouterView />
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>
