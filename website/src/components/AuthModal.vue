<template>
  <transition name="modal-fade">
    <div class="auth-modal-overlay" v-if="isOpen" @click.self="close">
      <div class="auth-modal-box">
        <button class="close-btn" @click="close" aria-label="关闭">×</button>
        <iframe :src="iframeUrl" frameborder="0" class="auth-iframe"></iframe>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  mode: {
    type: String,
    default: 'login' // 'login' or 'register'
  }
})

const emit = defineEmits(['close'])

const dashboardUrl = import.meta.env.VITE_DASHBOARD_URL || 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? `${window.location.protocol}//${window.location.hostname}:3000`
    : `${window.location.protocol}//${window.location.hostname}:8080`)

const iframeUrl = computed(() => {
  return `${dashboardUrl}/${props.mode}?modal=true`
})

const close = () => {
  emit('close')
}

const handleMessage = (event) => {
  // 确保消息来源于我们信任的 dashboard 域名（本地也可以允许）
  // 只要收到登录成功，就跳转
  if (event.data && event.data.type === 'LOGIN_SUCCESS') {
    window.location.href = `${dashboardUrl}/user/workspace`
  }
}

onMounted(() => {
  window.addEventListener('message', handleMessage)
})

onUnmounted(() => {
  window.removeEventListener('message', handleMessage)
})
</script>

<style scoped>
.auth-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(210, 210, 215, 0.64);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-modal-box {
  width: 90%;
  max-width: 440px;
  height: 620px;
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: rgba(0, 0, 0, 0.22) 3px 5px 30px 0px;
  border: none;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 20px;
  background: transparent;
  border: none;
  color: #1d1d1f;
  opacity: 0.48;
  font-size: 28px;
  cursor: pointer;
  z-index: 10;
  line-height: 1;
  transition: all 0.2s;
  padding: 0;
}

.close-btn:hover {
  opacity: 1;
  transform: scale(1.1);
}

.auth-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: transparent;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .auth-modal-box,
.modal-fade-leave-active .auth-modal-box {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-fade-enter-from .auth-modal-box {
  transform: translateY(20px) scale(0.95);
}

.modal-fade-leave-to .auth-modal-box {
  transform: translateY(20px) scale(0.95);
}
</style>
