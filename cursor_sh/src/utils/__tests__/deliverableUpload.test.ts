import { describe, expect, it } from 'vitest'
import {
  DELIVERABLE_ACCEPT,
  DELIVERABLE_MAX_FILE_SIZE,
  isDeliverableFileSizeAllowed,
} from '../deliverableUpload'

describe('creator deliverable upload rules', () => {
  it('allows a file up to exactly 200MB and rejects anything larger', () => {
    expect(DELIVERABLE_MAX_FILE_SIZE).toBe(200 * 1024 * 1024)
    expect(isDeliverableFileSizeAllowed(DELIVERABLE_MAX_FILE_SIZE)).toBe(true)
    expect(isDeliverableFileSizeAllowed(DELIVERABLE_MAX_FILE_SIZE + 1)).toBe(false)
  })

  it('accepts representative image, video, document, design, 3D and archive formats', () => {
    for (const extension of ['.png', '.mp4', '.pdf', '.psd', '.fbx', '.zip']) {
      expect(DELIVERABLE_ACCEPT.split(',')).toContain(extension)
    }
  })
})
