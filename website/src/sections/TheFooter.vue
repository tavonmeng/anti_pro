<template>
  <footer class="footer">

    <!-- 顶部分割线 -->
    <div class="footer-divider-full"></div>

    <div class="footer-inner">

      <!-- 主体区域 -->
      <div class="footer-main">

        <!-- 左侧：Logo + 口号 + 社交图标 -->
        <div class="footer-left">
          <div class="footer-logo">
            <!-- Unique Vision Logo: 盾牌形图标 -->
            <svg class="logo-icon" viewBox="0 0 32 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <!-- 盾牌外框 -->
              <path d="M16 1L2 7V17C2 25.5 8 32 16 35C24 32 30 25.5 30 17V7L16 1Z" stroke="#111" stroke-width="2" fill="none"/>
              <!-- 内部 U 形条纹 -->
              <path d="M9 12V22C9 25.5 12 28 16 28C20 28 23 25.5 23 22V12" stroke="#111" stroke-width="2.2" fill="none" stroke-linecap="round"/>
              <line x1="16" y1="12" x2="16" y2="24" stroke="#111" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <div class="logo-text">
              <span class="logo-line">Unique</span>
              <span class="logo-line">Vision</span>
            </div>
          </div>

          <a class="footer-slogan" href="#contact">
            <span class="slogan-text">让内容更高效 让屏幕更有价值</span>
            <svg class="slogan-arrow" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <line x1="4" y1="12" x2="20" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              <polyline points="14,6 20,12 14,18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
            </svg>
          </a>

          <!-- 社交图标：抖音、邮箱、微信、知乎、小红书、快手 -->
          <div class="footer-socials">
            <!-- TikTok -->
            <a href="#" class="social-icon" aria-label="TikTok" title="TikTok">
              <img src="/icon/Tiktok_icon.svg" alt="TikTok" class="social-img" />
            </a>
            <!-- 邮箱 -->
            <a href="mailto:contact@uniquevision.cn" class="social-icon" aria-label="邮箱" title="邮箱">
              <img src="/icon/email-download-svgrepo-com.svg" alt="邮箱" class="social-img" />
            </a>
            <!-- 微信 -->
            <a href="#" class="social-icon" aria-label="微信" title="微信">
              <img src="/icon/wechat-logo-svgrepo-com.svg" alt="微信" class="social-img" />
            </a>
            <!-- 知乎 -->
            <a href="#" class="social-icon" aria-label="知乎" title="知乎">
              <img src="/icon/Zhihu_logo.svg" alt="知乎" class="social-img" />
            </a>
            <!-- 小红书 -->
            <a href="#" class="social-icon" aria-label="小红书" title="小红书">
              <img src="/icon/xiaohongshu-seeklogo.svg" alt="小红书" class="social-img" />
            </a>
            <!-- 快手 -->
            <a href="#" class="social-icon" aria-label="快手" title="快手">
              <img src="/icon/Kuaishou-OyH26YzFs_brandlogos.net.svg" alt="快手" class="social-img" />
            </a>
          </div>
        </div>

        <!-- 右侧：导航链接三列 -->
        <nav class="footer-nav">
          <div class="nav-col">
            <h5 class="nav-title">
              <span class="nav-dot">■</span>
              业务合作
            </h5>
            <ul>
              <li><a href="#">裸眼3D广告制作</a></li>
              <li><a href="#">品牌视觉创意</a></li>
              <li><a href="#">AI驱动内容生成</a></li>
              <li><a href="#">数字媒体策划</a></li>
            </ul>
          </div>
          <div class="nav-col">
            <h5 class="nav-title">
              <span class="nav-dot">■</span>
              著作/专利
            </h5>
            <ul>
              <li><a href="#">数字艺术</a></li>
              <li><a href="#">裸眼3D</a></li>
              <li><a href="#">AI-3D</a></li>
              <li><a href="#">数字光影</a></li>
            </ul>
          </div>
          <div class="nav-col">
            <h5 class="nav-title">
              <span class="nav-dot">■</span>
              联系我们
            </h5>
            <ul>
              <li><a href="#contact">项目联系</a></li>
              <li><a href="#">地理位置</a></li>
            </ul>
          </div>
        </nav>
      </div>
    </div>

    <div class="footer-bottom-divider"></div>

    <div class="footer-inner">
      <!-- 底部版权栏 -->
      <div class="footer-bottom">
        <span class="copyright">© 2025 Unique Vision. All rights reserved.</span>
        <div class="footer-legal">
          <a href="#" @click.prevent="$emit('open-experiment')">✨ 3D Lab</a>
          <a href="#">使用条款</a>
          <a href="#">隐私政策</a>
        </div>
      </div>

    </div>
  </footer>
</template>

<style scoped>
.footer {
  background-color: #fff;
  color: #111;
  font-family: 'Inter', 'PingFang SC', 'Helvetica Neue', sans-serif;
}

.footer-inner {
  width: 100%;
  padding: 0 48px;
}

/* 顶部分割线 */
.footer-divider-full {
  height: 1px;
  background-color: #d8d8d8;
  width: 100%;
}

/* 主体布局 */
.footer-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 40px;
  padding-top: 40px;
  padding-bottom: 36px;
}

/* ======= 左侧 ======= */
.footer-left {
  display: flex;
  flex-direction: column;
  gap: 24px;
  flex-shrink: 0;
  max-width: 280px;
}

/* Logo */
.footer-logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 34px;
  height: 38px;
  flex-shrink: 0;
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.logo-line {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #111;
}

/* 口号 + 箭头 */
.footer-slogan {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  font-weight: 500;
  color: #111;
  text-decoration: none;
  border-bottom: 1px solid #111;
  padding-bottom: 6px;
  width: fit-content;
  transition: opacity 0.2s;
}

.footer-slogan:hover {
  opacity: 0.6;
}

.slogan-arrow {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  transition: transform 0.25s ease;
}

.footer-slogan:hover .slogan-arrow {
  transform: translateX(4px);
}

/* 社交图标 - 无边框 */
.footer-socials {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.social-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  color: #333;
  text-decoration: none;
  transition: color 0.2s, transform 0.2s;
}

.social-icon svg {
  width: 22px;
  height: 22px;
}

.social-img {
  width: 22px;
  height: 22px;
  object-fit: contain;
  transition: transform 0.2s, opacity 0.2s;
}

.social-img:hover {
  opacity: 0.7;
}

.social-icon:hover {
  color: #000;
  transform: scale(1.15);
}

/* ======= 右侧导航 ======= */
.footer-nav {
  display: flex;
  gap: clamp(64px, 6vw, 160px);
  flex-shrink: 0;
  padding-top: 2px;
}

.nav-col {
  display: flex;
  flex-direction: column;
  gap: clamp(14px, 1.5vw, 24px);
  min-width: 110px;
}

.nav-title {
  font-size: 13px;
  font-weight: 700;
  color: #111;
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 2px 0;
  letter-spacing: 0.02em;
}

.nav-dot {
  font-size: 7px;
  color: #111;
  line-height: 1;
  position: relative;
  top: -1px;
}

.nav-col ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.nav-col ul li {
  line-height: 1;
}

.nav-col ul a {
  font-size: 13px;
  color: #666;
  text-decoration: none;
  transition: color 0.2s;
  line-height: 1.4;
}

.nav-col ul a:hover {
  color: #111;
}

/* ======= 底部版权 ======= */
.footer-bottom-divider {
  height: 1px;
  background-color: #e8e8e8;
  width: 100%;
}

.footer-bottom {
  padding: 16px 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.copyright {
  font-size: 11px;
  color: #999;
  letter-spacing: 0.02em;
}

.footer-legal {
  display: flex;
  gap: 20px;
}

.footer-legal a {
  font-size: 11px;
  color: #999;
  text-decoration: none;
  transition: color 0.2s;
}

.footer-legal a:hover {
  color: #111;
}

/* ======= 响应式 ======= */
@media (max-width: 900px) {
  .footer-inner {
    padding: 0 24px;
  }

  .footer-main {
    flex-direction: column;
    gap: 32px;
  }

  .footer-nav {
    gap: 32px;
  }

  .footer-left {
    max-width: 100%;
  }
}

@media (max-width: 540px) {
  .footer-nav {
    flex-wrap: wrap;
    gap: 24px;
  }
}
</style>
