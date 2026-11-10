import assert from 'node:assert/strict'
import { test } from 'node:test'
import { requestChatReply } from '../src/features/chat.js'

test('missing endpoint reports configuration without making a request', async (t) => {
  const fetch = t.mock.method(globalThis, 'fetch', () => assert.fail('unexpected request'))
  await assert.rejects(requestChatReply([]), /尚未配置/)
  assert.equal(fetch.mock.callCount(), 0)
})

test('sends conversation history and returns the assistant answer', async (t) => {
  const messages = [{ role: 'user', content: '你好' }, { role: 'assistant', content: '你好！' }, { role: 'user', content: '酒店如何定价？' }]
  const controller = new AbortController()
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/chat')
    assert.equal(options.method, 'POST')
    assert.deepEqual(JSON.parse(options.body), { messages })
    assert.equal(options.signal, controller.signal)
    return new Response(JSON.stringify({ answer: '  先了解需求和成本。  ' }))
  })
  assert.equal(await requestChatReply(messages, { endpoint: '/api/chat', signal: controller.signal }), '先了解需求和成本。')
})

test('reports service errors, HTML fallbacks, and empty replies', async (t) => {
  for (const [response, expected] of [
    [new Response('', { status: 503 }), /暂时不可用/],
    [new Response('<html>SPA fallback</html>'), /返回格式不正确/],
    [new Response(JSON.stringify({ answer: ' ' })), /有效回复/],
  ]) {
    t.mock.method(globalThis, 'fetch', async () => response)
    await assert.rejects(requestChatReply([], { endpoint: '/api/chat' }), expected)
    t.mock.restoreAll()
  }
})
