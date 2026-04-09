<template>
  <div class="marketplace-page">
    <div class="page-header">

      <h1 class="page-title">裸眼3D成片库</h1>
      <p class="page-subtitle">探索数百项优质纯原创 AGI 与 CG 结合制作的震撼案例，挑选符合您心意的裸眼 3D 成片进行二次适配。</p>
    </div>

    <!-- 瀑布流容器 -->
    <div class="waterfall-container">
      <div v-for="video in videoList" :key="video.id" class="video-card" @click="openModal(video)">
        <div class="video-preview-wrapper">
          <!-- 默认不播放声音并循环作为预览动画 -->
          <video 
            class="video-element" 
            :src="video.src" 
            muted 
            loop 
            playsinline
            @mouseenter="e => (e.target as HTMLVideoElement).play()"
            @mouseleave="e => (e.target as HTMLVideoElement).pause()"
          ></video>
          <div class="play-overlay">
            <el-icon class="play-icon"><VideoPlay /></el-icon>
            <span>点击播放</span>
          </div>
        </div>
        
        <div class="card-info">
          <div class="card-tags">
            <el-tag size="small" effect="light" class="cat-tag">{{ video.type }}</el-tag>
            <el-tag size="small" type="info" class="style-tag">#{{ video.tag }}</el-tag>
          </div>
          <h3 class="card-title">{{ video.title }}</h3>
          <p class="card-desc">{{ video.desc }}</p>
        </div>
      </div>
    </div>

    <!-- 视频播放模态框 -->
    <el-dialog 
      v-model="isModalVisible" 
      :title="activeVideo?.title" 
      width="60%"
      destroy-on-close
      class="video-dialog"
    >
      <div class="dialog-content" v-if="activeVideo">
        <video 
          class="dialog-video" 
          :src="activeVideo.src" 
          controls 
          autoplay 
          playsinline
        ></video>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <div class="dialog-price">
            <span class="price-hint">成片适配起步价</span>
            <span class="price-amount">¥ 8,800起</span>
          </div>
          <div>
            <el-button @click="isModalVisible = false">取消</el-button>
            <el-button type="primary" class="purchase-btn" @click="goToPurchase">
              立即购买适配
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { VideoPlay, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const isModalVisible = ref(false)
const activeVideo = ref<any>(null)

// 模拟视频数据库
const videoList = ref([
  { 
    id: 1, 
    title: '赛博朋克深空穿越', 
    type: '科幻奇境', 
    tag: '飞行器穿梭', 
    desc: '极具纵深感的宇宙飞行画面，机械部件极度写实，适合追求震撼冲击力的品牌展示。',
    src: '/videos/video1.mp4' 
  },
  { 
    id: 2, 
    title: '未来机甲异星破阵', 
    type: '硬科幻', 
    tag: '机械跃出', 
    desc: '巨型机甲从屏幕深处跳跃而出的裸眼3D大作，强烈的打破屏幕错觉。',
    src: '/videos/video2.mp4' 
  },
  { 
    id: 3, 
    title: '数字生机奇幻绿洲', 
    type: '超现实空间', 
    tag: '自然奇观', 
    desc: '数字花卉与晶体融合盛开，色彩艳丽，优雅高级，适合美妆或高端商业综合体宣发。',
    src: '/videos/video3.mp4' 
  },
  { 
    id: 4, 
    title: '霓虹暗都异客觉醒', 
    type: '赛博末世', 
    tag: '炫彩光影', 
    desc: '丰富的炫光特效与立体环境构造，光怪陆离的都市倒影极其深邃。',
    src: '/videos/video4.mp4' 
  }
])



const openModal = (video: any) => {
  activeVideo.value = video
  isModalVisible.value = true
}

const goToPurchase = () => {
  isModalVisible.value = false
  // 传参可以在query或者仅仅进入填写页
  router.push({
    path: '/user/create-order/video_purchase',
    query: { selected_id: activeVideo.value.id, title: activeVideo.value.title }
  })
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

.play-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.3);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #fff;
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
  background: #f0f4ff;
  border-color: #d6e2ff;
  color: #2F54EB;
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

/* 弹窗特化 */
.dialog-content {
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
}

.dialog-video {
  width: 100%;
  max-height: 60vh;
  object-fit: contain;
  display: block;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 8px;
}

.dialog-price {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.price-hint {
  font-size: 13px;
  color: #888;
}

.price-amount {
  font-size: 20px;
  font-weight: 700;
  color: #FF4D4F;
  margin-top: 4px;
}

.purchase-btn {
  font-weight: 600;
}
</style>
