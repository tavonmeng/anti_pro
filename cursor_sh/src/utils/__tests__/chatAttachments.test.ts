import { describe, expect, it } from 'vitest'
import { toAiAttachmentPayload } from '../chatAttachments'

describe('toAiAttachmentPayload', () => {
  it('keeps image attachment metadata needed by backend vision understanding', () => {
    const payload = toAiAttachmentPayload([
      {
        id: 'file-1',
        name: 'scene.png',
        url: '/uploads/site_photos/user-test/scene.png',
        isImage: true,
        size: 128,
        type: 'image/png',
        uploadTime: '2026-06-28T12:00:00Z',
        objectKey: 'site_photos/user-test/scene.png',
        previewFailed: false,
      },
    ])

    expect(payload).toEqual([
      {
        name: 'scene.png',
        url: '/uploads/site_photos/user-test/scene.png',
        type: 'image/png',
        is_image: true,
        object_key: 'site_photos/user-test/scene.png',
        size: 128,
      },
    ])
  })

  it('drops attachments without a usable url', () => {
    expect(
      toAiAttachmentPayload([
        {
          name: 'broken.png',
          url: '',
          isImage: true,
          size: 0,
          type: 'image/png',
          uploadTime: '2026-06-28T12:00:00Z',
        },
      ]),
    ).toEqual([])
  })
})
