<template>
  <div class="secondary-sidebar">
    <div class="secondary-header">
      <h3>业务菜单</h3>
    </div>
    <div class="module-list">
      <!-- AI Agent Entry (Banner Style) -->
      <div class="ai-agent-banner" :class="{ active: uiStore.isAiExpanded }" @click="goToService('ai_agent')">
        <h4 class="ai-banner-title">✨您的7×24小时AI创意合伙人</h4>
        <div class="ai-banner-input-mock">
          <span class="ai-mock-placeholder">有什么想法...</span>
          <div class="ai-mock-btn">发送 ✨</div>
        </div>
      </div>
    </div>

    <!-- 贯穿首尾的无空隙分割线 -->
    <div class="figma-full-divider"></div>

    <div class="module-list" style="margin-top: 16px;">

      <div 
        class="module-group"
        :class="{ active: currentModule === 'video_purchase' }"
      >
        <div class="module-pill" :class="{ 'is-active': currentModule === 'video_purchase' }" @click="goToService('video_purchase')">
          <span class="module-name">裸眼3D成片购买</span>
          <el-icon class="expand-icon" :class="{ rotated: currentModule === 'video_purchase', 'is-active-icon': currentModule === 'video_purchase' }"><ArrowDown /></el-icon>
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
        <div class="module-pill" :class="{ 'is-active': currentModule === 'ai_3d_custom' }" @click="goToService('ai_3d_custom')">
          <span class="module-name">AI裸眼3D内容定制</span>
          <el-icon class="expand-icon" :class="{ rotated: currentModule === 'ai_3d_custom', 'is-active-icon': currentModule === 'ai_3d_custom' }"><ArrowDown /></el-icon>
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
        <div class="module-pill" :class="{ 'is-active': currentModule === 'digital_art' }" @click="goToService('digital_art')">
          <span class="module-name">数字艺术内容定制</span>
          <el-icon class="expand-icon" :class="{ rotated: currentModule === 'digital_art', 'is-active-icon': currentModule === 'digital_art' }"><ArrowDown /></el-icon>
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
  width: 260px;
  background: #f3f3f4;
  border-right: 1px solid rgba(0,0,0,0.05);
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
    opacity: 0;
  }
  to {
    width: 260px;
    opacity: 1;
  }
}

.secondary-header {
  padding: 0 16px;
  margin-bottom: 24px;
}

.secondary-header h3 {
  font-size: 14px;
  font-weight: 500;
  color: #1b1b1c;
  margin: 0;
  letter-spacing: 0.5px;
}

.module-list {
  display: flex;
  flex-direction: column;
  padding: 0 8px; /* Was 24px, Figma uses tight padding so buttons stretch wide */
  gap: 0;
}

.figma-full-divider {
  width: 100%;
  height: 1px;
  background-color: #000000;
  opacity: 0.08; /* Strict black and white system */
  margin: 12px 0 0 0;
  flex-shrink: 0;
}

/* AI Agent Banner Style */
.ai-agent-banner {
  background: transparent; /* No card background */
  padding: 12px 12px; /* Aligned with pill text */
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  border-radius: 12px; /* Smoother corner */
}

.ai-agent-banner:hover {
  background: rgba(0,0,0,0.03);
}

.ai-agent-banner:hover .ai-banner-title {
  color: #000;
}

.ai-agent-banner.active .ai-banner-title {
  color: #000;
}

.ai-banner-title {
  font-size: 13px;
  font-weight: 500;
  color: #1b1b1c;
  margin: 0 0 12px 0;
  letter-spacing: -0.01em;
}

.ai-banner-input-mock {
  background: #ffffff;
  border-radius: 99px; /* Stitch pill */
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 0 16px;
  border: 1px solid rgba(0,0,0,0.08);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.ai-agent-banner:hover .ai-banner-input-mock {
  border-color: rgba(0,0,0,0.15);
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.ai-mock-placeholder {
  font-size: 12px;
  color: #a0a4ae;
}

.ai-mock-btn {
  background: #f3f3f4; /* Softer background */
  color: #1b1b1c;
  font-weight: 500;
  padding: 0 12px;
  height: 28px;
  border-radius: 99px;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.module-group {
  background: transparent;
  transition: all 0.3s ease;
  overflow: hidden;
  border: none; /* No separator between items per user request */
  margin-bottom: 4px;
}

.module-pill {
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  color: #414754;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.2s;
  background: transparent;
}

.module-pill:hover {
  background: rgba(0, 0, 0, 0.04);
  color: #1b1b1c;
}

.module-pill.is-active {
  background: #e5f4ff; /* Figma active item light blue */
  color: #1a1c1c; /* Text stays dark/black as in Figma */
  font-weight: 500;
  margin-bottom: 8px; /* space before intro drops down */
}

.expand-icon {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.4);
  transition: transform 0.3s ease;
}

.expand-icon.is-active-icon {
  color: #0d99ff; /* The icon takes the Figma primary blue to pop */
}

.expand-icon.rotated {
  transform: rotate(180deg);
  color: #333;
}

/* Descriptive Intro inside accordion */
.module-intro {
  padding: 0 12px 24px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: slide-down 0.25s ease both;
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
  font-weight: 500;
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
