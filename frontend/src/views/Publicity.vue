<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card">
          <div class="stat-label">公示月份</div>
          <div class="stat-value" style="color:#409eff">{{ data.latest_month }}</div>
          <div class="stat-sub">当月发放</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card">
          <div class="stat-label">当月发放金额</div>
          <div class="stat-value" style="color:#67c23a">{{ (data.total_amount || 0).toLocaleString() }} 万元</div>
          <div class="stat-sub">全市合计</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card">
          <div class="stat-label">当月受益人数</div>
          <div class="stat-value" style="color:#e6a23c">{{ (data.total_count || 0).toLocaleString() }} 人</div>
          <div class="stat-sub">70 周岁以上</div>
        </div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <div class="stat-card">
          <div class="stat-label">公示区县</div>
          <div class="stat-value" style="color:#909399">{{ data.items.length }}</div>
          <div class="stat-sub">应公开尽公开</div>
        </div>
      </el-col>
    </el-row>

    <div class="panel">
      <div style="display:flex; justify-content:space-between; align-items:center">
        <div class="panel-title" style="margin:0">各区县发放公示</div>
        <el-button size="small" plain @click="exportPublicity">导出公示</el-button>
      </div>
      <el-table :data="data.items" border stripe max-height="520">
        <el-table-column type="index" label="#" width="55" />
        <el-table-column prop="district" label="区县" width="140" />
        <el-table-column prop="count" label="受益人数" width="140">
          <template #default="{ row }">{{ row.count.toLocaleString() }} 人</template>
        </el-table-column>
        <el-table-column prop="amount" label="发放金额（万元）" width="160" />
        <el-table-column label="公示状态">
          <template #default>
            <el-tag type="success" size="small">已公示</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="公示渠道">
          <template #default>
            <span style="color:#606266">政府网站 / 公示栏 / 小程序</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="panel">
      <div class="panel-title">社会监督 · 举报投诉</div>
      <el-form :model="report" label-width="90px" style="max-width:620px">
        <el-form-item label="举报内容">
          <el-input v-model="report.content" type="textarea" :rows="3" placeholder="请描述举报事项，如：某街道补贴发放不及时、疑似冒领等" />
        </el-form-item>
        <el-form-item>
          <el-button type="danger" @click="submitReport">提交举报</el-button>
          <span style="color:#909399; font-size:12px; margin-left:10px">举报将生成诉求工单，进入监管闭环处理</span>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api'
import { exportCSV } from '../utils/export'

const data = ref({ items: [], total_amount: 0, total_count: 0, latest_month: '' })
const report = reactive({ content: '' })

async function load() {
  data.value = await request.get('/publicity')
}

async function submitReport() {
  if (!report.content.trim()) { ElMessage.warning('请填写举报内容'); return }
  const r = await request.post('/publicity/report', { content: report.content })
  ElMessage.success(`举报已提交，工单号 ${r.work_no}`)
  report.content = ''
}

function exportPublicity() {
  const rows = data.value.items.map(r => [r.district, r.count, r.amount, '已公示', '政府网站/公示栏/小程序'])
  exportCSV('发放公示.csv', ['区县', '受益人数', '金额(万元)', '状态', '渠道'], rows)
}

onMounted(load)
</script>
