import { describe, expect, it } from 'vitest'
import { prepareAssistantTypewriterTarget } from '../messageTypewriter'

describe('prepareAssistantTypewriterTarget', () => {
  it('reuses an existing assistant thinking message for typewriter output', () => {
    const messages = [
      {
        client_message_id: 'assistant-creative-1',
        role: 'assistant',
        content: '正在进入创意方向构思，这一步会比普通问答更久一些',
        timestamp: '23:42',
        isThinkingStatus: true,
      },
    ]

    const targetIndex = prepareAssistantTypewriterTarget(messages, {
      clientMessageId: 'assistant-creative-1',
      createMessageId: () => 'assistant-new',
      now: () => '23:43',
    })

    expect(targetIndex).toBe(0)
    expect(messages).toHaveLength(1)
    expect(messages[0]).toMatchObject({
      client_message_id: 'assistant-creative-1',
      role: 'assistant',
      content: '',
      timestamp: '23:42',
      isThinkingStatus: false,
    })
  })

  it('creates a new assistant message when no reusable target exists', () => {
    const messages: any[] = []

    const targetIndex = prepareAssistantTypewriterTarget(messages, {
      createMessageId: () => 'assistant-new',
      now: () => '23:43',
    })

    expect(targetIndex).toBe(0)
    expect(messages).toEqual([
      {
        client_message_id: 'assistant-new',
        role: 'assistant',
        content: '',
        timestamp: '23:43',
      },
    ])
  })
})
