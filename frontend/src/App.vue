<script setup>
import SiteNavigation from './components/SiteNavigation.vue'
import AiChatWidget from './components/AiChatWidget.vue'
</script>

<template>
  <SiteNavigation />
  <main class="date-card">
    <RouterView />
  </main>
  <AiChatWidget />
</template>
