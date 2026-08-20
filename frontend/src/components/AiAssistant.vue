<template>
  <div class="ai-assistant">
    <transition name="el-zoom-in-bottom">
      <div v-if="open" class="chat-panel">
        <div class="chat-header">
          <span>🤖 AI 助手</span>
          <el-button link @click="open = false"><el-icon><Close /></el-icon></el-button>
        </div>
        <div class="chat-body" ref="bodyRef">
          <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
            <div class="bubble">{{ m.content }}</div>
          </div>
          <div v-if="loading" class="msg assistant"><div class="bubble typing">正在思考…</div></div>
        </div>
        <div class="chat-input">
          <el-input v-model="input" placeholder="问我政策 / 数据…" @keyup.enter="send" />
          <el-button type="primary" :disabled="loading" @click="send">发送</el-button>
        </div>
      </div>
    </transition>
    <div class="fab" @click="open = !open">🤖</div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const open = ref(false)
const input = ref('')
const loading = ref(false)
const bodyRef = ref()
const messages = ref([
  { role: 'assistant', content: '你好，我是平台 AI 助手。可以问我高龄补贴政策、申领流程、资格认证，或平台实时数据（如"雁塔区有多少老人"）。' }
])

async function send() {
  const q = input.value.trim()
  if (!q || loading.value) return
  messages.value.push({ role: 'user', content: q })
  input.value = ''
  loading.value = true
  messages.value.push({ role: 'assistant', content: '' })
  const idx = messages.value.length - 1
  await nextTick(); scrollToBottom()
  try {
    const token = localStorage.getItem('token')
    const resp = await fetch('/api/ai/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-User-Id': token },
      body: JSON.stringify({ messages: messages.value.slice(0, idx) })
    })
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop()
      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data:')) continue
        try {
          const obj = JSON.parse(line.slice(5).trim())
          if (obj.content) {
            messages.value[idx].content += obj.content
            scrollToBottom()
          }
        } catch (e) { /* 忽略不完整分块 */ }
      }
    }
  } catch (e) {
    messages.value[idx].content = '抱歉，AI 服务暂时不可用，请稍后再试。'
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
}
</script>

<style scoped>
.ai-assistant { position: fixed; right: 24px; bottom: 24px; z-index: 3000; }
.fab {
  width: 54px; height: 54px; border-radius: 50%; background: #409eff; color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 26px;
  cursor: pointer; box-shadow: 0 4px 16px rgba(64,158,255,0.4); user-select: none;
  transition: transform .2s;
}
.fab:hover { transform: scale(1.08); }
.chat-panel {
  position: absolute; right: 0; bottom: 66px; width: 360px; height: 480px;
  background: #fff; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,21,41,0.18);
  display: flex; flex-direction: column; overflow: hidden;
}
.chat-header {
  height: 46px; padding: 0 14px; background: #409eff; color: #fff;
  display: flex; align-items: center; justify-content: space-between; font-weight: 600;
}
.chat-body { flex: 1; padding: 14px; overflow-y: auto; background: #f5f7fa; }
.msg { display: flex; margin-bottom: 10px; }
.msg.user { justify-content: flex-end; }
.bubble {
  max-width: 78%; padding: 9px 12px; border-radius: 10px; font-size: 13px; line-height: 1.5;
  white-space: pre-wrap; word-break: break-word;
}
.msg.user .bubble { background: #409eff; color: #fff; border-bottom-right-radius: 2px; }
.msg.assistant .bubble { background: #fff; color: #303133; border-bottom-left-radius: 2px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.typing { color: #909399; }
.chat-input { display: flex; gap: 8px; padding: 10px; border-top: 1px solid #ebeef5; }
</style>
