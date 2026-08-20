<template>
  <div class="login-page">
    <div class="brand-panel">
      <canvas ref="canvasRef" class="brand-canvas"></canvas>
      <div class="brand-content">
        <div class="brand-logo">🏛️</div>
        <div class="brand-title">西安市高龄补贴监管平台</div>
        <div class="brand-divider"></div>
        <div class="brand-sub">全市高龄保健补贴补助发放情况 · 市级 / 区县 / 街道三级监管</div>

        <div class="brand-stats">
          <div class="bstat">
            <div class="bstat-v">{{ stats.people }}</div>
            <div class="bstat-l">在册受益老人</div>
          </div>
          <div class="bstat">
            <div class="bstat-v">{{ stats.amount }}</div>
            <div class="bstat-l">半年发放金额</div>
          </div>
          <div class="bstat">
            <div class="bstat-v">{{ stats.districts }}</div>
            <div class="bstat-l">覆盖区县</div>
          </div>
        </div>

        <div class="brand-features">
          <div class="fcard">
            <div class="f-icon">📊</div>
            <div><div class="f-t">数据驾驶舱</div><div class="f-d">地图下钻 · 态势感知</div></div>
          </div>
          <div class="fcard">
            <div class="f-icon">🛡️</div>
            <div><div class="f-t">智能稽核</div><div class="f-d">风险画像 · 双随机</div></div>
          </div>
          <div class="fcard">
            <div class="f-icon">🤖</div>
            <div><div class="f-t">AI 助手</div><div class="f-d">政策问答 · 数据查询</div></div>
          </div>
          <div class="fcard">
            <div class="f-icon">🔗</div>
            <div><div class="f-t">档案贯通</div><div class="f-d">全生命周期追踪</div></div>
          </div>
        </div>
      </div>
    </div>

    <div class="form-panel">
      <div class="form-card">
        <div class="form-head">
          <div class="form-title">欢迎登录</div>
          <div class="form-sub">请使用监管账号登录系统</div>
        </div>
        <el-form :model="form" @submit.prevent>
          <el-form-item>
            <el-input v-model="form.username" placeholder="监管账号" size="large">
              <template #prefix><el-icon><User /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item>
            <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password @keyup.enter="handleLogin">
              <template #prefix><el-icon><Lock /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="handleLogin">
            登 录
          </el-button>
        </el-form>

        <div class="demo-box">
          <div class="demo-title">演示账号（点击快速填入）</div>
          <div class="demo-chips">
            <span class="chip" @click="fill('admin', 'admin123')">市级 admin</span>
            <span class="chip" @click="fill('yanta', '123456')">区县 雁塔</span>
            <span class="chip" @click="fill('xiaozhai', '123456')">街道 小寨路</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../api'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const canvasRef = ref()
let raf = null
const stats = ref({ people: '104.1 万', amount: '4.23 亿', districts: '17 个' })

function fill(username, password) {
  form.username = username
  form.password = password
}

async function handleLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const data = await request.post('/login', form)
    localStorage.setItem('token', data.token)
    localStorage.setItem('user', JSON.stringify(data.user))
    ElMessage.success('登录成功')
    router.push('/workbench')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '账号或密码错误')
  } finally {
    loading.value = false
  }
}

function initParticles() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  let w = 0
  let h = 0
  const resize = () => {
    w = canvas.width = canvas.offsetWidth
    h = canvas.height = canvas.offsetHeight
  }
  resize()
  window.addEventListener('resize', resize)

  const N = 90
  const pts = Array.from({ length: N }, () => ({
    x: Math.random() * w, y: Math.random() * h,
    vx: (Math.random() - 0.5) * 0.5, vy: (Math.random() - 0.5) * 0.5,
    r: Math.random() * 2 + 1
  }))
  const LINK = 120

  function tick() {
    ctx.clearRect(0, 0, w, h)
    for (const p of pts) {
      p.x += p.vx
      p.y += p.vy
      if (p.x < 0 || p.x > w) p.vx *= -1
      if (p.y < 0 || p.y > h) p.vy *= -1
    }
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const dx = pts[i].x - pts[j].x
        const dy = pts[i].y - pts[j].y
        const d = dx * dx + dy * dy
        if (d < LINK * LINK) {
          ctx.strokeStyle = `rgba(79, 209, 255, ${0.22 * (1 - d / (LINK * LINK))})`
          ctx.lineWidth = 0.6
          ctx.beginPath()
          ctx.moveTo(pts[i].x, pts[i].y)
          ctx.lineTo(pts[j].x, pts[j].y)
          ctx.stroke()
        }
      }
    }
    for (const p of pts) {
      ctx.fillStyle = 'rgba(150, 225, 255, 0.9)'
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fill()
    }
    raf = requestAnimationFrame(tick)
  }
  tick()
}

onMounted(() => {
  initParticles()
  request.get('/standards').then(s => {
    const latest = s.city_stats && s.city_stats[1]
    if (latest) {
      stats.value.people = latest['受益老人']
      stats.value.amount = latest['发放金额']
    }
    stats.value.districts = `${(s.districts || []).length} 个`
  }).catch(() => {})
})
onBeforeUnmount(() => { if (raf) cancelAnimationFrame(raf) })
</script>

<style scoped>
.login-page {
  height: 100vh; display: flex;
  background: linear-gradient(120deg, #002140 0%, #003a70 45%, #0a4f8f 100%);
}
.brand-panel {
  position: relative; flex: 1; display: flex; align-items: center;
  color: #fff; overflow: hidden;
}
.brand-canvas { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0.6; }
.brand-content { position: relative; z-index: 1; padding: 0 72px; max-width: 620px; }
.brand-logo { font-size: 52px; }
.brand-title { font-size: 32px; font-weight: 700; margin-top: 16px; letter-spacing: 1px; }
.brand-divider { width: 44px; height: 3px; border-radius: 2px; background: linear-gradient(90deg, #4fd1ff, #66b1ff); margin: 16px 0; }
.brand-sub { font-size: 15px; opacity: 0.78; line-height: 1.6; }

.brand-stats { display: flex; gap: 14px; margin-top: 40px; }
.bstat {
  flex: 1; padding: 16px 18px; border-radius: 12px; text-align: center;
  background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
  backdrop-filter: blur(6px);
}
.bstat-v { font-size: 24px; font-weight: 700; color: #4fd1ff; }
.bstat-l { font-size: 12px; opacity: 0.75; margin-top: 4px; }

.brand-features { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 26px; }
.fcard {
  display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-radius: 12px;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
}
.f-icon { font-size: 24px; }
.f-t { font-size: 14px; font-weight: 600; }
.f-d { font-size: 12px; opacity: 0.7; margin-top: 2px; }

.form-panel {
  width: 480px; background: #fff; display: flex; align-items: center; justify-content: center;
  box-shadow: -8px 0 40px rgba(0,0,0,0.15);
}
.form-card { width: 340px; }
.form-head { margin-bottom: 30px; }
.form-title { font-size: 26px; font-weight: 700; color: #303133; }
.form-sub { font-size: 14px; color: #909399; margin-top: 6px; }

.demo-box { margin-top: 28px; padding-top: 20px; border-top: 1px dashed #ebeef5; }
.demo-title { font-size: 13px; color: #909399; margin-bottom: 10px; }
.demo-chips { display: flex; gap: 10px; flex-wrap: wrap; }
.chip {
  font-size: 12px; color: #409eff; background: #ecf5ff; border: 1px solid #b3d8ff;
  border-radius: 14px; padding: 5px 12px; cursor: pointer; transition: all .2s;
}
.chip:hover { background: #409eff; color: #fff; border-color: #409eff; }

@media (max-width: 900px) {
  .brand-panel { display: none; }
  .form-panel { width: 100%; }
}
</style>
