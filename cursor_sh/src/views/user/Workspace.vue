<template>
  <div class="workspace-page">
    <div class="page-header">
      <h1 class="page-title">服务工作台</h1>
      <p class="page-subtitle">欢迎回来，{{ authStore.user?.username }}。选择您需要的服务类型开始创作</p>
    </div>
    
    <!-- 我的订单概览 (置于最上方) -->
    <div class="my-orders-section" style="margin-top: 0; margin-bottom: 48px;">
      <div class="section-header">
        <h2 class="section-title">我的订单</h2>
        <el-button text type="primary" @click="goToOrders">
          查看全部
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
      
      <!-- 统计卡片 -->
      <div class="stats-cards">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #E3F2FD;">
              <el-icon :size="24" color="#2196F3"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ orderStore.orderStats.total }}</div>
              <div class="stat-label">总订单数</div>
            </div>
          </div>
        </el-card>
        
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #FFF3E0;">
              <el-icon :size="24" color="#FF9800"><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ orderStore.orderStats.inProduction }}</div>
              <div class="stat-label">制作中</div>
            </div>
          </div>
        </el-card>
        
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #F3E5F5;">
              <el-icon :size="24" color="#9C27B0"><View /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ orderStore.orderStats.preview }}</div>
              <div class="stat-label">待预览</div>
            </div>
          </div>
        </el-card>
        
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #E8F5E9;">
              <el-icon :size="24" color="#4CAF50"><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ orderStore.orderStats.completed }}</div>
              <div class="stat-label">已完成</div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 服务入口卡片 -->
    <div class="service-cards">
      <el-card class="service-card" shadow="hover" @click="goToService('video_purchase')">
        <div class="service-icon">📹</div>
        <h3 class="service-title">裸眼3D成片购买适配</h3>
        <p class="service-description">
          专业的裸眼3D视频内容库，根据您的屏幕参数精准适配，快速交付高质量成片。
          支持多种行业应用和视觉风格选择。
        </p>
        <div class="service-features">
          <el-tag size="small">快速交付</el-tag>
          <el-tag size="small" type="success">专业适配</el-tag>
          <el-tag size="small" type="info">多种风格</el-tag>
        </div>
        <el-button type="primary" class="service-button">
          开始选购
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </el-card>
      
      <el-card class="service-card" shadow="hover" @click="goToService('ai_3d_custom')">
        <div class="service-icon">🎨</div>
        <h3 class="service-title">AI裸眼3D内容定制</h3>
        <p class="service-description">
          基于AI技术的定制化3D内容创作，从创意构思到成品落地的全流程服务。
          上传现场照片，描述您的想法，我们将AI技术转化为震撼的裸眼3D效果。
        </p>
        <div class="service-features">
          <el-tag size="small">AI驱动</el-tag>
          <el-tag size="small" type="success">5-7天交付</el-tag>
          <el-tag size="small" type="warning">可修改</el-tag>
        </div>
        <el-button type="primary" class="service-button">
          定制内容
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </el-card>
      
      <el-card class="service-card" shadow="hover" @click="goToService('digital_art')">
        <div class="service-icon">🖼️</div>
        <h3 class="service-title">数字艺术内容定制</h3>
        <p class="service-description">
          专业数字艺术创作服务，涵盖抽象、写实、装置、动态艺术等多种风格。
          由资深艺术家团队倾力打造，3天内提供初稿预览。
        </p>
        <div class="service-features">
          <el-tag size="small">专业艺术家</el-tag>
          <el-tag size="small" type="success">3天初稿</el-tag>
          <el-tag size="small" type="info">多种风格</el-tag>
        </div>
        <el-button type="primary" class="service-button">
          艺术定制
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Document, Clock, CircleCheck, ArrowRight, View } from '@element-plus/icons-vue'
import { useOrderStore } from '@/stores/order'
import { useAuthStore } from '@/stores/auth'
import type { OrderType } from '@/types'

const router = useRouter()
const orderStore = useOrderStore()
const authStore = useAuthStore()

onMounted(() => {
  orderStore.fetchOrders()
})

const goToService = (type: OrderType) => {
  router.push(`/user/create-order/${type}`)
}

const goToOrders = () => {
  router.push('/user/orders')
}
</script>

<style lang="scss" scoped>
.workspace-page {
  padding: 24px;
}

.page-header {
  text-align: center;
  margin-bottom: 48px;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: #1D1D1F;
  margin: 0 0 12px 0;
}

.page-subtitle {
  font-size: 16px;
  color: #86868B;
  margin: 0;
}

.service-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 24px;
  margin-bottom: 48px;
}

.service-card {
  border-radius: 16px;
  padding: 32px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  
  &:hover {
    transform: translateY(-4px);
    border-color: #667eea;
    box-shadow: 0 12px 24px rgba(102, 126, 234, 0.15);
  }
  
  :deep(.el-card__body) {
    padding: 0;
  }
}

.service-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.service-title {
  font-size: 20px;
  font-weight: 600;
  color: #1D1D1F;
  margin: 0 0 12px 0;
}

.service-description {
  font-size: 14px;
  color: #86868B;
  line-height: 1.6;
  margin: 0 0 16px 0;
  min-height: 64px;
}

.service-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}

.service-button {
  width: 100%;
}

.my-orders-section {
  margin-top: 48px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-title {
  font-size: 24px;
  font-weight: 600;
  color: #1D1D1F;
  margin: 0;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.stat-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  
  :deep(.el-card__body) {
    padding: 20px;
  }
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #1D1D1F;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #86868B;
}
</style>




