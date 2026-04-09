import { reactive } from 'vue'

export const uiState = reactive({
  authModalOpen: false,
  authMode: 'login'
})

export const openAuthModal = (mode = 'login') => {
  uiState.authMode = mode
  uiState.authModalOpen = true
}

export const closeAuthModal = () => {
  uiState.authModalOpen = false
}
