export type VideoLibraryMediaType = 'image' | 'video'

export interface VideoLibraryItem {
  id: string
  title: string
  type: string
  tag: string
  desc: string
  media: {
    type: VideoLibraryMediaType
    url: string
    poster?: string
  }
  price: {
    label: string
    display: string
    note: string
  }
  fitNotes: string[]
}

export const videoLibraryItems: VideoLibraryItem[] = [
  {
    id: '1',
    title: '赛博朋克深空穿越',
    type: '科幻奇境',
    tag: '飞行器穿梭',
    desc: '极具纵深感的宇宙飞行画面，机械部件极度写实，适合追求震撼冲击力的品牌展示。',
    media: {
      type: 'image',
      url: '/video-library-images/1.png',
    },
    price: {
      label: '成片适配起步价',
      display: '¥ 8,800起',
      note: '最终费用会根据屏幕比例、分辨率、品牌替换和适配深度确认。',
    },
    fitNotes: ['适合L型屏或大纵深屏幕', '可替换品牌露出与核心视觉元素', '支持按媒体规格做二次裁切和安全区适配'],
  },
  {
    id: '2',
    title: '未来机甲异星破阵',
    type: '硬科幻',
    tag: '机械跃出',
    desc: '巨型机甲从屏幕深处跳跃而出的裸眼3D大作，强烈的打破屏幕错觉。',
    media: {
      type: 'image',
      url: '/video-library-images/2.jpg',
    },
    price: {
      label: '成片适配起步价',
      display: '¥ 8,800起',
      note: '适配报价会结合屏幕结构、输出规格和品牌植入复杂度调整。',
    },
    fitNotes: ['适合科技、游戏、汽车等高能视觉场景', '可强化角色出屏和机械细节', '适合需要强第一眼冲击的投放点位'],
  },
  {
    id: '3',
    title: '数字生机奇幻绿洲',
    type: '超现实空间',
    tag: '自然奇观',
    desc: '数字花卉与晶体融合盛开，色彩艳丽，优雅高级，适合美妆或高端商业综合体宣发。',
    media: {
      type: 'image',
      url: '/video-library-images/3.jpg',
    },
    price: {
      label: '成片适配起步价',
      display: '¥ 8,800起',
      note: '最终费用取决于品牌元素替换、屏幕比例适配和交付版本数量。',
    },
    fitNotes: ['适合美妆、商业综合体和城市美陈内容', '可保留高饱和自然视觉资产', '适合偏艺术化和打卡传播的屏幕'],
  },
]

export const getVideoLibraryItemById = (id: string | number | undefined) => {
  const normalizedId = String(id || '')
  return videoLibraryItems.find(item => item.id === normalizedId) || null
}

export const buildVideoPurchaseQuery = (item: VideoLibraryItem) => ({
  selected_id: item.id,
  title: item.title,
  price: item.price.display,
  media_type: item.media.type,
  media_url: item.media.url,
})

export const buildVideoPurchaseRoute = (item: VideoLibraryItem) => ({
  path: '/user/create-order/video_purchase',
  query: buildVideoPurchaseQuery(item),
})
