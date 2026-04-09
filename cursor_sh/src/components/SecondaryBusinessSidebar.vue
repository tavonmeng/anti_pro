<template>
  <div class="secondary-sidebar">
    <div class="secondary-header">
      <h3>业务菜单</h3>
    </div>
    <div class="module-list">
      <!-- AI Agent Entry (Banner Style) -->
      <div 
        class="ai-agent-banner"
        :class="{ active: uiStore.isAiExpanded }"
        @click="goToService('ai_agent')"
      >
        <div class="ai-banner-header">
          <span class="ai-banner-sparkle">✨</span>
          <h4 class="ai-banner-title">AI智能体帮你理清思路</h4>
        </div>
        <p class="ai-banner-subtitle">您的 24/7 创意合伙人</p>
        <div class="ai-banner-input-mock">
          <span class="ai-mock-placeholder">有什么想法...</span>
          <div class="ai-mock-btn">
            发送 ✨
          </div>
        </div>
      </div>

      <div class="divider"></div>

      <div 
        class="module-group"
        :class="{ active: currentModule === 'video_purchase' }"
      >
        <div class="module-title" @click="goToService('video_purchase')">
          <span class="module-name">裸眼3D成片购买</span>
          <el-icon class="expand-icon" :class="{ rotated: currentModule === 'video_purchase' }"><ArrowDown /></el-icon>
        </div>
        <div class="module-intro" v-show="currentModule === 'video_purchase'">
          <div class="intro-image" style="background: linear-gradient(to bottom right, #111, #333);">
            <div class="badge">Premium 3D</div>
          </div>
          <p class="intro-desc">
            专业的裸眼3D视频内容库。海量高质量成片，基于您屏幕参数快速二次适配，最快48小时极速交付。
          </p>
        </div>
      </div>

      <div 
        class="module-group"
        :class="{ active: currentModule === 'ai_3d_custom' }"
      >
        <div class="module-title" @click="goToService('ai_3d_custom')">
          <span class="module-name">AI裸眼3D内容定制</span>
          <el-icon class="expand-icon" :class="{ rotated: currentModule === 'ai_3d_custom' }"><ArrowDown /></el-icon>
        </div>
        <div class="module-intro" v-show="currentModule === 'ai_3d_custom'">
          <div class="intro-image" style="background: linear-gradient(to bottom right, #001f3f, #004080);">
            <div class="badge creative">AI Creative</div>
          </div>
          <p class="intro-desc">
            基于前沿AI技术的定制化3D内容创作。提供创意文字即可生成震撼视觉，将灵感快速转化为高品质展出作品。
          </p>
        </div>
      </div>

      <div 
        class="module-group"
        :class="{ active: currentModule === 'digital_art' }"
      >
        <div class="module-title" @click="goToService('digital_art')">
          <span class="module-name">数字艺术内容定制</span>
          <el-icon class="expand-icon" :class="{ rotated: currentModule === 'digital_art' }"><ArrowDown /></el-icon>
        </div>
        <div class="module-intro" v-show="currentModule === 'digital_art'">
          <div class="intro-image" style="background: linear-gradient(to bottom right, #4a0000, #ff1a1a);">
            <div class="badge art">Digital Art</div>
          </div>
          <p class="intro-desc">
            专属资深艺术家团队人工精雕。涵盖抽象、写实等定制艺术流派，为您定制独一无二的线下屏幕地标数字艺术品。
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { ArrowDown, Right } from '@element-plus/icons-vue'

const router = useRouter()
const uiStore = useUiStore()

const currentModule = computed(() => uiStore.activeModule)

const goToService = async (type: string) => {
  if (type === 'ai_agent') {
    uiStore.setIsAiExpanded(true)
    uiStore.setSecondarySidebar(false)
    await router.push('/user/workspace')
    return
  }

  if (type === 'video_purchase') {
    await router.push('/user/video-marketplace')
  } else {
    await router.push(`/user/create-order/${type}`)
  }
}
</script>

<style scoped>
.secondary-sidebar {
  width: 260px; /* Slight bump for side imagery room */
  background: #ffffff;
  border-right: 1px solid #eae7e7;
  display: flex;
  flex-direction: column;
  padding: 24px 0;
  box-sizing: border-box;
  flex-shrink: 0;
  overflow-y: auto;
  animation: sidebar-expand 0.45s cubic-bezier(0.25, 1, 0.3, 1) both;
}

@keyframes sidebar-expand {
  from {
    width: 0;
    padding: 24px 0;
    opacity: 0;
  }
  to {
    width: 260px;
    padding: 24px 0;
    opacity: 1;
  }
}

.secondary-header {
  padding: 0 24px;
  margin-bottom: 24px;
}

.secondary-header h3 {
  font-size: 14px;
  font-weight: 700;
  color: #1b1b1c;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.module-list {
  display: flex;
  flex-direction: column;
  padding: 0 16px;
  gap: 12px;
}

/* AI Agent Banner Style */
.ai-agent-banner {
  background: #f0f5fc;
  border-radius: 14px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 1, 0.3, 1);
  border: 1px solid rgba(0, 88, 188, 0.1);
  margin-bottom: 4px;
  position: relative;
  overflow: hidden;
}

.ai-agent-banner:hover {
  background: #e8f0f9;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 88, 188, 0.08);
}

.ai-agent-banner.active {
  background: #fff;
  border: 1px solid #0058bc;
  box-shadow: 0 4px 20px rgba(0, 88, 188, 0.12);
}

.ai-banner-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.ai-banner-sparkle {
  font-size: 14px;
}

.ai-banner-title {
  font-size: 14px;
  font-weight: 800;
  color: #1b1b1c;
  margin: 0;
  letter-spacing: -0.01em;
}

.ai-banner-subtitle {
  font-size: 11px;
  color: #646a78;
  margin: 0 0 12px 0;
  line-height: 1.4;
}

.ai-banner-input-mock {
  background: #fff;
  border-radius: 99px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 0 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0,0,0,0.02);
}

.ai-mock-placeholder {
  font-size: 11px;
  color: #a0a4ae;
}

.ai-mock-btn {
  background: #0058bc;
  color: #fff;
  font-weight: 600;
  padding: 0 10px;
  height: 24px;
  border-radius: 99px;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.module-group {
  border-radius: 12px;
  background: #f6f3f2;
  transition: all 0.3s ease;
  overflow: hidden;
}

.module-group.active {
  background: #fcfcfc;
  box-shadow: 0 4px 16px rgba(0,0,0,0.04);
  border: 1px solid #f0f0f0;
}

.module-title {
  padding: 14px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  color: #414754;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.module-title:hover {
  color: #1b1b1c;
}

.module-group.active .module-title {
  color: #1b1b1c;
  font-weight: 600;
  padding-bottom: 8px; /* Room for intro */
}

.expand-icon {
  font-size: 12px;
  color: #888;
  transition: transform 0.3s cubic-bezier(0.25, 1, 0.5, 1);
}

.expand-icon.rotated {
  transform: rotate(180deg);
  color: #333;
}

/* Descriptive Intro inside accordion */
.module-intro {
  padding: 0 16px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: slide-down 0.35s cubic-bezier(0.25, 1, 0.3, 1) both;
}

@keyframes slide-down {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.intro-image {
  height: 100px;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.1);
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 8px;
}

.intro-image .badge {
  background: rgba(0, 112, 235, 0.9);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 4px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.intro-image .badge.creative { background: rgba(0, 112, 235, 0.9); }
.intro-image .badge.art { background: rgba(0, 112, 235, 0.9); }

.intro-desc {
  margin: 0;
  font-size: 12px;
  color: #6c707d;
  line-height: 1.6;
}

</style>
