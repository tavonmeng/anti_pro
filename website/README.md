# Unique Vision Website

3D OOH 数字内容平台官网首页前端项目。

## 技术栈

- **前端框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **语言**: JavaScript
- **样式**: CSS3 Variables

## 快速开始

本项目已配置本地 Node.js 环境，无需全局安装 Node.js。

### 1. 启动项目

在项目根目录运行启动脚本：

```bash
./start_website.sh
```

这将自动设置环境并启动本地开发服务器。

### 2. 访问网站

打开浏览器访问: http://localhost:5173

## 项目结构

```
/anti_project
├── start_website.sh      # 启动脚本
├── tools/                # 本地 Node.js 环境
├── website/              # 前端源码
│   ├── src/
│   │   ├── components/   # 通用组件 (Header, Menu, etc.)
│   │   ├── sections/     # 页面各个板块 (Hero, Cases, etc.)
│   │   ├── composables/  # 逻辑复用 (如鼠标特效)
│   │   └── assets/       # 静态资源 (CSS, Images)
│   └── public/           # 视频文件
```

## 功能特性

- **Hero 视频背景**: 全屏视频播放
- **鼠标交互**: 光晕跟随 + 附近文字放大特效
- **页面进度条**: 顶部白色进度条随滚动变化
- **全屏菜单**: 汉堡菜单展开全屏导航
- **响应式布局**: 适配不同尺寸屏幕

---
© 2024 Unique Vision
