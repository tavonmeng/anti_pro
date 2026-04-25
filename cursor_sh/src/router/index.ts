import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/login'
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/admin/login',
      name: 'AdminLogin',
      component: () => import('../views/AdminLogin.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('../views/Register.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/user',
      component: () => import('../views/UserDashboard.vue'),
      meta: { requiresAuth: true, role: 'user' },
      redirect: '/user/workspace',
      children: [
        {
          path: 'workspace',
          name: 'Workspace',
          component: () => import('../views/user/Workspace.vue'),
          meta: { requiresAuth: true, role: 'user' }
        },
        {
          path: 'video-marketplace',
          name: 'VideoMarketplace',
          component: () => import('../views/user/VideoMarketplace.vue'),
          meta: { requiresAuth: true, role: 'user' }
        },
        {
          path: 'create-order/:type',
          name: 'CreateOrder',
          component: () => import('../views/user/CreateOrder.vue'),
          meta: { requiresAuth: true, role: 'user' }
        },
        {
          path: 'orders',
          name: 'Orders',
          component: () => import('../views/user/Orders.vue'),
          meta: { requiresAuth: true, role: 'user' }
        },
        {
          path: 'orders/:id',
          name: 'OrderDetail',
          component: () => import('../views/user/OrderDetail.vue'),
          meta: { requiresAuth: true, role: 'user' }
        },
        {
          path: 'edit-order/:id',
          name: 'EditOrder',
          component: () => import('../views/user/CreateOrder.vue'),
          meta: { requiresAuth: true, role: 'user' }
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('../views/user/Profile.vue'),
          meta: { requiresAuth: true, role: 'user' }
        },
        {
          path: 'drafts',
          name: 'Drafts',
          component: () => import('../views/user/Drafts.vue'),
          meta: { requiresAuth: true, role: 'user' }
        },
        // 保留旧路由用于兼容
        {
          path: 'tasks',
          redirect: '/user/orders'
        }
      ]
    },
    {
      path: '/admin',
      component: () => import('../views/AdminDashboard.vue'),
      meta: { requiresAuth: true, role: 'admin' },
      redirect: '/admin/orders',
      children: [
        {
          path: 'orders',
          name: 'AdminOrders',
          component: () => import('../views/admin/OrderManagement.vue'),
          meta: { requiresAuth: true, role: 'admin' }
        },
        {
          path: 'orders/:id',
          name: 'AdminOrderDetail',
          component: () => import('../views/admin/AdminOrderDetail.vue'),
          meta: { requiresAuth: true, role: 'admin' }
        },
        {
          path: 'staff',
          name: 'StaffManagement',
          component: () => import('../views/admin/StaffManagement.vue'),
          meta: { requiresAuth: true, role: 'admin' }
        },
        {
          path: 'announcements',
          name: 'AnnouncementManagement',
          component: () => import('../views/admin/AnnouncementManagement.vue'),
          meta: { requiresAuth: true, role: 'admin' }
        },
        {
          path: 'enterprise-review',
          name: 'EnterpriseReview',
          component: () => import('../views/admin/EnterpriseReview.vue'),
          meta: { requiresAuth: true, role: 'admin' }
        }
      ]
    },
    {
      path: '/staff',
      component: () => import('../views/StaffDashboard.vue'),
      meta: { requiresAuth: true, role: 'staff' },
      redirect: '/staff/orders',
      children: [
        {
          path: 'orders',
          name: 'StaffOrders',
          component: () => import('../views/staff/OrderList.vue'),
          meta: { requiresAuth: true, role: 'staff' }
        },
        {
          path: 'orders/:id',
          name: 'StaffOrderDetail',
          component: () => import('../views/staff/OrderDetail.vue'),
          meta: { requiresAuth: true, role: 'staff' }
        },
        {
          path: 'profile',
          name: 'StaffProfile',
          component: () => import('../views/staff/Profile.vue'),
          meta: { requiresAuth: true, role: 'staff' }
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  // 检查是否需要认证
  if (to.meta.requiresAuth && !authStore.isAuthenticated()) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  
  // 检查角色权限
  if (to.meta.role) {
    const requiredRole = to.meta.role as string
    if (requiredRole === 'admin' && !authStore.isAdmin()) {
      ElMessage.error('您没有权限访问此页面')
      if (authStore.isStaff()) {
        next('/staff')
      } else {
        next('/user')
      }
      return
    }
    if (requiredRole === 'staff' && !authStore.isStaff()) {
      ElMessage.error('您没有权限访问此页面')
      if (authStore.isAdmin()) {
        next('/admin')
      } else {
        next('/user')
      }
      return
    }
    if (requiredRole === 'user' && !authStore.isUser()) {
      ElMessage.error('您没有权限访问此页面')
      if (authStore.isAdmin()) {
        next('/admin')
      } else if (authStore.isStaff()) {
        next('/staff')
      } else {
        next('/login')
      }
      return
    }
  }
  
  // 如果已登录，访问登录页则跳转到对应dashboard
  if (authStore.isAuthenticated()) {
    if (to.name === 'Login' || to.name === 'Register') {
      if (to.query.modal === 'true') {
        window.parent.postMessage({ type: 'LOGIN_SUCCESS' }, '*')
        next(false)
        return
      }
      // 用户登录页 -> 根据角色跳转
      if (authStore.isAdmin()) {
        next('/admin')
      } else if (authStore.isStaff()) {
        next('/staff')
      } else {
        next('/user/workspace')
      }
      return
    }
    if (to.name === 'AdminLogin') {
      // 管理员/负责人登录页 -> 根据角色跳转
      if (authStore.isAdmin()) {
        next('/admin')
      } else if (authStore.isStaff()) {
        next('/staff')
      } else {
        next('/user/workspace')
      }
      return
    }
  }
  
  next()
})

export default router

