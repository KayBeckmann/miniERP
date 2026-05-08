import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/LoginPage.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('@/layouts/DefaultLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/dashboard',
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/pages/DashboardPage.vue'),
        },
        {
          path: 'customers',
          name: 'customers',
          component: () => import('@/pages/CustomersPage.vue'),
        },
        {
          path: 'quotes',
          name: 'quotes',
          component: () => import('@/pages/QuotesPage.vue'),
        },
        {
          path: 'orders',
          name: 'orders',
          component: () => import('@/pages/OrdersPage.vue'),
        },
        {
          path: 'invoices',
          name: 'invoices',
          component: () => import('@/pages/InvoicesPage.vue'),
        },
        {
          path: 'time',
          name: 'time',
          component: () => import('@/pages/TimeEntryPage.vue'),
        },
        {
          path: 'supplier-invoices',
          name: 'supplier-invoices',
          component: () => import('@/pages/SupplierInvoicesPage.vue'),
        },
        {
          path: 'reports',
          name: 'reports',
          component: () => import('@/pages/ReportsPage.vue'),
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
})

export default router
