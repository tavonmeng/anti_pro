export type AssistantTypewriterMessage = {
  client_message_id?: string
  role?: string
  content?: string
  timestamp?: string
  isThinkingStatus?: boolean
  [key: string]: any
}

type PrepareAssistantTypewriterTargetOptions = {
  clientMessageId?: string
  createMessageId: () => string
  now: () => string
}

export const prepareAssistantTypewriterTarget = (
  messages: AssistantTypewriterMessage[],
  options: PrepareAssistantTypewriterTargetOptions,
) => {
  const existingIndex = options.clientMessageId
    ? messages.findIndex(
        msg => msg.role === 'assistant' && msg.client_message_id === options.clientMessageId,
      )
    : -1

  if (existingIndex >= 0) {
    messages[existingIndex].content = ''
    messages[existingIndex].isThinkingStatus = false
    return existingIndex
  }

  messages.push({
    client_message_id: options.clientMessageId || options.createMessageId(),
    role: 'assistant',
    content: '',
    timestamp: options.now(),
  })
  return messages.length - 1
}
