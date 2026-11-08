import { createApp } from 'vue'
import { createWebHistory } from 'vue-router'
import App from './App.vue'
import { createDateRouter } from './router.js'
import './style.css'

createApp(App).use(createDateRouter(createWebHistory())).mount('#app')
