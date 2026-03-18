<template>
  <section id="brands" class="brands-section" ref="sectionRef">
    <div class="brands-wrapper">
      <!-- 第一行品牌 -->
      <div class="brands-container" ref="track1Ref">
        <div class="brands-track" ref="track1Inner">
          <div v-for="brand in brandsRow1" :key="brand" class="brand-item">
            <span class="brand-name">{{ brand }}</span>
          </div>
          <div v-for="brand in brandsRow1" :key="brand + '_dup'" class="brand-item">
            <span class="brand-name">{{ brand }}</span>
          </div>
        </div>
      </div>
      
      <!-- 第二行品牌 -->
      <div class="brands-container" ref="track2Ref">
        <div class="brands-track" ref="track2Inner">
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
import { ref, onMounted, onUnmounted } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const sectionRef = ref(null)
const track1Ref = ref(null)
const track2Ref = ref(null)
const track1Inner = ref(null)
const track2Inner = ref(null)

let ctx

const brandsRow1 = [
  'DISNEY', 'LANCÔME', 'MARVIS', 'SULWHASOO', 
  'LANEIGE', 'SHU UEMURA', 'MERCEDES-BENZ', 
  'ARCFOX', 'L\'ORÉAL'
]

const brandsRow2 = [...brandsRow1].reverse()

onMounted(() => {
  ctx = gsap.context(() => {
    const t1Inner = track1Inner.value
    const t2Inner = track2Inner.value

    // 选中两行内部独立的所有品牌元素
    const items1 = t1Inner.querySelectorAll('.brand-item')
    const items2 = t2Inner.querySelectorAll('.brand-item')

    // ─── 阶段1: 品牌名字由下向上淡入 ─────────────────────
    // 初始状态：每一个名字单独隐藏 + 下移（距离大幅拉长，增强视觉冲击力）
    gsap.set([items1, items2], { 
      opacity: 0, 
      y: 150 
    })

    // 第一行品牌以波浪形式（逐个交错）淡入
    gsap.to(items1, {
      opacity: 1,
      y: 0,
      duration: 1.8, // 动画变长，使得减速过程更细腻漫长
      stagger: 0.05, // 每个品牌依次出现
      ease: 'power4.out', // 从 power3 升级为 power4，极其柔和的高级长尾减速曲线
      scrollTrigger: {
        trigger: sectionRef.value,
        start: 'top 75%', // 提前一点触发，体验更丝滑
        toggleActions: 'play none none reverse'
      },
      onComplete: () => {
        // 阶段2: 淡入完成后，启动水平无限滚动
        t1Inner.classList.add('scrolling-left')
      },
      onReverseComplete: () => {
        t1Inner.classList.remove('scrolling-left')
      }
    })

    // 第二行品牌以波浪形式淡入（整行动画比第一行晚一点触发）
    gsap.to(items2, {
      opacity: 1,
      y: 0,
      duration: 1.8,
      stagger: 0.05,
      delay: 0.2, // 第二行整体晚0.2秒启动
      ease: 'power4.out',
      scrollTrigger: {
        trigger: sectionRef.value,
        start: 'top 75%',
        toggleActions: 'play none none reverse'
      },
      onComplete: () => {
        t2Inner.classList.add('scrolling-right')
      },
      onReverseComplete: () => {
        t2Inner.classList.remove('scrolling-right')
      }
    })

  }, sectionRef.value)
})

onUnmounted(() => {
  if (ctx) ctx.revert()
})
</script>

<style scoped>
.brands-section {
  background-color: #fff;
  position: relative;
  border-bottom: 1px solid #f0f0f0;
  padding: 120px 0;
  overflow: hidden;
}

.brands-wrapper {
  display: flex;
  flex-direction: column;
  gap: 50px;
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
  white-space: nowrap;
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

@keyframes scrollLeft {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

@keyframes scrollRight {
  0% { transform: translateX(-50%); }
  100% { transform: translateX(0); }
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
