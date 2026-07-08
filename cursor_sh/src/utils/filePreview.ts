export type PreviewableFile = Record<string, any> | null | undefined
export type FilePreviewKind = 'image' | 'video' | 'pdf' | 'other'

export const getPreviewFileUrl = (file: PreviewableFile): string =>
  file?.url || file?.previewUrl || file?.file_url || file?.fileUrl || file?.href || ''

export const getPreviewFileName = (file: PreviewableFile, fallback = '文件'): string => {
  const name = file?.name || file?.filename || file?.fileName || file?.originalName || file?.original_filename || ''
  if (name) return name

  const urlName = String(getPreviewFileUrl(file)).split('/').pop()?.split('?')[0] || ''
  return urlName ? decodeURIComponent(urlName) : fallback
}

export const getFilePreviewKind = (file: PreviewableFile): FilePreviewKind => {
  const mime = String(
    file?.mime_type || file?.mimeType || file?.content_type || file?.type || '',
  ).toLowerCase()

  if (mime.startsWith('image/')) return 'image'
  if (mime.startsWith('video/')) return 'video'
  if (mime === 'application/pdf' || mime === 'application/x-pdf') return 'pdf'

  const raw = `${getPreviewFileName(file, '')} ${String(getPreviewFileUrl(file)).split('?')[0]}`
  const match = raw.toLowerCase().match(/\.([a-z0-9]+)(?:\s|$)/)
  const ext = match?.[1] || ''

  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'avif'].includes(ext)) return 'image'
  if (['mp4', 'webm', 'ogg', 'mov', 'm4v'].includes(ext)) return 'video'
  if (ext === 'pdf') return 'pdf'
  return 'other'
}

export const isInlinePreviewableFile = (file: PreviewableFile): boolean =>
  getFilePreviewKind(file) !== 'other'

export const getFileOpenActionText = (file: PreviewableFile): '预览' | '下载' =>
  isInlinePreviewableFile(file) ? '预览' : '下载'

export const getPreviewSignUrlParams = (file: PreviewableFile): Record<string, string> => {
  if (getFilePreviewKind(file) !== 'pdf') return {}

  return {
    disposition: 'inline',
    content_type: 'application/pdf',
    filename: getPreviewFileName(file, 'preview.pdf'),
  }
}
