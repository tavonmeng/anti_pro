<template>
  <section id="business" class="business-section">
    <div class="container">
      <h2>业务合作</h2>
      <div class="services-list">
        <div class="service-item">
          <span class="num">01</span>
          <h3>裸眼3D广告制作</h3>
          <p>针对各类大屏幕定制高冲击力的3D视频内容。</p>
        </div>
        <div class="service-item">
          <span class="num">02</span>
          <h3>品牌视觉创意</h3>
          <p>全案视觉策划与品牌形象升级。</p>
        </div>
        <div class="service-item">
          <span class="num">03</span>
          <h3>AI驱动内容生成</h3>
          <p>利用AIGC技术实现高效内容产出。</p>
        </div>
        <div class="service-item">
          <span class="num">04</span>
          <h3>数字媒体策划</h3>
          <p>从硬件到软件的整体解决方案。</p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.business-section {
  padding: 120px 40px;
  background-color: var(--color-bg-primary);
  color: #fff;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

h2 {
  font-size: 32px;
  margin-bottom: 60px;
}

.services-list {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 40px;
}

.service-item {
  padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,0.2);
  transition: border-color 0.3s;
}

.service-item:hover {
  border-color: var(--color-accent);
}

.num {
  display: block;
  font-size: 14px;
  color: var(--color-text-tertiary);
  margin-bottom: 20px;
  font-family: monospace;
}

.service-item h3 {
  font-size: 20px;
  margin-bottom: 15px;
}

.service-item p {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

@media (max-width: 1024px) {
  .services-list {
    grid-template-columns: repeat(2, 1fr);
    gap: 60px 40px;
  }
}

@media (max-width: 600px) {
  .services-list {
    grid-template-columns: 1fr;
  }
}
</style>
