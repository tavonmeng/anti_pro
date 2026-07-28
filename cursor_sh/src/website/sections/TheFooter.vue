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
            <img
              class="logo-icon"
              src="/landing/logo/official-mark-black.svg"
              alt="Unique Vision"
              width="32"
              height="48"
              loading="lazy"
              decoding="async"
            />
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
            <span class="social-icon is-placeholder" aria-label="TikTok 即将上线" title="TikTok 即将上线">
              <img src="/landing/icon/Tiktok_icon.svg" alt="" class="social-img" loading="lazy" decoding="async" />
            </span>
            <!-- 邮箱 -->
            <a href="mailto:support@uniquevisionx.com" class="social-icon" aria-label="邮箱" title="邮箱">
              <img src="/landing/icon/email-download-svgrepo-com.svg" alt="" class="social-img" loading="lazy" decoding="async" />
            </a>
            <!-- 微信 -->
            <span class="social-icon is-placeholder" aria-label="微信即将上线" title="微信即将上线">
              <img src="/landing/icon/wechat-logo-svgrepo-com.svg" alt="" class="social-img" loading="lazy" decoding="async" />
            </span>
            <!-- 知乎 -->
            <span class="social-icon is-placeholder" aria-label="知乎即将上线" title="知乎即将上线">
              <img src="/landing/icon/Zhihu_logo.svg" alt="" class="social-img" loading="lazy" decoding="async" />
            </span>
            <!-- 小红书 -->
            <span class="social-icon is-placeholder" aria-label="小红书即将上线" title="小红书即将上线">
              <img src="/landing/icon/xiaohongshu-seeklogo.svg" alt="" class="social-img" loading="lazy" decoding="async" />
            </span>
            <!-- 快手 -->
            <span class="social-icon is-placeholder" aria-label="快手即将上线" title="快手即将上线">
              <img src="/landing/icon/Kuaishou-OyH26YzFs_brandlogos.net.svg" alt="" class="social-img" loading="lazy" decoding="async" />
            </span>
          </div>
        </div>

        <!-- 右侧：导航链接三列 -->
        <nav class="footer-nav">
          <div class="nav-col">
            <h2 class="nav-title">
              <span class="nav-dot">■</span>
              业务合作
            </h2>
            <ul>
              <li><a href="#intro">3D OOH数字内容资源库</a></li>
              <li><a href="#intro">AI驱动3D OOH内容定制</a></li>
              <li><a href="#intro">数字艺术与沉浸式视觉设计</a></li>
              <li><a href="#intro">广告视觉与动态影像制作</a></li>
              <li><a href="#intro">户外媒体后期制作服务</a></li>
              <li><a href="#intro">广告投放分析与效果报告</a></li>
            </ul>
          </div>
          <div class="nav-col">
            <h2 class="nav-title">
              <span class="nav-dot">■</span>
              著作/专利
            </h2>
            <ul>
              <li><span>数字艺术</span></li>
              <li><span>裸眼3D</span></li>
              <li><span>AI-3D</span></li>
              <li><span>数字光影</span></li>
            </ul>
          </div>
          <div class="nav-col">
            <h2 class="nav-title">
              <span class="nav-dot">■</span>
              邮件联系
            </h2>
            <ul>
              <li><a href="mailto:support@uniquevisionx.com">support@uniquevisionx.com</a></li>
            </ul>
          </div>
        </nav>
      </div>
    </div>

    <div class="footer-bottom-divider"></div>

    <div class="footer-inner">
      <!-- 底部版权栏 -->
      <div class="footer-bottom">
        <span class="copyright">© 2026 Unique Vision. All rights reserved.</span>
        <a
          class="icp-record"
          href="https://beian.miit.gov.cn/"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="前往工业和信息化部备案管理系统查询京ICP备2026029893号-1"
        >
          京ICP备2026029893号-1
        </a>
        <div class="footer-legal">
          <span>使用条款</span>
          <span>隐私政策</span>
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
  width: 32px;
  height: 48px;
  display: block;
  flex-shrink: 0;
  object-fit: contain;
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

.social-icon.is-placeholder {
  cursor: default;
  opacity: 0.7;
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

.nav-col ul a,
.nav-col ul span {
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
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 24px;
}

.copyright {
  font-size: 11px;
  color: #999;
  letter-spacing: 0.02em;
  justify-self: start;
}

.icp-record {
  color: #777;
  font-size: 11px;
  letter-spacing: 0.02em;
  text-decoration: none;
  transition: color 0.2s;
}

.icp-record:hover {
  color: #111;
}

.footer-legal {
  display: flex;
  gap: 20px;
  justify-self: end;
}

.footer-legal a,
.footer-legal span {
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

  .footer-bottom {
    display: flex;
    flex-direction: column;
    gap: 10px;
    text-align: center;
  }

  .footer-legal {
    justify-content: center;
  }
}
</style>
