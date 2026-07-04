const quotedBoldPairs: Record<string, string> = {
  '“': '”',
  '「': '」',
  '『': '』',
  '《': '》',
}

export const normalizeAssistantMarkdown = (text: string) => {
  if (!text) return ''

  return text.replace(
    /\*\*([“「『《])([^*\n]+?)([”」』》])\*\*/g,
    (match, openQuote: string, content: string, closeQuote: string) => {
      if (quotedBoldPairs[openQuote] !== closeQuote) return match
      return `${openQuote}**${content}**${closeQuote}`
    },
  )
}
