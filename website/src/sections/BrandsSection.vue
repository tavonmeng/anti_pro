<template>
  <section id="brands" class="brands-section">
    <div class="brands-container">
      <div class="brands-track">
        <div v-for="brand in brands" :key="brand" class="brand-item">
          <span class="brand-name">{{ brand }}</span>
        </div>
        <!-- 重复一遍实现无缝滚动效果 -->
        <div v-for="brand in brands" :key="brand + '_dup'" class="brand-item">
          <span class="brand-name">{{ brand }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const brands = [
  'DISNEY', 'LANCÔME', 'MARVIS', 'SULWHASOO', 
  'LANEIGE', 'SHU UEMURA', 'MERCEDES-BENZ', 
  'ARCFOX', 'L\'ORÉAL'
]
</script>

<style scoped>
.brands-section {
  background-color: #fff;
  padding: 60px 0;
  overflow: hidden;
  border-top: 1px solid #f0f0f0;
  border-bottom: 1px solid #f0f0f0;
}

.brands-container {
  display: flex;
  width: 100%;
}

.brands-track {
  display: flex;
  gap: 100px;
  animation: scroll 40s linear infinite;
  padding-left: 50px;
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
  .brands-track {
    gap: 60px;
  }
}
</style>
