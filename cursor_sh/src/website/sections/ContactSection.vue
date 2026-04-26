<template>
  <section id="contact" class="contact-section" ref="sectionRef">
    <!-- 顶部朦胧渐变遮罩 -->
    <div class="fade-overlay" ref="overlayRef"></div>
    <!-- 确保下方背景为白色的底图 -->
    <div class="solid-white-bg"></div>

    <div class="container contact-container">
      <p class="sub-label">有项目想法？</p>
      
      <!-- 无限滚动跑马灯 -->
      <div class="marquee-container" @mouseenter="isHover = true" @mouseleave="isHover = false">
        <div class="marquee-track" :class="{ 'is-paused': isHover }">
          <div class="marquee-content">
            <span class="cta-heading" v-for="i in 8" :key="'a'+i">给我们留个消息。</span>
          </div>
          <div class="marquee-content">
            <span class="cta-heading" v-for="i in 8" :key="'b'+i">给我们留个消息。</span>
          </div>
        </div>
      </div>

      <div class="action-container">
        <div class="contact-card">
          <a href="mailto:mlm3344521@163.com" class="email-link">
            mlm3344521@163.com
          </a>
        </div>
        <div class="contact-card ai-card">
          <a :href="dashboardUrl + '/user/workspace'" class="email-link">
            找AI向导
          </a>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const isHover = ref(false)
const sectionRef = ref(null)
const overlayRef = ref(null)

// 动态判断应用跳转地址，优先使用部署时注入的环境变量
// 如果没有，判断是否为本地开发环境(localhost)，是则跳转到 3000，否则推导当前域名+8080端口(生产环境部署端口)
const dashboardUrl = import.meta.env.VITE_DASHBOARD_URL || 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? `${window.location.protocol}//${window.location.hostname}:3000`
    : `${window.location.protocol}//${window.location.hostname}:8080`)

let ctx

onMounted(() => {
  ctx = gsap.context(() => {
    // 动态在页面滑上去（进入contact section）时，渐显遮罩层，避免遮挡最后一个案例被 pinned 时的视觉
    gsap.fromTo(overlayRef.value, 
      { opacity: 0 },
      { 
        opacity: 1,
        scrollTrigger: {
          trigger: sectionRef.value,
          start: 'top bottom', // 当contact top刚接触视口底部，也就是cases刚刚结束pin开始往上滑时
          end: 'top 85%', // 滑动到15vh高度左右时完全显现白边渐变
          scrub: true
        }
      }
    )
  }, sectionRef.value)
})

onUnmounted(() => {
  if (ctx) ctx.revert()
})
</script>

<style scoped>
.contact-section {
  position: relative;
  margin-top: -15vh; /* 重新启用负边距，15vh 覆盖在上一区块的尾部 */
  padding: 14vh 0 50px;
  background-color: transparent; 
  color: #000;
  z-index: 1000;
}

.fade-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 15vh;
  background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 50%, rgba(255,255,255,1) 100%);
  z-index: -1;
  pointer-events: none;
  opacity: 0; /* 默认隐藏，通过 GSAP 动画渐渐浮现 */
}

.solid-white-bg {
  position: absolute;
  top: 15vh; /* 与高度匹配 */
  left: 0;
  width: 100%;
  height: calc(100% - 15vh);
  background: #fff;
  z-index: -1;
}

.contact-container {
  max-width: 100%;
  margin: 0 auto; 
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  overflow: hidden; /* 防止跑马灯出现系统底部横向滚动条 */
}

.sub-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px; /* 极度压窄 */
  z-index: 10;
}

/* 跑马灯动画 */
.marquee-container {
  width: 100vw;
  margin-bottom: 20px; /* 砍掉一半留白，极度压窄 */
  display: flex;
  position: relative;
  z-index: 10;
}

.marquee-track {
  display: flex;
  width: max-content;
  animation: scroll-left 50s linear infinite; /* 放慢循环速度 */
  will-change: transform;
}

.marquee-track.is-paused {
  animation-play-state: paused;
}

.marquee-content {
  display: flex;
  white-space: nowrap;
}

.cta-heading {
  font-size: 5vw; /* 让文字紧凑、具有屏幕张力 */
  font-weight: 300; /* 去除原本非常粗的设定，变得更加克制高级 */
  padding-right: 3vw; /* 每条标语之前的间隔 */
  color: #000;
  cursor: default;
}

@keyframes scroll-left {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

.action-container {
  display: flex;
  gap: 20px;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  z-index: 10;
}

.contact-card {
  background: #000;
  padding: 16px 48px; /* 加大胶囊体积 */
  border-radius: 60px; /* 大号圆角，保持胶囊形状 */
  transition: transform 0.3s ease, background 0.3s ease;
  z-index: 10;
}

.contact-card:hover {
  transform: translateY(-3px);
}

.email-link {
  color: #fff;
  font-size: 24px; /* 加大邮箱字号 */
  font-family: monospace;
  text-decoration: none;
  letter-spacing: 1px;
}

/* --- 响应式 --- */
@media (max-width: 768px) {
  .cta-heading {
    font-size: 8vw;
    padding-right: 6vw;
  }
  .contact-section {
    padding-top: 15vh;
  }
}
</style>
