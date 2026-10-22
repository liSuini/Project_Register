import { createRouter, createWebHistory } from 'vue-router'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'list', component: () => import('./views/ProjectList.vue') },
    { path: '/projects/:id', name: 'detail', component: () => import('./views/ProjectDetail.vue') },
    { path: '/stats', name: 'stats', component: () => import('./views/StatsView.vue') }
  ]
})
