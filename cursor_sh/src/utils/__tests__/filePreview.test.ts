import { describe, expect, it } from 'vitest'
import {
  getFilePreviewOpenTarget,
  getFileOpenActionText,
  getFilePreviewKind,
  getPreviewFileSignKey,
  getPreviewSignUrlParams,
  isInlinePreviewableFile,
} from '../filePreview'

describe('filePreview helpers', () => {
  it('treats uploaded PDFs as inline-previewable files', () => {
    const file = {
      name: '需求确认.pdf',
      type: 'application/pdf',
      url: '/uploads/deliverables/user-1/%E9%9C%80%E6%B1%82%E7%A1%AE%E8%AE%A4.pdf?Expires=3600',
    }

    expect(getFilePreviewKind(file)).toBe('pdf')
    expect(isInlinePreviewableFile(file)).toBe(true)
    expect(getFileOpenActionText(file)).toBe('预览')
  })

  it('keeps unsupported office documents as download-only', () => {
    const file = {
      name: '项目说明.docx',
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      file_url: '/uploads/deliverables/user-1/project.docx',
    }

    expect(getFilePreviewKind(file)).toBe('other')
    expect(isInlinePreviewableFile(file)).toBe(false)
    expect(getFileOpenActionText(file)).toBe('下载')
  })

  it('requests inline OSS headers for PDF preview URLs', () => {
    const file = {
      name: '需求确认.pdf',
      type: 'application/pdf',
      object_key: 'deliverables/user-1/demo.pdf',
    }

    expect(getPreviewSignUrlParams(file)).toEqual({
      disposition: 'inline',
      filename: '需求确认.pdf',
    })
  })

  it('detects legacy PDFs from object keys even when metadata is incomplete', () => {
    const file = {
      name: '需求确认',
      object_key: 'deliverables/user-1/demo.pdf',
    }

    expect(getFilePreviewKind(file)).toBe('pdf')
    expect(getPreviewSignUrlParams(file)).toEqual({
      disposition: 'inline',
      filename: '需求确认',
    })
  })

  it('opens PDFs in a browser tab instead of the embedded preview dialog', () => {
    expect(getFilePreviewOpenTarget({ name: '需求确认.pdf', type: 'application/pdf' })).toBe('new-tab')
    expect(getFilePreviewOpenTarget({ name: '现场图.png', type: 'image/png' })).toBe('dialog')
    expect(getFilePreviewOpenTarget({ name: '演示视频.mp4', type: 'video/mp4' })).toBe('dialog')
    expect(getFilePreviewOpenTarget({ name: '项目说明.docx' })).toBe('new-tab')
  })

  it('uses existing URLs as sign-url keys for legacy uploaded files', () => {
    const ossUrl = 'https://anti-pro-prod-assets.oss-cn-beijing.aliyuncs.com/deliverables/user-1/demo.pdf?Expires=3600'

    expect(getPreviewFileSignKey({ object_key: 'deliverables/user-1/current.pdf', url: ossUrl })).toBe(
      'deliverables/user-1/current.pdf',
    )
    expect(getPreviewFileSignKey({ url: ossUrl })).toBe(ossUrl)
  })
})
