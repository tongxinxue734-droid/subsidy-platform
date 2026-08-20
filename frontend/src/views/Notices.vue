<template>
  <div class="page-container">
    <div class="panel">
      <el-radio-group v-model="filter" style="margin-bottom:14px">
        <el-radio-button label="全部">全部</el-radio-button>
        <el-radio-button label="通知">通知</el-radio-button>
        <el-radio-button label="政策">政策</el-radio-button>
        <el-radio-button label="预警">预警</el-radio-button>
      </el-radio-group>
      <el-table :data="filteredItems" border stripe @row-click="showDetail" empty-text="暂无公告">
        <el-table-column label="分类" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.category)" size="small">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题">
          <template #default="{ row }">
            <span :style="{ fontWeight: row.important ? 600 : 400 }">{{ row.important ? '🔔 ' : '' }}{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="publish_date" label="发布日期" width="130" />
      </el-table>

      <el-dialog v-model="dialogVisible" :title="current.title" width="600px">
        <div style="color:#909399;font-size:13px;margin-bottom:12px">
          {{ current.category }} · {{ current.publish_date }}
        </div>
        <div style="line-height:1.8;color:#303133">{{ current.content }}</div>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import request from '../api'

const items = ref([])
const filter = ref('全部')
const filteredItems = computed(() => filter.value === '全部' ? items.value : items.value.filter(i => i.category === filter.value))
const dialogVisible = ref(false)
const current = ref({})

function tagType(c) {
  return { 通知: 'primary', 政策: 'success', 预警: 'danger' }[c] || 'info'
}

function showDetail(row) {
  current.value = row
  dialogVisible.value = true
}

onMounted(async () => {
  const data = await request.get('/notices')
  items.value = data.items
})
</script>
