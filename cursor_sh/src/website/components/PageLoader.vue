<template>
  <div class="page-loader" ref="loaderRef">
    <!-- 文字区域 (随进度条完成而消失) -->
    <div class="text-group">
      <div class="loading-label">Loading</div>
      <div class="percent-tracker" :style="{ left: Math.max(progressValue, 10) + '%' }">
        <!-- 保持一个最小边距不溢出版面，同时挂在末端内侧避免超出全宽 -->
        <span class="percent-text">{{ Math.floor(progressValue) }}%</span>
      </div>
    </div>

    <!-- 进度黑线 (从居左向右延伸变宽) -->
    <div class="progress-line" ref="lineRef"></div>

    <!-- 底部 Unique Vision 标识 -->
    <div class="bottom-brand">UNIQUE VISION</div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import gsap from 'gsap'

const emit = defineEmits(['complete'])
const loaderRef = ref(null)
const lineRef = ref(null)
const progressValue = ref(0) 

onMounted(() => {
  // 禁止页面滚动
  document.body.style.overflow = 'hidden'

  const tl = gsap.timeline({
    onComplete: () => {
      // 允许滚动并解绑
      document.body.style.overflow = ''
      emit('complete')
      // 最后将整个loader面板硬裁切或渐隐消失
      gsap.to(loaderRef.value, { autoAlpha: 0, duration: 0.5, delay: 0.2 })
    }
  })

  // 虚拟对象用于GSAP驱动数字进度
  const proxy = { value: 0 }

  // 1. 百分比数字跟着跑（数值从 0 到 100）
  tl.to(proxy, {
    value: 100,
    duration: 1.8,
    ease: 'power2.inOut',
    onUpdate: () => {
      progressValue.value = proxy.value
    }
  }, "start")
  
  // 1.1 黑线长度从 0% 生长到 100%（因为CSS设置了left:0，所以是从左向右展开）
  tl.fromTo(lineRef.value, 
    { width: '0%', height: '5px' }, // 这里加宽到了 5px
    { width: '100%', duration: 1.8, ease: 'power2.inOut' },
    "start"
  )

  // 2. 当到达进度末尾时，立即隐藏 Loading，百分比，以及底部的品牌文字
  tl.to('.text-group, .bottom-brand', {
    autoAlpha: 0,
    duration: 0.2
  }, "-=0.2")

  // 3. 翻转感官极强的一幕：这条黑线从屏幕中央 猛然垂直扩张吞没整个画布
  .to(lineRef.value, {
    height: '100vh',
    duration: 0.8,
    ease: 'power4.inOut' 
  })
})
</script>

<style scoped>
.page-loader {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100vh;
  background-color: #fff; /* 默认纯白背景 */
  z-index: 9999;
}

/* 轨道基准定位设定在正中间，所以文字放它上面即可 */
.text-group {
  position: absolute;
  top: calc(50% - 24px); /* 黑线上方 24px 位置 */
  left: 0;
  width: 100vw;
}

.loading-label {
  position: absolute;
  left: 3vw; 
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 3px;
  color: #000;
  text-transform: uppercase;
}

.percent-tracker {
  position: absolute;
  /* 使用 -100% 将百分比数字反向吸附在生长黑线的尾端内侧 */
  /* 这能保证当左侧进度0%启动或者涨满100%时，字体本身都不会由于字宽而溢出屏幕之外造成布局横向滚动条 */
  transform: translateX(calc(-100% - 10px));
}

.percent-text {
  font-size: 15px;
  font-weight: 500;
  color: #000;
  font-variant-numeric: tabular-nums;
}

.progress-line {
  background-color: #000; 
  width: 0;
  height: 5px; /* 加粗的进度条 */
  position: absolute;
  top: 50%;
  left: 0; /* 限定居左，自然生长效果 */
  transform: translateY(-50%); /* 让它保持垂直严格居中，这样扩展高度为 100vh 时就是均匀占满上下 */
}

.bottom-brand {
  position: absolute;
  bottom: 5vh;
  left: 0;
  width: 100%;
  text-align: center;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 12px;
  letter-spacing: 5px;
  color: #000;
  font-weight: 600;
}

/* 适配：为了防止到达100%时字超出右侧 */
/* 这里我们对 percent-tracker 加上了 padding 限制溢出 */
@media (max-width: 768px) {
  .percent-tracker {
    transform: translateX(5px);
  }
}
</style>
