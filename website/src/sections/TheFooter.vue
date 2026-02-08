<template>
  <footer class="footer">
    <div class="footer-grid">
      <div class="col">
        <h4>著作/专利</h4>
        <ul>
          <li><a href="#">相关资质</a></li>
          <li><a href="#">知识产权</a></li>
        </ul>
      </div>
      <div class="col">
        <h4>关于我们</h4>
        <ul>
          <li><a href="#about">团队介绍</a></li>
          <li><a href="#">加入我们</a></li>
        </ul>
      </div>
      <div class="col">
        <h4>业务合作</h4>
        <ul>
          <li><a href="#cases">案例展示</a></li>
          <li><a href="#business">服务流程</a></li>
        </ul>
      </div>
      <div class="col">
        <h4>联系我们</h4>
        <ul>
          <li><a href="#contact">在线咨询</a></li>
          <li><a href="#">地理位置</a></li>
        </ul>
      </div>
    </div>
    
    <div class="footer-bottom">
      <div class="brand-slogan">
        让内容更高效 让屏幕更有价值 <span class="arrow">→</span>
      </div>
      <div class="legal">
        <a href="#">使用条款</a>
        <a href="#">隐私政策</a>
        <span class="copyright">© 2024 Unique Vision. All rights reserved.</span>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  background-color: #f5f5f5;
  color: #000;
  padding: 80px 40px 40px;
  border-top: 1px solid #e0e0e0;
}

.footer-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 40px;
  max-width: 1200px;
  margin: 0 auto 80px;
}

h4 {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 20px;
}

ul li {
  margin-bottom: 12px;
}

ul a {
  font-size: 14px;
  color: #666;
  transition: color 0.2s;
}

ul a:hover {
  color: #000;
}

.footer-bottom {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-top: 40px;
  border-top: 1px solid #e0e0e0;
}

.brand-slogan {
  font-weight: 700;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.legal {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: #666;
}

.legal a {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .footer-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .footer-bottom {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }
}
</style>
