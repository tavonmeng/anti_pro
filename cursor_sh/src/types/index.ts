// 用户角色类型
export type UserRole = 'admin' | 'user' | 'staff'

// 订单类型
export type OrderType = 'video_purchase' | 'ai_3d_custom' | 'digital_art'

// 消息通知类型
export type NotificationType = 
  | 'order_status_changed'  // 订单状态变更
  | 'order_assigned'        // 订单分配
  | 'order_reassigned'      // 订单重新分配
  | 'new_feedback'          // 新反馈
  | 'preview_ready'         // 预览文件就绪
  | 'order_completed'       // 订单完成
  | 'order_cancelled'       // 订单取消
  | 'revision_needed'       // 需要修改
  | 'preview_review_required'   // 预览待审核
  | 'preview_review_approved'   // 预览审核通过
  | 'preview_review_rejected'   // 预览审核拒绝

// 订单状态
export type OrderStatus = 
  | 'draft'                // 草稿
  | 'pending_assign'       // 待分配
  | 'in_production'        // 制作中
  | 'pending_review'       // 待审核
  | 'preview_ready'        // 初稿预览
  | 'review_rejected'      // 审核拒绝
  | 'revision_needed'      // 需要修改
  | 'final_preview'        // 终稿预览
  | 'completed'            // 已完成
  | 'cancelled'            // 已取消

// 行业类型
export type IndustryType = 'movie' | 'outdoor' | 'custom'

// 视觉风格
export type VisualStyle = 'scifi' | 'realistic' | 'custom'

// 艺术方向
export type ArtDirection = 'abstract' | 'realistic' | 'installation' | 'dynamic' | 'custom'

// 用户接口
export interface User {
  id: string
  username: string
  role: UserRole
  email?: string
  avatar?: string
  realName?: string  // 真实姓名，用于负责人显示
  isActive?: boolean  // 是否启用
  orderCount?: number  // 负责的订单数量
  createdAt?: string  // 创建时间
  updatedAt?: string  // 更新时间
}

// 上传文件信息
export interface UploadedFile {
  id: string
  name: string
  size: number
  type: string
  uploadTime: string
  url?: string  // 模拟存储路径
}

// 预览历史记录
export interface PreviewHistory {
  id: string
  files: UploadedFile[]
  note: string
  createdAt: string
  createdBy: string
  createdByName: string
  previewType: 'initial' | 'final'  // 初稿或终稿
  reviewStatus: 'pending' | 'approved' | 'rejected'
  reviewNote?: string
  reviewedAt?: string | null
  reviewedBy?: string | null
  reviewedByName?: string | null
}

// 客户反馈
export interface OrderFeedback {
  id: string
  orderId: string
  content: string
  type: 'approval' | 'revision'  // 确认或修改
  createdAt: string
  createdBy: string
  createdByName?: string
}

// 时间线项目（预览或反馈）
export type TimelineItem = 
  | { type: 'preview'; data: PreviewHistory }
  | { type: 'feedback'; data: OrderFeedback }

// 基础订单接口
export interface BaseOrder {
  id: string
  orderNumber: string          // 项目编号
  orderType: OrderType         // 订单类型
  status: OrderStatus          // 订单状态
  userId: string               // 用户ID
  userName?: string            // 用户名
  assignees?: Array<{ id: string, name: string }>  // 当前负责人列表
  createdAt: string
  updatedAt: string
  feedbacks: OrderFeedback[]   // 客户反馈记录
  previewHistory?: PreviewHistory[]  // 预览历史记录
  pendingReviewPreviewIds?: string[]
  revisionCount: number        // 修改次数
}

// 裸眼3D成片购买订单
export interface VideoPurchaseOrder extends BaseOrder {
  orderType: 'video_purchase'
  industryType: IndustryType
  customIndustry?: string
  visualStyle: VisualStyle
  customStyle?: string
  duration: number             // 时长(秒)
  priceRange: { min: number; max: number }
  resolution: string
  size: string
  curvature?: string
}

// AI裸眼3D内容定制订单
export interface AI3DCustomOrder extends BaseOrder {
  orderType: 'ai_3d_custom'
  brand?: string               // 品牌与产品关键词
  background?: string          // 项目背景
  target_group?: string        // 目标受众
  brand_tone?: string          // 品牌调性
  content?: string             // 内容需求
  style?: string               // 风格偏好
  prohibited_content?: string  // 品牌禁忌内容
  city?: string                // 投放城市或站点
  media_size?: string          // 投放媒体及尺寸
  time_number?: string         // 投放时长与数量
  technology?: string          // 技术需求
  budget?: string              // 制作预算
  online_time?: string         // 预计上刊时间
  sales_contact?: string       // 销售对接人
  scenePhotos?: UploadedFile[] // 现场实拍图
  previewFiles?: UploadedFile[] // 预览文件
  previewNote?: string         // 预览备注说明
}

// 数字艺术内容定制订单
export interface DigitalArtOrder extends BaseOrder {
  orderType: 'digital_art'
  artDirection: ArtDirection
  customDirection?: string
  description: string          // 说明文字
  materials: UploadedFile[]    // 相关材料
  previewFiles?: UploadedFile[] // 预览文件
  previewNote?: string         // 预览备注说明
}

// 订单联合类型
export type Order = VideoPurchaseOrder | AI3DCustomOrder | DigitalArtOrder

// ============ 旧的任务类型（保留用于兼容） ============
// 任务状态类型
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'rejected'

// 设计形状类型
export type DesignShape = 'circle' | 'square' | 'rectangle' | 'triangle' | 'custom'

// 设计大小类型（支持预设或自定义尺寸字符串，格式如 "1024*768" 或 "custom:800*600"）
export type DesignSize = '1024*768' | '800*600' | '640*680' | '1920*1080' | 'custom'

// 任务接口（已废弃，保留用于过渡）
export interface Task {
  id: string
  title: string
  description: string
  images?: string[]
  status: TaskStatus
  userId: string
  userName?: string
  // 设计相关字段
  designShape?: DesignShape
  customShapeText?: string  // 自定义形状的文字描述
  designSize?: DesignSize | string  // 设计大小，支持预设或自定义尺寸（如 "custom:800*600"）
  customWidth?: number  // 自定义尺寸的宽度
  customHeight?: number  // 自定义尺寸的高度
  is3D?: boolean
  isCurved?: boolean
  createdAt: string
  updatedAt: string
}

// 登录请求接口
export interface LoginRequest {
  phone: string
  password?: string
  sms_code?: string      // 短信验证码登录
  role: UserRole
  captcha?: string
}

// 注册请求接口
export interface RegisterRequest {
  phone: string
  sms_code: string
  username: string
  email: string
  password: string
  role: UserRole
}

// 登录响应接口
export interface LoginResponse {
  token: string
  user: User
}

// 消息通知接口
export interface Notification {
  id: string
  userId: string
  orderId?: string
  type: NotificationType
  title: string
  content: string
  isRead: boolean
  createdAt: string
  readAt?: string
}

// 消息列表响应接口
export interface NotificationList {
  items: Notification[]
  total: number
  unreadCount: number
}

// API响应接口
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

