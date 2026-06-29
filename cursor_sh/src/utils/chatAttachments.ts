export type ChatAttachmentLike = {
  name?: string
  url?: string
  type?: string
  isImage?: boolean
  is_image?: boolean
  objectKey?: string
  object_key?: string
  size?: number
}

export type AiAttachmentPayload = {
  name: string
  url: string
  type: string
  is_image: boolean
  object_key: string
  size: number
}

export const toAiAttachmentPayload = (files: ChatAttachmentLike[] = []): AiAttachmentPayload[] => {
  return files
    .filter(file => Boolean(file?.url))
    .map(file => ({
      name: file.name || '',
      url: file.url || '',
      type: file.type || '',
      is_image: Boolean(file.isImage ?? file.is_image),
      object_key: file.objectKey || file.object_key || '',
      size: Number(file.size || 0),
    }))
}
