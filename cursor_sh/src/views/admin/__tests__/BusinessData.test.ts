import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ElMessage } from 'element-plus'
import { businessDataApi } from '@/utils/api'
import BusinessData from '../BusinessData.vue'

vi.mock('@/utils/api', () => ({
  businessDataApi: { getWebsiteVisits: vi.fn(), resolveUnresolvedVisitGeos: vi.fn() },
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), info: vi.fn(), error: vi.fn() },
}))

const mountDashboard = () => mount(BusinessData, {
  global: {
    directives: { loading: () => {} },
    stubs: {
      ElSelect: {
        props: ['modelValue', 'disabled'],
        emits: ['update:modelValue', 'change'],
        template: '<select :value="modelValue" :disabled="disabled" @change="$emit(\'update:modelValue\', Number($event.target.value)); $emit(\'change\')"><slot /></select>',
      },
      ElOption: { props: ['label', 'value'], template: '<option :value="value">{{ label }}</option>' },
      ElButton: { props: ['disabled', 'loading'], template: '<button :disabled="disabled || loading"><slot /></button>' },
      ElCard: { template: '<section><slot name="header" /><slot /></section>' },
      ElTable: true,
      ElTableColumn: true,
      ElTag: true,
    },
  },
})

describe('BusinessData historical IP resolution', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(businessDataApi.getWebsiteVisits).mockResolvedValue({
      totals: { today_pv: 0, today_uv: 0, yesterday_pv: 0, yesterday_uv: 0, range_pv: 0, range_uv: 0, days: 7 },
      daily: [], paths: [], recent_events: [],
    })
    vi.mocked(businessDataApi.resolveUnresolvedVisitGeos).mockResolvedValue({
      candidate_unique_ips: 250, processed_unique_ips: 200, cache_hits: 0, resolved: 200,
      unavailable: 0, failed: 0, updated_events: 200, evicted_cache_entries: 0,
    })
  })

  it('resolves the selected historical range and tells the admin when another batch remains', async () => {
    const wrapper = mountDashboard()
    await flushPromises()
    await wrapper.get('select').setValue('30')
    await flushPromises()
    const resolveButton = wrapper.findAll('button').find(button => button.text().includes('解析最近'))!
    expect(resolveButton.text()).toBe('解析最近 30 天未识别地域')
    await resolveButton.trigger('click')
    await flushPromises()
    expect(businessDataApi.resolveUnresolvedVisitGeos).toHaveBeenCalledTimes(1)
    expect(businessDataApi.resolveUnresolvedVisitGeos).toHaveBeenCalledWith(30)
    expect(businessDataApi.getWebsiteVisits).toHaveBeenLastCalledWith(30)
    expect(ElMessage.info).toHaveBeenCalledWith('本次还有 50 个 IP 未处理，可再次点击继续解析。')
    wrapper.unmount()
  })
})
