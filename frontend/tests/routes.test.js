import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory } from 'vue-router'

const server = await createServer({ server: { middlewareMode: true } })
after(() => server.close())

const { createDateRouter } = await server.ssrLoadModule('/src/router.js')
const { default: App } = await server.ssrLoadModule('/src/App.vue')

async function render(path) {
  const router = createDateRouter(createMemoryHistory())
  const app = createSSRApp(App).use(router)
  await router.push(path)
  await router.isReady()
  return renderToString(app)
}

test('home displays the local current date', async () => {
  const today = new Date()
  const expected = [today.getFullYear(), today.getMonth() + 1, today.getDate()]
    .map((part, index) => String(part).padStart(index === 0 ? 4 : 2, '0')).join('/')
  assert.ok((await render('/')).includes(`>${expected}</time>`))
})

test('date route displays the requested date', async () => {
  assert.ok((await render('/2026/10/10')).includes('datetime="2026-10-10">2026/10/10</time>'))
})

test('date validation handles leap years and invalid days', async () => {
  assert.ok((await render('/2024/02/29')).includes('>2024/02/29</time>'))
  for (const path of ['/2026/02/29', '/2026/02/30', '/2026/13/01', '/0000/01/01']) {
    assert.ok((await render(path)).includes('日期无效'), path)
  }
})

test('unknown paths show an invalid date message', async () => {
  assert.ok((await render('/unknown')).includes('日期无效'))
})
