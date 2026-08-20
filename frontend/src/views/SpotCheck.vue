<template>
  <div class="page-container">
    <div class="panel">
      <div style="display:flex; justify-content:space-between; align-items:center">
        <div>
          <div class="panel-title" style="margin:0">双随机 · 一公开</div>
          <div style="color:#909399; font-size:13px; margin-top:6px">随机抽取检查对象 · 随机选派检查人员 · 抽查结果公开</div>
        </div>
        <div style="display:flex; gap:10px; align-items:center">
          <span style="font-size:13px; color:#606266">抽查人数</span>
          <el-input-number v-model="count" :min="5" :max="50" size="small" />
          <el-button type="primary" @click="generate">发起抽查</el-button>
        </div>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="9">
        <div class="panel">
          <div class="panel-title">抽查任务</div>
          <el-table :data="tasks" border stripe size="small" highlight-current-row empty-text="暂无抽查任务，请先发起抽查" @current-change="onSelectTask">
            <el-table-column prop="task_no" label="任务编号" width="150" />
            <el-table-column prop="name" label="任务名称" min-width="120" show-overflow-tooltip />
            <el-table-column prop="elder_count" label="抽查人数" width="80" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }"><el-tag :type="row.status === '检查中' ? 'warning' : 'success'" size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
      <el-col :span="15">
        <div class="panel">
          <div class="panel-title">抽查记录 <span v-if="currentTask" style="color:#909399; font-size:12px; font-weight:400">（{{ currentTask.task_no }}）</span></div>
          <el-table :data="records" border stripe size="small" max-height="420" empty-text="请选择左侧任务查看抽查记录">
            <el-table-column prop="archive_no" label="档案号" width="150" />
            <el-table-column prop="name" label="姓名(脱敏)" width="105" />
            <el-table-column prop="district" label="区县" width="95" />
            <el-table-column prop="checker" label="检查人员" width="90" />
            <el-table-column prop="result" label="检查结果" width="100">
              <template #default="{ row }">
                <el-tag :type="{ 待检查: 'info', 正常: 'success', 发现问题: 'danger' }[row.result]" size="small">{{ row.result }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="登记结果" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="success" size="small" @click="setResult(row, '正常')">正常</el-button>
                <el-button link type="danger" size="small" @click="setResult(row, '发现问题')">发现问题</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api'

const count = ref(20)
const tasks = ref([])
const records = ref([])
const currentTask = ref(null)

async function loadTasks() {
  tasks.value = (await request.get('/spotcheck')).items
}

async function generate() {
  const r = await request.post('/spotcheck/generate', { count: count.value })
  ElMessage.success(`已发起抽查，抽取 ${r.count} 人`)
  await loadTasks()
  if (tasks.value.length) onSelectTask(tasks.value[0])
}

async function onSelectTask(row) {
  if (!row) return
  currentTask.value = row
  records.value = (await request.get(`/spotcheck/${row.id}/records`)).items
}

async function setResult(row, result) {
  await request.post(`/spotcheck/record/${row.id}/result`, { result })
  ElMessage.success(result === '发现问题' ? '已登记问题，并生成稽核工单' : '已登记为正常')
  if (currentTask.value) onSelectTask(currentTask.value)
}

onMounted(loadTasks)
</script>
