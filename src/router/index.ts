import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
    { path: '/timeline', name: 'timeline', component: () => import('@/views/TimelineView.vue') },
    { path: '/culture', name: 'culture', component: () => import('@/views/CultureView.vue') },
  ],
})

export default router
