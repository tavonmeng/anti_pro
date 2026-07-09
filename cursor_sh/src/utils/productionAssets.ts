import {
  getFilePreviewKind,
  getPreviewFileName,
  getPreviewFileSignKey,
  getPreviewFileUrl,
} from './filePreview'

export type ProductionAssetKind = 'image' | 'video' | 'pdf' | 'document' | 'archive' | 'other'

export interface ProductionAsset {
  id?: string
  name?: string
  filename?: string
  label?: string
  source?: string
  kind?: ProductionAssetKind
  url?: string
  file_url?: string
  fileUrl?: string
  object_key?: string
  mime_type?: string
  type?: string
  [key: string]: any
}

export interface ProductionAssetGroup {
  label: string
  assets: ProductionAsset[]
}

export function groupProductionAssets(assets?: ProductionAsset[] | null): ProductionAssetGroup[] {
  const groups: ProductionAssetGroup[] = []
  const byLabel = new Map<string, ProductionAsset[]>()

  for (const asset of assets || []) {
    const label = asset.label || '制作素材'
    if (!byLabel.has(label)) {
      byLabel.set(label, [])
      groups.push({ label, assets: byLabel.get(label)! })
    }
    byLabel.get(label)!.push(asset)
  }

  return groups
}

export function assetKindLabel(kind?: ProductionAssetKind | string): string {
  const labels: Record<string, string> = {
    image: '图片',
    video: '视频',
    pdf: 'PDF',
    document: '文档',
    archive: '压缩包',
    other: '文件',
  }
  return labels[kind || 'other'] || '文件'
}

const documentExtensions = new Set([
  'doc', 'docx', 'ppt', 'pptx', 'key', 'xls', 'xlsx', 'txt', 'csv',
])

const archiveExtensions = new Set(['zip', 'rar', '7z'])

const extensionFromAsset = (asset: ProductionAsset): string => {
  const raw = [
    getPreviewFileName(asset, ''),
    getPreviewFileUrl(asset),
    getPreviewFileSignKey(asset),
  ].join(' ')
  const match = raw.toLowerCase().match(/\.([a-z0-9]+)(?:[?#\s]|$)/)
  return match?.[1] || ''
}

export function productionAssetKind(asset: ProductionAsset): ProductionAssetKind {
  if (asset.kind) return asset.kind

  const previewKind = getFilePreviewKind(asset)
  if (previewKind !== 'other') return previewKind

  const ext = extensionFromAsset(asset)
  if (documentExtensions.has(ext)) return 'document'
  if (archiveExtensions.has(ext)) return 'archive'
  return 'other'
}

export function productionAssetActionText(asset: ProductionAsset): '预览' | '打开' {
  return ['image', 'video', 'pdf'].includes(productionAssetKind(asset)) ? '预览' : '打开'
}

export function productionAssetPreviewTarget(asset: ProductionAsset): 'dialog' | 'new-tab' {
  return ['image', 'video', 'pdf'].includes(productionAssetKind(asset)) ? 'dialog' : 'new-tab'
}
