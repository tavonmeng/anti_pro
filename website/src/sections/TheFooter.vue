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
        <h4>业务合作</h4>
        <ul>
          <li><a href="#">裸眼3D广告制作</a></li>
          <li><a href="#">品牌视觉创意</a></li>
          <li><a href="#">AI驱动内容生成</a></li>
          <li><a href="#">数字媒体策划</a></li>
        </ul>
      </div>
      <div class="col">
        <h4>联系我们</h4>
        <ul>
          <li><a href="#contact">项目联系</a></li>
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
  background-color: #fff;
  color: #000;
  padding: 15px 40px 15px; /* 高度增大 1.5 倍 */
  border-top: 1px solid #e0e0e0;
}

.footer-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px; /* 缩减水平间隙 */
  max-width: 1200px;
  margin: 0 auto 24px; /* 增大间距 */
}

h4 {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 12px; /* 增大间距 */
}

ul li {
  margin-bottom: 10px; /* 增大行距 */
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
  padding-top: 16px; /* 增大顶线与文字的内边距 */
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
