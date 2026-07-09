export interface WebsiteVisitPayload {
  path: string
  referrer: string
}

interface TrackWebsiteVisitOptions {
  location?: Location
  documentReferrer?: string
}

const TRACKING_ENDPOINT = '/api/website-analytics/visit'

export const buildWebsiteVisitPayload = (
  locationRef: Location = window.location,
  documentReferrer = ''
): WebsiteVisitPayload => {
  const path = locationRef.pathname || '/'
  return {
    path,
    referrer: documentReferrer || '',
  }
}

export const trackWebsiteVisit = (options: TrackWebsiteVisitOptions = {}) => {
  try {
    const payload = buildWebsiteVisitPayload(
      options.location || window.location,
      options.documentReferrer ?? document.referrer
    )
    const body = JSON.stringify(payload)

    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' })
      if (navigator.sendBeacon(TRACKING_ENDPOINT, blob)) {
        return
      }
    }

    void fetch(TRACKING_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
    }).catch(() => undefined)
  } catch {
    // Website analytics must never affect the public landing page.
  }
}
