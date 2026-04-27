<template>
  <section id="brands" class="brands-section" ref="sectionRef">
    <div class="brands-wrapper" ref="wrapperRef">
      <!-- 第一行品牌 -->
      <div class="brands-container" ref="track1Ref">
        <div class="brands-track" ref="track1Inner">
          <div v-for="brand in brandsRow1" :key="brand" class="brand-item">
            <img :src="brand" class="brand-logo" alt="Partner Logo" />
          </div>
          <div v-for="brand in brandsRow1" :key="brand + '_dup'" class="brand-item">
            <img :src="brand" class="brand-logo" alt="Partner Logo" />
          </div>
        </div>
      </div>
      
      <!-- 第二行品牌 -->
      <div class="brands-container" ref="track2Ref">
        <div class="brands-track" ref="track2Inner">
          <div v-for="brand in brandsRow2" :key="brand" class="brand-item">
            <img :src="brand" class="brand-logo" alt="Partner Logo" />
          </div>
          <div v-for="brand in brandsRow2" :key="brand + '_dup'" class="brand-item">
            <img :src="brand" class="brand-logo" alt="Partner Logo" />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const sectionRef = ref(null)
const wrapperRef = ref(null)
const track1Ref = ref(null)
const track2Ref = ref(null)
const track1Inner = ref(null)
const track2Inner = ref(null)

const allBrands = Array.from({ length: 14 }, (_, i) => `/landing/logo/black/brand${i + 15}.png`)
const brandsRow1 = allBrands.slice(0, 7)
const brandsRow2 = allBrands.slice(7)

onMounted(() => {
  // Start infinite scroll immediately
  if (track1Inner.value) track1Inner.value.classList.add('scrolling-left')
  if (track2Inner.value) track2Inner.value.classList.add('scrolling-right')

  // Smooth fade-in observer avoiding GSAP pinning bugs
  if (wrapperRef.value) {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        wrapperRef.value.classList.add('is-visible')
        observer.disconnect()
      }
    }, { threshold: 0.1, rootMargin: '0px 0px -100px 0px' })
    observer.observe(wrapperRef.value)
  }
})

</script>

<style scoped>
.brands-section {
  background-color: #fff; /* Reverted to white background */
  position: relative;
  border-bottom: 1px solid #f0f0f0;
  padding: 120px 0;
  overflow: hidden;
}

.brands-wrapper {
  display: flex;
  flex-direction: column;
  gap: 50px;
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 1.2s cubic-bezier(0.2, 0, 0.2, 1), transform 1.2s cubic-bezier(0.2, 0, 0.2, 1);
  will-change: opacity, transform;
}

.brands-wrapper.is-visible {
  opacity: 1;
  transform: translateY(0);
}

.brands-container {
  display: flex;
  width: 100%;
  will-change: transform, opacity;
}

.brands-track {
  display: flex;
  gap: 100px;
  padding-left: 50px;
  width: fit-content;
  /* 初始状态：不滚动 */
}

/* 阶段2：淡入完成后通过添加class启动水平滚动 */
.brands-track.scrolling-left {
  animation: scrollLeft 40s linear infinite;
}

.brands-track.scrolling-right {
  animation: scrollRight 45s linear infinite;
}

.brand-item {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: default;
  min-width: 150px;
  position: relative;
}

.brand-logo {
  height: 60px;
  width: auto;
  min-width: 60px;
  object-fit: contain;
  opacity: 0.8;
  filter: brightness(0); /* Make any white pixels black to render safely on white bg */
  transition: all 0.4s cubic-bezier(0.2, 0, 0.2, 1);
  will-change: transform, opacity;
}

.brand-item:hover .brand-logo {
  opacity: 1;
  filter: brightness(0) drop-shadow(0 4px 10px rgba(0,0,0,0.15));
  transform: translateY(-3px) scale(1.05);
}

@keyframes scrollLeft {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

@keyframes scrollRight {
  0% { transform: translateX(-50%); }
  100% { transform: translateX(0); }
}

@media (max-width: 768px) {
  .brand-logo {
    height: 45px;
  }
  .brands-wrapper {
    gap: 30px;
  }
  .brands-track {
    gap: 60px;
  }
}
</style>
