<template>
  <section id="brands" class="brands-section">
    <!-- 顶部渐变过渡 (黑白平滑过渡) -->
    <div class="transition-gradient"></div>

    <div class="brands-wrapper">
      <!-- 第一行品牌 -->
      <div class="brands-container">
        <div class="brands-track track-1">
          <div v-for="brand in brandsRow1" :key="brand" class="brand-item">
            <span class="brand-name">{{ brand }}</span>
          </div>
          <div v-for="brand in brandsRow1" :key="brand + '_dup'" class="brand-item">
            <span class="brand-name">{{ brand }}</span>
          </div>
        </div>
      </div>
      
      <!-- 第二行品牌 -->
      <div class="brands-container">
        <div class="brands-track track-2">
          <div v-for="brand in brandsRow2" :key="brand" class="brand-item">
            <span class="brand-name">{{ brand }}</span>
          </div>
          <div v-for="brand in brandsRow2" :key="brand + '_dup'" class="brand-item">
            <span class="brand-name">{{ brand }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const brandsRow1 = [
  'DISNEY', 'LANCÔME', 'MARVIS', 'SULWHASOO', 
  'LANEIGE', 'SHU UEMURA', 'MERCEDES-BENZ', 
  'ARCFOX', 'L\'ORÉAL'
]

// 稍微打乱顺序或者使用更多品牌作为第二行
const brandsRow2 = [...brandsRow1].reverse()
</script>

<style scoped>
.brands-section {
  background-color: #fff;
  position: relative;
  border-bottom: 1px solid #f0f0f0;
}

.transition-gradient {
  width: 100%;
  height: 30vh; /* 增高渐变区域让过渡更加漫长柔和 */
  background: linear-gradient(
    to bottom, 
    #000 0%, 
    rgba(0,0,0,0.8) 30%,
    rgba(0,0,0,0.4) 60%,
    rgba(0,0,0,0.1) 85%,
    #fff 100%
  );
}

.brands-wrapper {
  padding: 60px 0 80px 0; /* 控制下部的留边 */
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 50px; /* 两行之间的间距 */
}

.brands-container {
  display: flex;
  width: 100%;
}

.brands-track {
  display: flex;
  gap: 100px;
  padding-left: 50px;
  width: fit-content;
}

.track-1 {
  animation: scroll 40s linear infinite;
}

.track-2 {
  /* 第二行反向滚动且稍微慢一点 */
  animation: scroll 45s linear infinite reverse;
}

.brand-item {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: default;
}

.brand-name {
  font-size: 28px;
  font-weight: 800;
  color: #000;
  font-family: 'Outfit', sans-serif;
  letter-spacing: 4px;
  opacity: 0.7;
  transition: all 0.4s cubic-bezier(0.2, 0, 0.2, 1);
  position: relative;
}

.brand-name::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  width: 0;
  height: 2px;
  background-color: #000;
  transition: width 0.4s ease;
}

.brand-item:hover .brand-name {
  opacity: 1;
  transform: translateY(-2px);
}

.brand-item:hover .brand-name::after {
  width: 100%;
}

@keyframes scroll {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

@media (max-width: 768px) {
  .brand-name {
    font-size: 18px;
    letter-spacing: 2px;
  }
  .brands-wrapper {
    gap: 30px;
  }
  .brands-track {
    gap: 60px;
  }
}
</style>
