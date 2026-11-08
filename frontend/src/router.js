import { createRouter } from 'vue-router'
import DateView from './views/DateView.vue'

export function createDateRouter(history) {
  return createRouter({
    history,
    routes: [
      { path: '/', component: DateView },
      { path: '/:year(\\d{4})/:month(\\d{2})/:day(\\d{2})', component: DateView },
      { path: '/:pathMatch(.*)*', component: DateView, props: { notFound: true } },
    ],
  })
}
