<template>
  <div class="page-container">
    <div class="panel">
      <div class="panel-title">补贴测算器</div>
      <el-form :inline="true">
        <el-form-item label="老人年龄">
          <el-input-number v-model="calcAge" :min="70" :max="120" :step="1" />
        </el-form-item>
        <el-form-item label="户籍所在地">
          <el-select v-model="calcDistrict" style="width:170px">
            <el-option v-for="d in districts" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
      </el-form>
      <el-alert type="success" :closable="false" show-icon :title="calcResult" />
    </div>

    <div class="panel">
      <div class="panel-title">补贴发放标准</div>
      <el-table :data="standards" border stripe>
        <el-table-column prop="年龄段" label="年龄段" width="200" />
        <el-table-column prop="补贴标准" label="补贴标准" />
      </el-table>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <div class="panel">
          <div class="panel-title">申领补贴及发放流程</div>
          <div class="tip">线上渠道：{{ channels.join('、') }}；线下持身份证、户口簿到村（居）委会申请</div>
          <el-steps direction="vertical" :active="applySteps.length" style="margin-top:14px">
            <el-step v-for="s in applySteps" :key="s.步骤" :title="s.步骤" :description="s.说明" />
          </el-steps>
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="panel">
          <div class="panel-title">资金来源（省/市/区县分担）</div>
          <el-table :data="fundSources" border stripe size="small">
            <el-table-column prop="年龄段" label="年龄段" width="140" />
            <el-table-column prop="省财政负担" label="省财政" />
            <el-table-column prop="市、区县财政负担" label="市、区县财政" />
          </el-table>
          <div class="panel-title" style="margin-top:18px">年度复审规则</div>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="认证周期">{{ certifyRules.周期 }}</el-descriptions-item>
            <el-descriptions-item label="认证方式">{{ (certifyRules.方式 || []).join('、') }}</el-descriptions-item>
            <el-descriptions-item label="逾期处理">{{ certifyRules.逾期处理 }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-col>
    </el-row>

    <div class="panel">
      <div class="panel-title">政策法规库</div>
      <el-table :data="policies" border stripe>
        <el-table-column label="层级" width="90">
          <template #default="{ row }">
            <el-tag :type="tagType(row.层级)" size="small">{{ row.层级 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="政策名称" label="政策名称" width="260" />
        <el-table-column prop="要点" label="要点" />
        <el-table-column prop="来源" label="来源" width="200" />
      </el-table>
      <div class="tip" style="margin-top:10px">注：政策要点整理自公开资料，具体以官方文件为准。</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import request from '../api'

const standards = ref([])
const channels = ref([])
const fundSources = ref([])
const applySteps = ref([])
const certifyRules = ref({ 周期: '', 方式: [], 逾期处理: '' })
const policies = ref([])
const districts = ref([])
const calcAge = ref(80)
const calcDistrict = ref('雁塔区')

const calcResult = computed(() => {
  const age = calcAge.value
  if (age < 70) return '未满 70 周岁，暂不符合申领条件'
  let band
  if (age <= 79) band = '70-79 周岁'
  else if (age <= 89) band = '80-89 周岁'
  else if (age <= 99) band = '90-99 周岁'
  else band = '100 周岁及以上'
  const std = standards.value.find(s => s.年龄段 === band)
  return `符合「${band}」档，每月可领取 ${std?.补贴标准 || ''}；可通过陕西民政通、三秦宝、西民 e 站线上申领，或到 ${calcDistrict.value} 户籍地村（居）委会申请。`
})

onMounted(async () => {
  const data = await request.get('/standards')
  standards.value = data.standards
  channels.value = data.channels
  fundSources.value = data.fund_sources
  applySteps.value = data.apply_steps
  certifyRules.value = data.certify_rules
  policies.value = data.policies
  districts.value = data.districts
})

function tagType(level) {
  return { 国家: 'danger', 省级: 'warning', 市级: 'primary' }[level] || 'info'
}
</script>

<style scoped>
.tip { font-size: 13px; color: #909399; line-height: 1.7; }
</style>
