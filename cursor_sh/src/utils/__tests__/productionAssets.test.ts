import { describe, expect, it } from 'vitest'
import {
  assetKindLabel,
  groupProductionAssets,
  productionAssetActionText,
  productionAssetKind,
  productionAssetPreviewTarget,
} from '../productionAssets'

describe('productionAssets utilities', () => {
  it('groups assets by their display label', () => {
    const groups = groupProductionAssets([
      { id: 'a1', name: '现场.jpg', label: '现场/参考文件', kind: 'image' },
      { id: 'a2', name: '说明.pdf', label: '现场/参考文件', kind: 'pdf' },
      { id: 'a3', name: '方案.pptx', label: 'AI设计方案附件', kind: 'document' },
    ])

    expect(groups).toEqual([
      {
        label: '现场/参考文件',
        assets: [
          { id: 'a1', name: '现场.jpg', label: '现场/参考文件', kind: 'image' },
          { id: 'a2', name: '说明.pdf', label: '现场/参考文件', kind: 'pdf' },
        ],
      },
      {
        label: 'AI设计方案附件',
        assets: [
          { id: 'a3', name: '方案.pptx', label: 'AI设计方案附件', kind: 'document' },
        ],
      },
    ])
  })

  it('returns reader-facing labels for asset kinds', () => {
    expect(assetKindLabel('image')).toBe('图片')
    expect(assetKindLabel('pdf')).toBe('PDF')
    expect(assetKindLabel('archive')).toBe('压缩包')
  })

  it('uses preview copy for image video and pdf assets', () => {
    expect(productionAssetActionText({ kind: 'image' })).toBe('预览')
    expect(productionAssetActionText({ kind: 'video' })).toBe('预览')
    expect(productionAssetActionText({ kind: 'pdf' })).toBe('预览')
    expect(productionAssetActionText({ kind: 'document' })).toBe('打开')
  })

  it('keeps previewable demand assets inside the authenticated preview dialog', () => {
    expect(productionAssetPreviewTarget({ kind: 'image' })).toBe('dialog')
    expect(productionAssetPreviewTarget({ kind: 'video' })).toBe('dialog')
    expect(productionAssetPreviewTarget({ kind: 'pdf' })).toBe('dialog')
    expect(productionAssetPreviewTarget({ kind: 'document' })).toBe('new-tab')
  })

  it('infers preview behavior for untyped uploaded attachments', () => {
    const sitePhoto = { filename: '现场实拍.jpg', url: '/uploads/site_photos/u1/photo.jpg' }
    const aiPdf = { filename: 'AI方案.pdf', object_key: 'design-plans/order-1/AI方案.pdf' }
    const aiDoc = { filename: '需求说明.docx', url: '/uploads/site_photos/u1/需求说明.docx' }
    const archive = { filename: '参考素材.zip', url: '/uploads/site_photos/u1/参考素材.zip' }

    expect(productionAssetKind(sitePhoto)).toBe('image')
    expect(productionAssetKind(aiPdf)).toBe('pdf')
    expect(productionAssetKind(aiDoc)).toBe('document')
    expect(productionAssetKind(archive)).toBe('archive')
    expect(productionAssetActionText(aiPdf)).toBe('预览')
    expect(productionAssetPreviewTarget(aiPdf)).toBe('dialog')
    expect(productionAssetPreviewTarget(aiDoc)).toBe('new-tab')
  })
})
