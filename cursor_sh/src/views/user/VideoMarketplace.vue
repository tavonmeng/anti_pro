<template>
  <div class="marketplace-page">
    <div class="page-header">

      <h1 class="page-title">裸眼3D成片库</h1>
      <p class="page-subtitle">探索数百项优质纯原创 AGI 与 CG 结合制作的震撼案例，挑选符合您心意的裸眼 3D 成片进行二次适配。</p>
    </div>

    <div class="waterfall-container">
      <div
        v-for="video in videoList"
        :key="video.id"
        class="video-card"
        role="button"
        tabindex="0"
        @click="goToDetail(video)"
        @keydown.enter.self.prevent="goToDetail(video)"
        @keydown.space.self.prevent="goToDetail(video)"
      >
        <div class="video-preview-wrapper">
          <img
            v-if="video.media.type === 'image'"
            class="preview-image"
            :src="video.media.url"
            :alt="video.title"
          />
          <video 
            v-else
            class="video-element" 
            :src="video.media.url"
            :poster="video.media.poster"
            muted 
            loop 
            playsinline
            @mouseenter="e => (e.target as HTMLVideoElement).play()"
            @mouseleave="e => (e.target as HTMLVideoElement).pause()"
          ></video>
          <div class="play-overlay">
            <el-icon class="play-icon"><VideoPlay /></el-icon>
            <span>查看详情</span>
          </div>
        </div>
        
        <div class="card-info">
          <div class="card-tags">
            <el-tag size="small" effect="light" class="cat-tag">{{ video.type }}</el-tag>
            <el-tag size="small" type="info" class="style-tag">#{{ video.tag }}</el-tag>
          </div>
          <h3 class="card-title">{{ video.title }}</h3>
          <p class="card-desc">{{ video.desc }}</p>
          <div class="card-price">
            <span>{{ video.price.label }}</span>
            <strong>{{ video.price.display }}</strong>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { VideoPlay } from '@element-plus/icons-vue'
import { buildVideoPurchaseRoute, videoLibraryItems, type VideoLibraryItem } from '@/data/videoMarketplace'

const router = useRouter()
const videoList = videoLibraryItems

const goToDetail = (video: VideoLibraryItem) => {
  router.push(buildVideoPurchaseRoute(video))
}
</script>

<style scoped>
.marketplace-page {
  padding: 32px 48px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 48px;
  text-align: center;
  position: relative;
}

.back-button {
  position: absolute;
  left: 0;
  top: 0;
  font-size: 15px;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: #1D1D1F;
  margin: 0 0 16px 0;
}

.page-subtitle {
  font-size: 16px;
  color: #86868B;
  max-width: 600px;
  margin: 0 auto;
  line-height: 1.6;
}

/* 瀑布流布局 */
.waterfall-container {
  column-count: 2;
  column-gap: 24px;
  padding-bottom: 64px;
}

@media (max-width: 768px) {
  .waterfall-container {
    column-count: 1;
  }
}

.video-card {
  break-inside: avoid;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 24px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.06);
  cursor: pointer;
  border: 1px solid #eaeaea;
  transition: all 0.3s cubic-bezier(0.25, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
}

.video-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 40px rgba(0,0,0,0.12);
  border-color: #ddd;
}

.video-preview-wrapper {
  width: 100%;
  position: relative;
  background: #111;
  display: flex;
}

.video-element {
  width: 100%;
  height: auto;
  display: block;
}

.preview-image {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
}

.play-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.3);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: var(--uv-ws-action-button-bg, #A0522D);
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none; /* 让 hover 事件作用到底部 video */
}

.video-card:hover .play-overlay {
  opacity: 1;
}

.play-icon {
  font-size: 48px;
  margin-bottom: 8px;
  opacity: 0.9;
}

.card-info {
  padding: 24px;
}

.card-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.cat-tag {
  background: var(--uv-ws-module-active-bg, #F3E7E1);
  border-color: rgba(160, 82, 45, 0.24);
  color: var(--uv-ws-action-button-bg, #A0522D);
}

.style-tag {
  background: #f5f5f5;
  border-color: #e8e8e8;
  color: #666;
}

.card-title {
  font-size: 20px;
  font-weight: 600;
  color: #111;
  margin: 0 0 12px 0;
}

.card-desc {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-price {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.card-price span {
  font-size: 13px;
  color: #86868b;
}

.card-price strong {
  font-size: 20px;
  font-weight: 700;
  color: #FF4D4F;
}
</style>
