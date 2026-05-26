import type { OrderType } from '@/types'

export type ServiceType =
  | OrderType
  | 'motion_content'
  | 'media_post_production'
  | 'campaign_analytics'

export interface PlatformService {
  type: ServiceType
  title: string
  subtitle: string
  description: string
  badge: string
  gradient: string
  features: string[]
  footer: string
  orderable: boolean
}

export const platformServices: PlatformService[] = [
  {
    type: 'video_purchase',
    title: '3D OOH数字内容资源库',
    subtitle: '3D DOOH Content Library',
    description: '即用型裸眼3D数字内容资产 / 多屏适配内容方案 / 全球地标大屏内容规格适配',
    badge: '01｜3D DOOH Content Library',
    gradient: 'linear-gradient(135deg, #111111 0%, #303842 52%, #5d6f82 100%)',
    features: ['即用型裸眼3D数字内容资产', '多屏适配内容方案', '全球地标大屏内容规格适配'],
    footer: 'Ready-to-Deploy 3D DOOH Assets',
    orderable: true
  },
  {
    type: 'ai_3d_custom',
    title: 'AI驱动3D OOH内容定制',
    subtitle: 'AI-Driven 3D DOOH Custom Production',
    description: 'AI创意内容开发 / 场景化裸眼3D空间适配 / 真实环境播放模拟 / 一站式DOOH内容制作',
    badge: '02｜AI-Driven 3D DOOH Custom Production',
    gradient: 'linear-gradient(135deg, #0b1f33 0%, #0f5b8f 48%, #3fb8af 100%)',
    features: ['AI创意内容开发', '场景化裸眼3D空间适配', '真实环境播放模拟', '一站式DOOH内容制作'],
    footer: 'End-to-End DOOH Content Production',
    orderable: true
  },
  {
    type: 'digital_art',
    title: '数字艺术与沉浸式视觉设计',
    subtitle: 'Digital Art & Immersive Visual Design',
    description: '艺术指导与视觉设计 / 虚拟装置艺术 / 沉浸式空间视觉 / 实验性数字艺术内容',
    badge: '03｜Digital Art & Immersive Visual Design',
    gradient: 'linear-gradient(135deg, #32121a 0%, #8b2337 50%, #f0764f 100%)',
    features: ['艺术指导与视觉设计', '虚拟装置艺术', '沉浸式空间视觉', '实验性数字艺术内容'],
    footer: 'Experimental Digital Art Content',
    orderable: true
  },
  {
    type: 'motion_content',
    title: '广告视觉与动态影像制作',
    subtitle: 'Advertising & Motion Content Production',
    description: '平面广告视觉设计 / TVC广告影片制作 / FOOH数字传播内容 / VJ视觉演出内容 / 动态视觉设计',
    badge: '04｜Advertising & Motion Content Production',
    gradient: 'linear-gradient(135deg, #17202a 0%, #7d3c98 48%, #f4d03f 100%)',
    features: ['平面广告视觉设计', 'TVC广告影片制作', 'FOOH数字传播内容', 'VJ视觉演出内容', '动态视觉设计'],
    footer: 'Motion Graphic Design',
    orderable: false
  },
  {
    type: 'media_post_production',
    title: '户外媒体后期制作服务',
    subtitle: 'Outdoor Media Post-Production Services',
    description: '高端精修图像处理 / 电影级视频精修 / CGI视觉增强 / 商业摄影与视频拍摄 / 航拍影像制作',
    badge: '05｜Outdoor Media Post-Production Services',
    gradient: 'linear-gradient(135deg, #1c2833 0%, #566573 45%, #d5dbdb 100%)',
    features: ['高端精修图像处理', '电影级视频精修', 'CGI视觉增强', '商业摄影与视频拍摄', '航拍影像制作'],
    footer: 'Cinematic Video Finishing',
    orderable: false
  },
  {
    type: 'campaign_analytics',
    title: '广告投放分析与效果报告',
    subtitle: 'Campaign Analytics & Performance Reporting',
    description: 'DOOH广告投放数据分析 / 受众效果分析报告 / 视觉传播效果评估 / 可下载数据报告系统',
    badge: '06｜Campaign Analytics & Performance Reporting',
    gradient: 'linear-gradient(135deg, #102027 0%, #00796b 48%, #cddc39 100%)',
    features: ['DOOH广告投放数据分析', '受众效果分析报告', '视觉传播效果评估', '可下载数据报告系统'],
    footer: 'Downloadable Data Reports',
    orderable: false
  }
]

export const orderableServiceTypes = platformServices
  .filter((service) => service.orderable)
  .map((service) => service.type) as OrderType[]

export const getServiceByType = (type: string) => {
  return platformServices.find((service) => service.type === type)
}

export const getServiceBadgeLabel = (badge: string) => {
  return badge.replace(/^\d+\s*[｜|]\s*/, '')
}

export const isOrderableServiceType = (type: string): type is OrderType => {
  return orderableServiceTypes.includes(type as OrderType)
}
