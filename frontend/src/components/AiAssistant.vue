<template>
  <div class="ai-assistant">
    <transition name="el-zoom-in-bottom">
      <div v-if="open" class="chat-panel">
        <div class="chat-header">
          <span>🤖 AI 助手</span>
          <div class="mode-toggle">
            <span :class="{ active: mode === 'chat' }" @click="mode = 'chat'">问答</span>
            <span :class="{ active: mode === 'data' }" @click="mode = 'data'">查数据</span>
          </div>
          <el-button link @click="open = false"><el-icon><Close /></el-icon></el-button>
        </div>
        <div class="chat-body" ref="bodyRef">
          <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
            <div class="bubble">{{ m.content }}</div>
          </div>
          <div v-if="loading" class="msg assistant"><div class="bubble typing">正在思考…</div></div>
        </div>
        <div class="chat-input">
          <el-input
            v-model="input"
            :placeholder="mode === 'chat' ? '问我政策，如：80 岁能领多少' : '问数据，如：雁塔区认证率最低的街道'"
            @keyup.enter="send"
          />
          <el-button type="primary" :disabled="loading" @click="send">发送</el-button>
        </div>
      </div>
    </transition>
    <div class="fab" @click="open = !open">🤖</div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import request from '../api'

const open = ref(false)
const mode = ref('chat')
const input = ref('')
const loading = ref(false)
const bodyRef = ref()
const messages = ref([
  { role: 'assistant', content: '你好，我是平台 AI 助手。\n【问答】问政策：如「80 岁能领多少补贴」\n【查数据】问数据：如「雁塔区认证率最低的街道」' }
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
    if (mode.value === 'data') await sendDataQuery(idx)
    else await sendChat(idx)
  } catch (e) {
    messages.value[idx].content = '抱歉，AI 服务暂时不可用，请稍后再试。'
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

async function sendChat(idx) {
  const token = localStorage.getItem('token')
  const resp = await fetch('/api/ai/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
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
}

async function sendDataQuery(idx) {
  const r = await request.post('/ai/nl2sql', { messages: messages.value.slice(0, idx) })
  if (r.error) {
    messages.value[idx].content = `⚠️ ${r.error}`
  } else if (!r.columns || !r.columns.length) {
    messages.value[idx].content = `📊 无匹配数据\n生成 SQL：${r.sql}`
  } else {
    let text = `📊 查询结果 ${r.count} 条\n生成 SQL：${r.sql}\n\n`
    text += r.columns.join(' | ') + '\n'
    text += r.rows.map(row => row.join(' | ')).join('\n')
    messages.value[idx].content = text
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
  position: absolute; right: 0; bottom: 66px; width: 380px; height: 500px;
  background: #fff; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,21,41,0.18);
  display: flex; flex-direction: column; overflow: hidden;
}
.chat-header {
  height: 46px; padding: 0 14px; background: #409eff; color: #fff;
  display: flex; align-items: center; gap: 10px; font-weight: 600;
}
.mode-toggle { display: flex; background: rgba(255,255,255,0.2); border-radius: 6px; padding: 2px; }
.mode-toggle span {
  font-size: 12px; padding: 3px 10px; border-radius: 5px; cursor: pointer; color: #dbe8ff;
}
.mode-toggle span.active { background: #fff; color: #409eff; font-weight: 600; }
.chat-header .el-button { margin-left: auto; }
.chat-body { flex: 1; padding: 14px; overflow-y: auto; background: #f5f7fa; }
.msg { display: flex; margin-bottom: 10px; }
.msg.user { justify-content: flex-end; }
.bubble {
  max-width: 82%; padding: 9px 12px; border-radius: 10px; font-size: 13px; line-height: 1.5;
  white-space: pre-wrap; word-break: break-word;
}
.msg.user .bubble { background: #409eff; color: #fff; border-bottom-right-radius: 2px; }
.msg.assistant .bubble { background: #fff; color: #303133; border-bottom-left-radius: 2px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.typing { color: #909399; }
.chat-input { display: flex; gap: 8px; padding: 10px; border-top: 1px solid #ebeef5; }
</style>
