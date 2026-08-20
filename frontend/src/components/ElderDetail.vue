<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    title="老人档案详情 · 全生命周期"
    size="780px"
    v-loading="loading"
  >
    <template v-if="detail">
      <!-- 画像卡 -->
      <div class="profile-card">
        <div class="profile-avatar">{{ detail.elder.name.slice(0, 1) }}</div>
        <div class="profile-main">
          <div class="profile-name">
            {{ detail.elder.name }}
            <span class="profile-no">{{ detail.elder.archive_no }}</span>
          </div>
          <div class="profile-tags">
            <el-tag size="small">{{ detail.elder.age_band }}</el-tag>
            <el-tag size="small" type="warning">{{ detail.elder.standard }}</el-tag>
            <el-tag size="small" :type="detail.elder.status === '在发' ? 'success' : 'danger'">{{ detail.elder.status }}</el-tag>
            <el-tag size="small" :type="certifyTag(detail.elder.certify_status)">{{ detail.elder.certify_status }}</el-tag>
            <el-tag v-if="detail.elder.suspect_type" size="small" type="danger" effect="dark">{{ detail.elder.suspect_type }}</el-tag>
          </div>
        </div>
        <div class="profile-stat">
          <div class="v">{{ (detail.total_paid || 0).toLocaleString() }}</div>
          <div class="l">累计已发（元）</div>
        </div>
      </div>

      <!-- 基本信息 -->
      <div class="block">
        <div class="block-title">基本信息</div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="档案号">{{ detail.elder.archive_no }}</el-descriptions-item>
          <el-descriptions-item label="姓名(脱敏)">{{ detail.elder.name }}</el-descriptions-item>
          <el-descriptions-item label="区县 / 街道">{{ detail.elder.district }} · {{ detail.elder.street }}</el-descriptions-item>
          <el-descriptions-item label="性别 / 年龄">{{ detail.elder.gender }} · {{ detail.elder.age_band }}</el-descriptions-item>
          <el-descriptions-item label="补贴标准">{{ detail.elder.standard }}</el-descriptions-item>
          <el-descriptions-item label="申领渠道">{{ detail.elder.apply_channel || '—' }}</el-descriptions-item>
          <el-descriptions-item label="身份证(脱敏)">{{ detail.elder.id_card || '—' }}</el-descriptions-item>
          <el-descriptions-item label="手机(脱敏)">{{ detail.elder.phone || '—' }}</el-descriptions-item>
          <el-descriptions-item label="银行卡(脱敏)">{{ detail.elder.bank_card || '—' }}</el-descriptions-item>
          <el-descriptions-item label="社保卡(脱敏)">{{ detail.elder.social_card || '—' }}</el-descriptions-item>
          <el-descriptions-item label="家庭住址(脱敏)" :span="2">{{ detail.elder.address || '—' }}</el-descriptions-item>
          <el-descriptions-item label="联系人(脱敏)">{{ detail.elder.contact || '—' }}</el-descriptions-item>
          <el-descriptions-item label="建档日期">{{ detail.elder.register_date || '—' }}</el-descriptions-item>
          <el-descriptions-item label="最近认证">{{ detail.elder.last_certify || '—' }}</el-descriptions-item>
          <el-descriptions-item label="发放状态">{{ detail.elder.status }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 认证记录 -->
      <div class="block">
        <div class="block-title">年度认证记录</div>
        <el-timeline>
          <el-timeline-item
            v-for="c in detail.certify_records"
            :key="c.certify_date + c.method"
            :timestamp="c.certify_date || '—'"
            :type="c.result === '通过' ? 'success' : 'danger'"
            placement="top"
          >
            <div class="tl">{{ c.method || '待认证' }} · {{ c.result }}</div>
          </el-timeline-item>
        </el-timeline>
      </div>

      <!-- 发放记录 -->
      <div class="block">
        <div class="block-title">近 6 个月发放记录</div>
        <el-table :data="detail.payments" border size="small">
          <el-table-column prop="pay_month" label="发放月份" width="120" />
          <el-table-column label="金额" width="120">
            <template #default="{ row }">{{ row.amount ? row.amount + ' 元' : '—' }}</template>
          </el-table-column>
          <el-table-column label="状态">
            <template #default="{ row }">
              <el-tag :type="{ 已发放: 'success', 停发: 'danger', 待发放: 'warning' }[row.status]" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 关联工单 -->
      <div class="block" v-if="detail.work_orders && detail.work_orders.length">
        <div class="block-title">关联监管工单</div>
        <el-table :data="detail.work_orders" border size="small">
          <el-table-column prop="work_no" label="工单号" width="170" />
          <el-table-column prop="category" label="类别" width="95" />
          <el-table-column prop="title" label="事项" min-width="160" />
          <el-table-column prop="level" label="级别" width="70" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="{ 待处理: 'danger', 整改中: 'warning', 待复核: 'primary', 已销号: 'success' }[row.status]" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 待遇变更 -->
      <div class="block">
        <div class="block-title">待遇变更</div>
        <el-form :inline="true" size="small">
          <el-form-item label="变更类型">
            <el-select v-model="change.change_type" style="width:120px">
              <el-option v-for="t in changeTypes" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="change.change_type === '调档'" label="调至">
            <el-select v-model="change.after_value" style="width:150px">
              <el-option v-for="s in standards" :key="s.年龄段" :label="s.年龄段" :value="s.年龄段" />
            </el-select>
          </el-form-item>
          <el-form-item label="原因">
            <el-input v-model="change.reason" style="width:200px" placeholder="如：年龄增长自动调档" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="submitChange">提交变更</el-button>
          </el-form-item>
        </el-form>
        <el-table v-if="detail.changes && detail.changes.length" :data="detail.changes" border size="small">
          <el-table-column prop="change_type" label="类型" width="90" />
          <el-table-column prop="before_value" label="变更前" />
          <el-table-column prop="after_value" label="变更后" />
          <el-table-column prop="reason" label="原因" width="150" />
          <el-table-column prop="operator" label="操作人" width="90" />
        </el-table>
        <el-empty v-else description="暂无变更记录" :image-size="60" />
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  elderId: { type: [Number, String], default: null }
})
const emit = defineEmits(['update:modelValue'])

const detail = ref(null)
const loading = ref(false)
const standards = ref([])
const changeTypes = ['调档', '停发', '恢复', '死亡终止', '迁出']
const change = ref({ change_type: '调档', after_value: '', reason: '' })

function certifyTag(s) {
  return { 已认证: 'success', 待认证: 'warning', 认证过期: 'danger' }[s] || 'info'
}

async function loadDetail(id) {
  loading.value = true
  try {
    detail.value = await request.get(`/elders/${id}`)
  } finally {
    loading.value = false
  }
}

async function submitChange() {
  if (!change.value.reason) { ElMessage.warning('请填写变更原因'); return }
  await request.post(`/elders/${props.elderId}/change`, change.value)
  ElMessage.success('待遇变更已提交')
  change.value.reason = ''
  change.value.after_value = ''
  loadDetail(props.elderId)
}

watch(
  () => [props.modelValue, props.elderId],
  ([visible, id]) => { if (visible && id) loadDetail(id) }
)

onMounted(async () => {
  const s = await request.get('/standards')
  standards.value = s.standards
})
</script>

<style scoped>
.profile-card {
  display: flex; align-items: center; gap: 16px; padding: 18px 20px; margin-bottom: 16px;
  background: linear-gradient(120deg, #409eff, #66b1ff); border-radius: 10px; color: #fff;
}
.profile-avatar { width: 52px; height: 52px; border-radius: 50%; background: rgba(255,255,255,0.25); display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 700; flex-shrink: 0; }
.profile-main { flex: 1; min-width: 0; }
.profile-name { font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
.profile-no { font-size: 12px; font-weight: 400; opacity: 0.85; }
.profile-tags { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.profile-tags .el-tag { --el-tag-bg-color: rgba(255,255,255,0.9); }
.profile-stat { text-align: right; flex-shrink: 0; }
.profile-stat .v { font-size: 22px; font-weight: 700; }
.profile-stat .l { font-size: 12px; opacity: 0.85; }

.block { border: 1px solid #ebeef5; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px; }
.block-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 12px; display: flex; align-items: center; }
.block-title::before { content: ''; width: 3px; height: 13px; background: #409eff; border-radius: 2px; margin-right: 8px; }
.tl { font-size: 13px; color: #606266; }
</style>
