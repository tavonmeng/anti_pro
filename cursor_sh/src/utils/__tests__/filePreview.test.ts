import { describe, expect, it } from 'vitest'
import {
  getFileOpenActionText,
  getFilePreviewKind,
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
      content_type: 'application/pdf',
      filename: '需求确认.pdf',
    })
  })
})
