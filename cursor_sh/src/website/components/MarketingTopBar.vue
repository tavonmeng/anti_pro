<template>
  <div
    v-if="isActive"
    class="marketing-top-bar"
    :class="{ 'is-hidden': !isVisible }"
    @click="openPdf"
  >
    <div class="bar-inner">
      <div class="bar-content">
        <span class="bar-media" aria-hidden="true">
          <img v-if="bar?.image_url" :src="bar.image_url" alt="" />
        </span>
        <span class="bar-copy">
          <span class="bar-title">{{ bar?.title }}</span>
          <button class="bar-action" type="button" @click.stop="openPdf">
            <span>{{ bar?.button_text || '下载 PDF' }}</span>
            <span class="bar-action-icon" aria-hidden="true"></span>
          </button>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { homepageBarApi, type HomepageBarConfig } from '@/utils/api'

const emit = defineEmits<{
  (e: 'visibility-change', visible: boolean): void
  (e: 'active-change', active: boolean): void
}>()

const bar = ref<HomepageBarConfig | null>(null)
const isVisible = ref(true)

const isActive = computed(() => Boolean(bar.value?.is_active && bar.value?.pdf_url))

const openPdf = () => {
  if (!bar.value?.pdf_url) return
  window.open(bar.value.pdf_url, '_blank', 'noopener,noreferrer')
}

const handleScroll = () => {
  const currentY = window.scrollY || 0
  isVisible.value = currentY < 16
}

const fetchBar = async () => {
  try {
    bar.value = await homepageBarApi.getPublic()
  } catch {
    bar.value = null
  }
}

watch(isVisible, value => emit('visibility-change', value), { immediate: true })
watch(isActive, value => emit('active-change', value), { immediate: true })

onMounted(() => {
  fetchBar()
  handleScroll()
  window.addEventListener('scroll', handleScroll, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.marketing-top-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 5002;
  height: 58px;
  display: flex;
  align-items: center;
  background: #d8ff36;
  color: #050505;
  border-bottom: 1px solid rgba(0, 0, 0, 0.16);
  transform: translateY(0);
  transition: transform 0.32s cubic-bezier(0.22, 1, 0.36, 1);
  cursor: pointer;
}

.marketing-top-bar.is-hidden {
  transform: translateY(-100%);
}

.bar-inner {
  width: 100%;
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-width: 0;
}

.bar-content {
  max-width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-width: 0;
}

.bar-media {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(5, 5, 5, 0.92) 0%, rgba(5, 5, 5, 0.92) 50%, transparent 50%),
    rgba(5, 5, 5, 0.18);
  flex: 0 0 auto;
  box-shadow: inset 0 0 0 1px rgba(5, 5, 5, 0.14);
}

.bar-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.bar-copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 5px;
  min-width: 0;
}

.bar-title {
  max-width: min(72vw, 520px);
  font-size: 14px;
  line-height: 1.08;
  font-weight: 900;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  text-align: left;
}

.bar-action {
  max-width: min(72vw, 520px);
  height: auto;
  padding: 0;
  border: 0;
  background: transparent;
  color: rgba(5, 5, 5, 0.72);
  font-size: 12px;
  line-height: 1.1;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.bar-action:hover {
  color: #050505;
}

.bar-action-icon {
  width: 5px;
  height: 5px;
  border-top: 1.4px solid currentColor;
  border-right: 1.4px solid currentColor;
  transform: rotate(45deg);
  flex: 0 0 auto;
}

@media (max-width: 720px) {
  .bar-inner {
    padding: 0 12px;
  }

  .bar-title {
    font-size: 12px;
  }

  .bar-action {
    font-size: 11px;
  }

  .bar-media {
    width: 34px;
    height: 34px;
    border-radius: 7px;
  }
}
</style>
