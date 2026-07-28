import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import BriefProgressPanel from '../BriefProgressPanel.vue'

const agentState = {
  brief_state: {
    fields: {
      project_name: { value: '城市春日计划', confidence: 'high' },
      theme_concept: { value: '', confidence: 'unknown' },
      city_location: { value: '', confidence: 'unknown' },
    },
    readiness: {
      level: 'insufficient',
      missing_for_formal: ['theme_concept', 'city_location'],
    },
  },
}

describe('BriefProgressPanel', () => {
  it('renders a compact progress disclosure and reveals the collected brief details', async () => {
    const wrapper = mount(BriefProgressPanel, {
      props: { agentState },
      global: {
        stubs: {
          ElIcon: { template: '<i><slot /></i>' },
        },
      },
    })

    expect(wrapper.text()).toContain('Brief进度')
    expect(wrapper.text()).toContain('33%')
    expect(wrapper.find('.brief-progress-details').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('城市春日计划')
    expect(wrapper.get('.brief-progress-arrow').classes()).not.toContain('is-expanded')

    await wrapper.get('.brief-progress-toggle').trigger('click')

    expect(wrapper.text()).toContain('城市春日计划')
    expect(wrapper.text()).toContain('接下来继续补充')
    expect(wrapper.get('.brief-progress-toggle').attributes('aria-expanded')).toBe('true')
    expect(wrapper.get('.brief-progress-arrow').classes()).toContain('is-expanded')

    await wrapper.get('.brief-progress-toggle').trigger('click')

    expect(wrapper.get('.brief-progress-toggle').attributes('aria-expanded')).toBe('false')
    expect(wrapper.get('.brief-progress-arrow').classes()).not.toContain('is-expanded')
  })
})
