export async function requestChatReply(messages, { endpoint, signal } = {}) {
  if (!endpoint) throw new Error('AI 聊天服务尚未配置，请配置 VITE_CHAT_API_URL 后重启或重新构建前端。')

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
    signal,
  })
  if (!response.ok) throw new Error('AI 服务暂时不可用，请稍后重新发送。')

  let data
  try {
    data = await response.json()
  } catch {
    throw new Error('聊天接口返回格式不正确，请检查服务配置。')
  }
  if (typeof data.answer !== 'string' || !data.answer.trim()) {
    throw new Error('AI 暂未返回有效回复，请重新发送。')
  }
  return data.answer.trim()
}
