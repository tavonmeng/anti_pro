import { beforeEach, describe, expect, it, vi } from 'vitest'
import { buildWebsiteVisitPayload, trackWebsiteVisit } from '../analytics'

describe('website analytics tracking', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('builds a minimal payload without query strings', () => {
    const payload = buildWebsiteVisitPayload({
      pathname: '/cases',
      search: '?invite=secret&utm_source=test',
      href: 'https://uniquevisionx.com/cases?invite=secret',
    } as Location)

    expect(payload).toEqual({
      path: '/cases',
      referrer: '',
    })
  })

  it('uses sendBeacon when available', () => {
    const sendBeacon = vi.fn(() => true)
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}'))
    Object.defineProperty(globalThis.navigator, 'sendBeacon', {
      value: sendBeacon,
      configurable: true,
    })

    trackWebsiteVisit({
      location: { pathname: '/', search: '', href: 'https://uniquevisionx.com/' } as Location,
      documentReferrer: 'https://example.com/link',
    })

    expect(sendBeacon).toHaveBeenCalledOnce()
    expect(sendBeacon).toHaveBeenCalledWith(
      '/api/website-analytics/visit',
      expect.any(Blob),
    )
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('falls back to keepalive fetch when sendBeacon is unavailable', () => {
    Object.defineProperty(globalThis.navigator, 'sendBeacon', {
      value: undefined,
      configurable: true,
    })
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}'))

    trackWebsiteVisit({
      location: { pathname: '/intro', search: '', href: 'https://uniquevisionx.com/intro' } as Location,
      documentReferrer: '',
    })

    expect(fetchSpy).toHaveBeenCalledWith('/api/website-analytics/visit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: '/intro', referrer: '' }),
      keepalive: true,
    })
  })
})
