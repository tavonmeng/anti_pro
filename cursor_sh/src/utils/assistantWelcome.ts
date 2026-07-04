export type AssistantWelcomeMode = 'brand' | 'media' | string

export type AssistantWelcomeCopy = {
  title: string
  description: string
}

export type WelcomeQuickStart = {
  kind: 'create' | 'evaluate' | 'image' | 'order'
  label: string
  prompt: string
}

export const getAssistantWelcomeCopy = (mode: AssistantWelcomeMode): AssistantWelcomeCopy => {
  const audiencePhrase = mode === 'media'
    ? '屏幕、创意、制作和上刊'
    : '品牌目标、创意、制作和投放'
  const expertisePhrase = mode === 'media'
    ? '我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，已为众多媒体方客户提供过高品质的裸眼3D视觉内容解决方案。'
    : '我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，已为众多一线品牌提供过高品质的视觉内容解决方案。'

  return {
    title: '您好，我是 Unique Vision AI 的创意提案总监。',
    description: `${expertisePhrase}您可以先从一句话、一个点位、一张参考图，或一个还没完全成形的创意开始。我会边聊边帮您判断方向，逐步补齐${audiencePhrase}信息，再整理成可执行 Brief。`,
  }
}

export const welcomeQuickStarts: WelcomeQuickStart[] = [
  {
    kind: 'create',
    label: '我想做一个3D视频',
    prompt: '我想做一个3D视频，先从需求开始帮我梳理。',
  },
  {
    kind: 'evaluate',
    label: '帮我评估一个创意',
    prompt: '我有一个创意方向，想让你帮我评估一下可行性和优化空间。',
  },
  {
    kind: 'image',
    label: '基于图片给点方向',
    prompt: '我想基于上传的图片做一些创意延展，请先告诉我可以从哪些方向展开。',
  },
  {
    kind: 'order',
    label: '查看我的订单进展',
    prompt: '帮我查看一下我的订单进展。',
  },
]
