import { describe, expect, it } from 'vitest'
import {
  buildVideoPurchaseQuery,
  buildVideoPurchaseRoute,
  getVideoLibraryItemById,
  videoLibraryItems,
} from '../videoMarketplace'

describe('video marketplace data', () => {
  it('provides reusable media and price metadata for library detail pages', () => {
    const item = getVideoLibraryItemById('1')

    expect(item?.title).toBe('赛博朋克深空穿越')
    expect(item?.media.type).toBe('image')
    expect(item?.media.url).toBe('/video-library-images/1.png')
    expect(item?.price.label).toBe('成片适配起步价')
    expect(item?.price.display).toBe('¥ 8,800起')
    expect(videoLibraryItems.every(entry => entry.price.display)).toBe(true)
  })

  it('builds purchase query from the selected library item', () => {
    const item = getVideoLibraryItemById('2')!

    expect(buildVideoPurchaseQuery(item)).toEqual({
      selected_id: '2',
      title: '未来机甲异星破阵',
      price: '¥ 8,800起',
      media_type: 'image',
      media_url: '/video-library-images/2.jpg',
    })
  })

  it('routes selected cards directly to the purchase adaptation form', () => {
    const item = getVideoLibraryItemById('3')!

    expect(buildVideoPurchaseRoute(item)).toEqual({
      path: '/user/create-order/video_purchase',
      query: buildVideoPurchaseQuery(item),
    })
  })
})
