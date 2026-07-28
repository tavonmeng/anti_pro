import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentInteractionComposer from '../AgentInteractionComposer.vue'

const interaction = (type: 'single_choice' | 'multiple_choice' = 'single_choice', count = 3) => ({
  type,
  question_id: `question-${type}-${count}`,
  placeholder: '输入其他视觉偏好',
  options: Array.from({ length: count }, (_, index) => ({
    id: `option-${index + 1}`,
    label: `选项 ${index + 1}`,
    value: `value-${index + 1}`,
  })),
  allow_other: true,
})

const mountComposer = (value: any = interaction()) => mount(AgentInteractionComposer, {
  props: { interaction: value },
  global: {
    stubs: {
      ElIcon: { template: '<i><slot /></i>' },
      ElDatePicker: {
        props: ['modelValue'],
        emits: ['update:modelValue'],
        template: '<input class="date-picker-test" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
      },
    },
  },
})

describe('AgentInteractionComposer', () => {
  it('uses the full answer card and submits a single selection only after confirmation', async () => {
    const wrapper = mountComposer()

    expect(wrapper.find('.agent-interaction-header').exists()).toBe(false)

    await wrapper.get('button.agent-interaction-option').trigger('click')
    expect(wrapper.emitted('submit')).toBeUndefined()

    await wrapper.get('button.agent-interaction-submit').trigger('click')
    expect(wrapper.emitted('submit')?.[0]).toEqual(['选项 1'])
  })

  it('supports a free-form answer and skip exit inside the card', async () => {
    const wrapper = mountComposer()

    await wrapper.get('button.is-other').trigger('click')
    expect(wrapper.find('.agent-interaction-custom').exists()).toBe(true)
    await wrapper.get('textarea.agent-interaction-custom-input').setValue('人物与产品并重')
    await wrapper.get('button.agent-interaction-submit').trigger('click')
    expect(wrapper.emitted('submit')?.[0]).toEqual(['人物与产品并重'])

    await wrapper.get('button.agent-interaction-skip').trigger('click')
    expect(wrapper.emitted('skip')).toHaveLength(1)
  })

  it('holds multiple selections until continue and filters long option lists', async () => {
    const wrapper = mountComposer(interaction('multiple_choice', 10))

    expect(wrapper.find('.agent-interaction-header').exists()).toBe(false)
    expect(wrapper.find('input[type="search"]').exists()).toBe(true)
    await wrapper.get('input[type="search"]').setValue('选项 10')
    expect(wrapper.findAll('button.agent-interaction-option')).toHaveLength(2)

    await wrapper.get('button.agent-interaction-option').trigger('click')
    await wrapper.get('input[type="search"]').setValue('选项 1')
    await wrapper.get('button.agent-interaction-option').trigger('click')
    expect(wrapper.emitted('submit')).toBeUndefined()

    await wrapper.get('button.agent-interaction-submit').trigger('click')
    expect(wrapper.emitted('submit')?.[0]).toEqual(['选项 10、选项 1'])
  })

  it('renders a date picker and submits the same localized date shown to the user', async () => {
    const wrapper = mountComposer({
      type: 'date',
      question_id: 'online-date',
      placeholder: '选择上刊日期',
    })

    expect(wrapper.find('.agent-interaction-date').exists()).toBe(true)
    expect(wrapper.get('button.agent-interaction-date-uncertain').text()).toBe('不确定')
    await wrapper.get('.date-picker-test').setValue('2026-08-09')
    await wrapper.get('button.agent-interaction-submit').trigger('click')

    expect(wrapper.emitted('submit')?.[0]).toEqual(['2026年8月9日'])
  })

  it('allows an uncertain date and submits exactly the visible option label', async () => {
    const wrapper = mountComposer({
      type: 'date',
      question_id: 'online-date-uncertain',
      placeholder: '选择上刊日期',
    })

    await wrapper.get('.date-picker-test').setValue('2026-08-09')
    await wrapper.get('button.agent-interaction-date-uncertain').trigger('click')

    expect((wrapper.get('.date-picker-test').element as HTMLInputElement).value).toBe('')
    expect(wrapper.get('button.agent-interaction-date-uncertain').classes()).toContain('is-selected')

    await wrapper.get('button.agent-interaction-submit').trigger('click')
    expect(wrapper.emitted('submit')).toEqual([['不确定']])
  })

  it('switches from uncertain back to a concrete date when the user picks one', async () => {
    const wrapper = mountComposer({
      type: 'date',
      question_id: 'online-date-switch',
      placeholder: '选择上刊日期',
    })

    await wrapper.get('button.agent-interaction-date-uncertain').trigger('click')
    await wrapper.get('.date-picker-test').setValue('2026-08-10')

    expect(wrapper.get('button.agent-interaction-date-uncertain').classes()).not.toContain('is-selected')
    await wrapper.get('button.agent-interaction-submit').trigger('click')
    expect(wrapper.emitted('submit')).toEqual([['2026年8月10日']])
  })
})
