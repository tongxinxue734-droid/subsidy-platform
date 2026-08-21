<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 疑点稽核 -->
      <el-tab-pane label="疑点稽核" name="audit">
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
                  <template #default>
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
          <el-table :data="suspects" border stripe max-height="520" empty-text="暂无疑点人员">
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
      </el-tab-pane>

      <!-- 风险画像 -->
      <el-tab-pane label="风险画像" name="risk">
        <el-row :gutter="16">
          <el-col :span="4" v-for="k in riskKpis" :key="k.label">
            <div class="stat-card">
              <div class="stat-label">{{ k.label }}</div>
              <div class="stat-value" :style="{ color: k.color }">{{ k.value }}</div>
              <div class="stat-sub">{{ k.sub }}</div>
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="16" style="margin-top:16px">
          <el-col :span="12">
            <div class="panel">
              <div class="panel-title">疑点类型分布</div>
              <div ref="typeRef" class="chart" style="height:300px"></div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="panel">
              <div class="panel-title">风险分数段分布</div>
              <div ref="scoreRef" class="chart" style="height:300px"></div>
            </div>
          </el-col>
        </el-row>

        <div class="panel">
          <div class="panel-title">统计异常检测（z-score 离群）</div>
          <el-alert :title="`${anomalyData.method}：认证间隔均值 ${anomalyData.mean} 月（标准差 ${anomalyData.stdev}），自动发现 ${anomalyData.outliers.length} 个异常对象`" :description="anomalyData.policy" type="warning" :closable="false" show-icon style="margin-bottom:12px" />
          <el-table :data="anomalyData.outliers" border stripe size="small" max-height="260" empty-text="当前无可检测异常（数据需含认证过期样本）">
            <el-table-column prop="district" label="区县" width="100" />
            <el-table-column prop="name" label="姓名(脱敏)" width="110" />
            <el-table-column prop="last_certify" label="上次认证" width="110" />
            <el-table-column prop="months" label="间隔(月)" width="90" />
            <el-table-column prop="z_score" label="z 分数" width="90">
              <template #default="{ row }">
                <el-tag type="danger" size="small">{{ row.z_score }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="认证状态" />
          </el-table>
        </div>

        <div class="panel">
          <div class="panel-title">高风险人群清单</div>
          <el-table :data="highList" border stripe max-height="460" empty-text="暂无高风险人员">
            <el-table-column prop="archive_no" label="档案号" width="155" />
            <el-table-column prop="name" label="姓名(脱敏)" width="105" />
            <el-table-column prop="district" label="区县" width="95" />
            <el-table-column prop="street" label="街道" width="120" />
            <el-table-column prop="suspect_type" label="疑点" width="105">
              <template #default="{ row }">
                <el-tag v-if="row.suspect_type" :type="{ 疑似冒领: 'danger', 重复领取: 'danger', 认证过期: 'warning', 信息异常: 'info' }[row.suspect_type]" size="small">{{ row.suspect_type }}</el-tag>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column label="风险分" width="90">
              <template #default="{ row }">
                <el-tag :type="row.score >= 60 ? 'danger' : row.score >= 40 ? 'warning' : 'info'" size="small">{{ row.score }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <ElderDetail v-model="detailVisible" :elder-id="detailId" />
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import request from '../api'
import ElderDetail from '../components/ElderDetail.vue'

const activeTab = ref('audit')
const alertCards = ref([])
const suspectTypes = ref([])
const rectifications = ref([])
const suspects = ref([])
const riskKpis = ref([])
const highList = ref([])
const anomalyData = ref({ mean: 0, stdev: 0, outliers: [], total: 0 })
const typeRef = ref()
const scoreRef = ref()
const detailVisible = ref(false)
const detailId = ref(null)
let typeChart = null
let scoreChart = null
let disposed = false

function openDetail(row) { detailId.value = row.id; detailVisible.value = true }

async function generateWorkOrders() {
  const data = await request.post('/audit/generate')
  ElMessage.success(`已生成 ${data.generated} 件稽核工单，请在「工单督办」中处理`)
}

function renderRiskCharts() {
  if (disposed || typeChart || !typeRef.value) return
  typeChart = echarts.init(typeRef.value)
  typeChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 人（{d}%）' },
    series: [{ type: 'pie', radius: ['40%', '65%'], data: typeDist, color: ['#f56c6c', '#e6a23c', '#f7ba2a', '#909399'] }]
  })
  scoreChart = echarts.init(scoreRef.value)
  scoreChart.setOption({
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: scoreDist.map(d => d.name) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: scoreDist.map(d => d.value), itemStyle: { color: '#f56c6c', borderRadius: [4, 4, 0, 0] } }]
  })
}

let typeDist = []
let scoreDist = []

watch(activeTab, (v) => {
  if (v === 'risk') nextTick(renderRiskCharts)
})

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

  const r = await request.get('/risk')
  riskKpis.value = [
    { label: '在册老人', value: r.kpi.total.toLocaleString(), sub: '抽样档案', color: '#409eff' },
    { label: '高风险', value: r.kpi.high.toLocaleString(), sub: '需立即处置', color: '#f56c6c' },
    { label: '中风险', value: r.kpi.mid.toLocaleString(), sub: '需关注', color: '#e6a23c' },
    { label: '低风险', value: r.kpi.low.toLocaleString(), sub: '正常', color: '#67c23a' },
    { label: '高风险占比', value: ((r.kpi.high / r.kpi.total) * 100).toFixed(1) + '%', sub: '占在册比例', color: '#f56c6c' },
    { label: '待处置', value: (r.kpi.high - r.kpi.disposed).toLocaleString(), sub: '未生成工单', color: '#e6a23c' }
  ]
  highList.value = r.high_list
  typeDist = r.type_dist
  scoreDist = r.score_dist
  anomalyData.value = await request.get('/anomaly')
})

onBeforeUnmount(() => {
  disposed = true
  if (typeChart) typeChart.dispose()
  if (scoreChart) scoreChart.dispose()
})
</script>

<style scoped>
.stat-label { font-size: 13px; color: #909399; }
.stat-value { font-size: 26px; font-weight: 700; margin: 8px 0 4px; }
.stat-sub { font-size: 12px; color: #c0c4cc; }
</style>
