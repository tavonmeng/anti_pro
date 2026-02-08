<template>
  <section id="about" class="about-section">
    <div class="container">
      <div class="section-header">
        <h2>关于我们</h2>
        <div class="line"></div>
      </div>
      
      <div class="content">
        <p class="lead">
          Unique Vision 是一家专注于裸眼3D数字内容创作的科技公司。
        </p>
        <p>
          我们结合创意与AI技术，为全球品牌提供高质量的3D OOH广告内容。我们的团队由资深3D艺术家、AI工程师和创意策划组成，致力于让每一块屏幕都能展现震撼的视觉效果。
        </p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.about-section {
  padding: 120px 40px;
  background-color: var(--color-bg-secondary);
  color: #fff;
}

.container {
  max-width: 1000px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 60px;
}

.section-header h2 {
  font-size: 32px;
  margin-bottom: 20px;
}

.line {
  width: 40px;
  height: 2px;
  background: #fff;
}

.content {
  color: var(--color-text-secondary);
  font-size: 18px;
  line-height: 1.8;
}

.lead {
  font-size: 24px;
  color: #fff;
  margin-bottom: 30px;
}

@media (max-width: 768px) {
  .container {
    grid-template-columns: 1fr;
    gap: 40px;
  }
}
</style>
