<script setup>
import { nextTick, onUnmounted, ref, watch } from 'vue'
import { requestChatReply } from '../features/chat.js'

const open = ref(false)
const draft = ref('')
const messages = ref([])
const pending = ref(false)
const error = ref('')
const input = ref(null)
const launcher = ref(null)
const transcript = ref(null)
const suggestions = ['帮我分析酒店价格趋势']
let controller

async function scrollToLatest() {
  await nextTick()
  if (transcript.value) transcript.value.scrollTop = transcript.value.scrollHeight
}

watch(open, async (visible) => {
  await nextTick()
  if (visible) {
    input.value?.focus()
    scrollToLatest()
  } else launcher.value?.focus()
})

async function send(text = draft.value) {
  const content = text.trim()
  if (!content || pending.value) return
  draft.value = ''
  error.value = ''
  messages.value.push({ role: 'user', content })
  pending.value = true
  scrollToLatest()
  controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 60000)
  try {
    const answer = await requestChatReply(messages.value, {
      endpoint: import.meta.env.VITE_CHAT_API_URL,
      signal: controller.signal,
    })
    messages.value.push({ role: 'assistant', content: answer })
  } catch (cause) {
    messages.value.pop()
    draft.value = content
    error.value = cause.name === 'AbortError'
      ? '等待回复超时，请重新发送。'
      : cause instanceof TypeError ? '无法连接 AI 服务，请检查网络或接口配置。' : cause.message
  } finally {
    clearTimeout(timeout)
    pending.value = false
    scrollToLatest()
    await nextTick()
    if (open.value) input.value?.focus()
  }
}

function handleEnter(event) {
  if (event.isComposing || event.keyCode === 229 || event.shiftKey) return
  event.preventDefault()
  send()
}

onUnmounted(() => controller?.abort())
</script>

<template>
  <div class="ai-chat" @keydown.esc.stop.prevent="open = false">
    <section v-show="open" id="ai-chat-panel" class="ai-chat-panel" role="dialog" aria-labelledby="ai-chat-title">
      <header class="ai-chat-header">
        <div class="ai-chat-avatar" aria-hidden="true">AI</div>
        <div class="ai-chat-heading">
          <h2 id="ai-chat-title">AI 酒店助手</h2>
          <p>经营思路，随时聊聊</p>
        </div>
        <button type="button" class="ai-chat-close" aria-label="关闭聊天" @click="open = false">×</button>
      </header>

      <div ref="transcript" class="ai-chat-transcript" role="log" aria-label="聊天记录" aria-live="polite" :aria-busy="pending">
        <div class="ai-chat-welcome">
          <span class="ai-chat-welcome-icon" aria-hidden="true">✦</span>
          <h3>你好，有什么可以帮你？</h3>
          <p>一起聊聊酒店经营、价格策略和营销思路。</p>
          <p class="ai-chat-context-note">当前对话尚未接入页面价格或酒店数据库。</p>
          <div v-if="!messages.length" class="ai-chat-suggestions">
            <button v-for="suggestion in suggestions" :key="suggestion" type="button" :disabled="pending" @click="send(suggestion)">{{ suggestion }} <span aria-hidden="true">↗</span></button>
          </div>
        </div>
        <div v-for="(message, index) in messages" :key="index" class="ai-chat-message" :class="`ai-chat-message--${message.role}`">
          <span class="ai-chat-message-author">{{ message.role === 'user' ? '你' : 'AI 助手' }}</span>
          <p>{{ message.content }}</p>
        </div>
        <p v-if="pending" class="ai-chat-pending" role="status">AI 正在思考<span aria-hidden="true">…</span></p>
      </div>

      <form class="ai-chat-composer" @submit.prevent="send()">
        <p v-if="error" class="ai-chat-error" role="alert">{{ error }}</p>
        <label class="ai-chat-sr-only" for="ai-chat-input">输入你的问题</label>
        <div class="ai-chat-input-row">
          <textarea id="ai-chat-input" ref="input" v-model="draft" rows="2" maxlength="4000" placeholder="输入你的问题…" :disabled="pending" @keydown.enter="handleEnter"></textarea>
          <button type="submit" class="ai-chat-send" :disabled="pending || !draft.trim()" aria-label="发送消息">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m5 12 7-7 7 7M12 5v15" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </button>
        </div>
        <p class="ai-chat-hint">Enter 发送 · Shift + Enter 换行 · AI 建议请核实</p>
      </form>
    </section>

    <button ref="launcher" type="button" class="ai-chat-launcher" :aria-label="open ? '收起 AI 聊天' : '打开 AI 聊天'" :aria-expanded="open" aria-controls="ai-chat-panel" aria-haspopup="dialog" @click="open = !open">
      <svg v-if="!open" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M20 11.5a8 8 0 0 1-8 8H5l-3 3v-11a9 9 0 1 1 18 0Z" stroke-linejoin="round" /><path d="M7 11h.01M11 11h.01M15 11h.01" stroke-width="3" stroke-linecap="round" /></svg>
      <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m6 9 6 6 6-6" stroke-linecap="round" stroke-linejoin="round" /></svg>
      <span v-if="!open">AI 聊天</span>
    </button>
  </div>
</template>

<style scoped>
.ai-chat { position: fixed; right: max(24px, env(safe-area-inset-right)); bottom: calc(24px + env(safe-area-inset-bottom)); z-index: 50; font-size: 14px; text-align: left; }
.ai-chat button, .ai-chat textarea { font: inherit; }
.ai-chat button { cursor: pointer; }
.ai-chat button:disabled { cursor: not-allowed; opacity: .5; }
.ai-chat :focus-visible { outline: 2px solid var(--theme-accent); outline-offset: 3px; }
.ai-chat-launcher { display: flex; align-items: center; gap: 10px; margin-left: auto; min-height: 56px; padding: 0 19px; border: 0; border-radius: 28px; background: var(--theme-accent); color: #fff; font-weight: 600 !important; box-shadow: 0 6px 24px #754b3340; }
.ai-chat-launcher:hover { background: var(--theme-accent-hover); }
.ai-chat-panel { display: flex; flex-direction: column; width: min(390px, calc(100vw - 32px)); height: min(560px, calc(100dvh - 116px - env(safe-area-inset-bottom))); margin-bottom: 14px; overflow: hidden; border: 1px solid var(--theme-border); border-radius: 20px; background: var(--theme-surface); box-shadow: 0 16px 56px #35211433; }
.ai-chat-header { display: flex; align-items: center; gap: 12px; padding: 20px; border-bottom: 1px solid var(--theme-border); }
.ai-chat-avatar { display: grid; place-items: center; width: 40px; height: 40px; flex-shrink: 0; border-radius: 12px; background: var(--theme-soft); color: var(--theme-accent); font-weight: 700; }
.ai-chat-heading { flex: 1; }
.ai-chat-heading h2 { margin: 0; font-size: 16px; }
.ai-chat-heading p { margin: 4px 0 0; color: var(--theme-muted); font-size: 12px; }
.ai-chat-close { width: 32px; height: 32px; border: 0; border-radius: 8px; background: var(--theme-soft); color: var(--theme-muted); font-size: 24px !important; }
.ai-chat-transcript { flex: 1; min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 20px; background: #f6f0e7; }
.ai-chat-welcome { padding: 8px 0 20px; }
.ai-chat-welcome-icon { color: var(--theme-accent); font-size: 30px; }
.ai-chat-welcome h3 { margin: 12px 0 8px; font-size: 18px; }
.ai-chat-welcome p { margin: 0; color: var(--theme-muted); line-height: 1.7; }
.ai-chat-welcome .ai-chat-context-note { margin-top: 8px; font-size: 12px; }
.ai-chat-suggestions { display: grid; gap: 8px; margin-top: 20px; }
.ai-chat-suggestions button { display: flex; justify-content: space-between; gap: 8px; padding: 12px; border: 1px solid var(--theme-border); border-radius: 10px; background: var(--theme-surface); color: var(--theme-muted); text-align: left; }
.ai-chat-suggestions button:hover { border-color: #b99c7f; color: var(--theme-accent); }
.ai-chat-message { max-width: 88%; margin: 14px 0; }
.ai-chat-message--user { margin-left: auto; }
.ai-chat-message-author { display: block; margin-bottom: 6px; color: var(--theme-muted); font-size: 12px; }
.ai-chat-message--user .ai-chat-message-author { text-align: right; }
.ai-chat-message p { margin: 0; padding: 12px 14px; border: 1px solid var(--theme-border); border-radius: 12px; background: var(--theme-surface); white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.75; }
.ai-chat-message--user p { border-color: var(--theme-accent); background: var(--theme-accent); color: #fff; }
.ai-chat-pending { color: var(--theme-muted); font-size: 13px; }
.ai-chat-composer { padding: 14px 16px 12px; border-top: 1px solid var(--theme-border); }
.ai-chat-input-row { display: flex; align-items: flex-end; gap: 8px; padding: 10px; border: 1px solid var(--theme-border); border-radius: 12px; }
.ai-chat-input-row:focus-within { border-color: var(--theme-accent); box-shadow: 0 0 0 2px #e9ddcd; }
.ai-chat textarea { flex: 1; width: 0; min-width: 0; max-height: 120px; resize: vertical; border: 0; background: transparent; color: var(--theme-text); line-height: 1.6; }
.ai-chat textarea:focus-visible { outline: none; }
.ai-chat-send { display: grid; place-items: center; flex-shrink: 0; width: 34px; height: 34px; padding: 0; border: 0; border-radius: 9px; background: var(--theme-accent); color: #fff; }
.ai-chat-hint { margin: 9px 0 0; color: var(--theme-muted); font-size: 11px; text-align: center; }
.ai-chat-error { margin: 0 0 10px; color: #b91c1c; font-size: 12px; line-height: 1.6; }
.ai-chat-sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
@media (max-width: 480px) {
  .ai-chat { right: max(16px, env(safe-area-inset-right)); bottom: calc(16px + env(safe-area-inset-bottom)); }
  .ai-chat textarea { font-size: 16px; }
}
</style>
