<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :span="6" v-for="a in alertCards" :key="a.label">
        <div class="stat-card">
          <div class="stat-label">{{ a.label }}</div>
          <div class="stat-value" :style="{ color: a.color }">{{ a.value }}</div>
          <div class="stat-sub">{{ a.sub }}</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12">
        <div class="panel">
          <div class="panel-title">疑点类型与预警分级</div>
          <el-table :data="suspectTypes" border stripe size="small">
            <el-table-column prop="类型" label="疑点类型" width="120" />
            <el-table-column prop="严重度" label="严重度" width="100">
              <template #default="{ row }">
                <el-tag :type="{ 红色: 'danger', 橙色: 'warning', 黄色: 'warning' }[row.严重度]" size="small">{{ row.严重度 }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="说明" label="说明" />
          </el-table>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="panel">
          <div class="panel-title">资金发放问题整改情况</div>
          <el-table :data="rectifications" border stripe size="small">
            <el-table-column prop="区县" label="区县" width="90" />
            <el-table-column prop="问题" label="问题" />
            <el-table-column label="状态" width="200">
              <template #default="{ row }">
                <el-tag type="success" size="small">✓ 已整改</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>

    <div class="panel">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px">
        <div class="panel-title" style="margin:0">疑点人员清单（待稽核）</div>
        <el-button type="primary" @click="generateWorkOrders">一键生成稽核工单</el-button>
      </div>
      <el-table :data="suspects" border stripe max-height="520">
        <el-table-column type="index" label="#" width="55" />
        <el-table-column prop="district" label="区县" width="110" />
        <el-table-column prop="name" label="姓名(脱敏)" width="110" />
        <el-table-column prop="age_band" label="年龄段" width="130" />
        <el-table-column prop="suspect_type" label="疑点类型" width="110">
          <template #default="{ row }">
            <el-tag :type="{ 疑似冒领: 'danger', 重复领取: 'danger', 认证过期: 'warning', 信息异常: 'info' }[row.suspect_type]" size="small">{{ row.suspect_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="certify_status" label="认证状态" width="100" />
        <el-table-column prop="status" label="发放状态" width="90" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <ElderDetail v-model="detailVisible" :elder-id="detailId" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api'
import ElderDetail from '../components/ElderDetail.vue'

const alertCards = ref([])
const suspectTypes = ref([])
const rectifications = ref([])
const suspects = ref([])
const detailVisible = ref(false)
const detailId = ref(null)

function openDetail(row) { detailId.value = row.id; detailVisible.value = true }

async function generateWorkOrders() {
  const data = await request.post('/audit/generate')
  ElMessage.success(`已生成 ${data.generated} 件稽核工单，请在「工单督办」中处理`)
}

onMounted(async () => {
  const data = await request.get('/audit')
  const a = data.alerts
  alertCards.value = [
    { label: '红色预警', value: a.red, sub: '疑似冒领/重复领取', color: '#f56c6c' },
    { label: '橙色预警', value: a.orange, sub: '认证过期', color: '#e6a23c' },
    { label: '黄色预警', value: a.yellow, sub: '信息异常', color: '#f7ba2a' },
    { label: '疑点合计', value: a.total, sub: '待稽核', color: '#909399' }
  ]
  suspectTypes.value = data.suspect_types
  rectifications.value = data.rectifications
  suspects.value = data.suspects
})
</script>

<style scoped>
.stat-label { font-size: 13px; color: #909399; }
.stat-value { font-size: 26px; font-weight: 700; margin: 8px 0 4px; }
.stat-sub { font-size: 12px; color: #c0c4cc; }
</style>
