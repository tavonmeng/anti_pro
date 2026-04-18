<template>
  <div class="staff-dashboard">
    <div class="dashboard-container">
      <Sidebar class="dashboard-sidebar" />
      
      <div class="dashboard-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from '@/components/Sidebar.vue'
</script>

<style lang="scss" scoped>
/* 统一最外层布局强制居中 */
.login-container, .admin-login-container, .register-container {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #000;
  font-family: 'Outfit', 'PingFang SC', sans-serif;
  color: #fff;
  padding: 20px 0;
  box-sizing: border-box;
}

.login-wrapper, .admin-login-wrapper, .register-wrapper {
  position: relative;
  z-index: 10;
  width: 90%;
  max-width: 400px;
  background: #000;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  margin: 0;
  padding: 32px;
  box-sizing: border-box;
}

/* 头部重置 */
.login-header, .admin-login-header, .register-header {
  text-align: center;
  margin-bottom: 24px;
}

.logo-icon, .lock-icon {
  width: 50px;
  height: 50px;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 50%;
  color: #000;
}

.logo-svg { width: 32px; height: 32px; }
.logo-svg circle, .logo-svg path { stroke: #000 !important; }

.login-title, .admin-title, .register-title {
  font-size: 24px;
  font-weight: 800;
  color: #fff;
  margin: 0 0 6px 0;
  text-align: center;
  line-height: 1.2;
}

.login-subtitle, .admin-subtitle, .register-subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
  text-align: center;
}

/* 表单紧凑设定 */
.login-form, .admin-login-form, .register-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

:deep(.el-form-item) {
  margin-bottom: 0 !important; 
  width: 100%;
}
:deep(.el-form-item__content) {
  line-height: normal !important;
}

.input-wrapper {
  width: 100%;
}

/* 黑底输入框原生主题覆写 */
.tech-input, .admin-input, .captcha-input {
  :deep(.el-input__wrapper) {
    background-color: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2) !important;
    box-shadow: none !important;
    padding: 0 10px !important;
    height: 40px;
    transition: all 0.3s;
    
    &.is-focus, &:hover {
      border-bottom-color: #fff !important;
    }
  }

  :deep(.el-input__inner) {
    height: 40px !important;
    font-size: 15px !important;
    color: #fff !important;
    &::placeholder {
      color: rgba(255, 255, 255, 0.4) !important;
    }
  }
}

.input-border { display: none !important; }
.input-icon { color: #888; font-size: 18px; }

/* 按钮 */
.login-button, .admin-login-button, .register-button {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  background: #fff !important;
  border: none !important;
  border-radius: 60px !important;
  color: #000 !important;
  margin-top: 8px; 
  transition: all 0.2s;
  
  &:hover {
    background: #e0e0e0 !important;
    transform: translateY(-2px);
  }
}

.button-icon { margin-left: 8px; }

/* 尾部区域 */
.login-footer, .admin-login-footer, .register-footer {
  margin-top: 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.footer-text, .security-notice, .security-tips {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.footer-link, .back-link {
  font-size: 13px;
  margin: 0;
}

:deep(.el-link) {
  color: #fff !important;
  font-weight: 600;
  &:hover { opacity: 0.8; }
}

/* 验证码特殊布局补丁 */
.captcha-container { display: flex; gap: 12px; align-items: center; width: 100%; }
.captcha-display {
  border-radius: 8px; overflow: hidden; height: 40px; 
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.captcha-display canvas { height: 100% !important; display: block; }
.captcha-input { flex: 1; }

.minimal-background {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background-color: #000; z-index: 1; pointer-events: none;
}
</style>


