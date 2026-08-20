<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="老人档案" name="archive">
        <div class="panel">
          <el-form :inline="true">
            <el-form-item label="区县" v-if="isCity">
              <el-select v-model="filter.district" placeholder="全部" clearable style="width:140px" @change="onDistrictChange">
                <el-option v-for="d in districts" :key="d" :label="d" :value="d" />
              </el-select>
            </el-form-item>
            <el-form-item label="街道" v-if="!isStreet">
              <el-select v-model="filter.street" placeholder="全部" clearable style="width:160px" @change="loadArchive">
                <el-option v-for="s in streetOptions" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>
            <el-form-item label="年龄段">
              <el-select v-model="filter.age" placeholder="全部" clearable style="width:150px" @change="loadArchive">
                <el-option v-for="s in standards" :key="s.年龄段" :label="s.年龄段" :value="s.年龄段" />
              </el-select>
            </el-form-item>
            <el-form-item label="认证状态">
              <el-select v-model="filter.certify" placeholder="全部" clearable style="width:130px" @change="loadArchive">
                <el-option label="已认证" value="已认证" />
                <el-option label="待认证" value="待认证" />
                <el-option label="认证过期" value="认证过期" />
              </el-select>
            </el-form-item>
            <el-form-item label="疑点类型">
              <el-select v-model="filter.suspect" placeholder="全部" clearable style="width:140px" @change="loadArchive">
                <el-option label="疑似冒领" value="疑似冒领" />
                <el-option label="重复领取" value="重复领取" />
                <el-option label="认证过期" value="认证过期" />
                <el-option label="信息异常" value="信息异常" />
              </el-select>
            </el-form-item>
          </el-form>
          <div style="margin-bottom:12px; display:flex; gap:12px; align-items:center">
            <el-button size="small" type="success" :disabled="!selectedIds.length" @click="batchCertify">批量复审</el-button>
            <el-button size="small" type="danger" :disabled="!selectedIds.length" @click="batchStop">批量停发</el-button>
            <el-button size="small" plain @click="exportPage">导出当前页</el-button>
            <span v-if="selectedIds.length" style="color:#909399; font-size:12px">已选 {{ selectedIds.length }} 人</span>
          </div>
          <el-table :data="items" border stripe v-loading="loading" @selection-change="onSelectionChange">
            <el-table-column type="selection" width="45" />
            <el-table-column prop="archive_no" label="档案号" width="150" />
            <el-table-column prop="district" label="区县" width="100" />
            <el-table-column prop="street" label="街道" width="120" />
            <el-table-column prop="name" label="姓名(脱敏)" width="100" />
            <el-table-column prop="gender" label="性别" width="65" />
            <el-table-column prop="age_band" label="年龄段" width="120" />
            <el-table-column prop="standard" label="补贴标准" width="95" />
            <el-table-column prop="certify_status" label="认证状态" width="95">
              <template #default="{ row }">
                <el-tag :type="{ 已认证: 'success', 待认证: 'warning', 认证过期: 'danger' }[row.certify_status]" size="small">{{ row.certify_status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="suspect_type" label="疑点" width="90">
              <template #default="{ row }">{{ row.suspect_type || '—' }}</template>
            </el-table-column>
            <el-table-column prop="id_card" label="身份证(脱敏)" width="180" />
            <el-table-column prop="phone" label="电话(脱敏)" width="125" />
            <el-table-column prop="status" label="发放状态" width="85" />
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            style="margin-top:14px; justify-content:flex-end"
            layout="total, prev, pager, next, sizes"
            :total="total" :page-size="filter.pageSize" :current-page="filter.page"
            @current-change="onPageChange" @size-change="onSizeChange"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="申领登记" name="apply">
        <div class="panel">
          <el-form :model="applyForm" label-width="90px" style="max-width:520px">
            <el-form-item label="申领区县" v-if="isCity">
              <el-select v-model="applyForm.district" placeholder="请选择" style="width:100%" @change="applyForm.street=''">
                <el-option v-for="d in districts" :key="d" :label="d" :value="d" />
              </el-select>
            </el-form-item>
            <el-form-item label="申领街道">
              <el-select v-model="applyForm.street" placeholder="请选择" style="width:100%">
                <el-option v-for="s in applyStreetOptions" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>
            <el-form-item label="性别">
              <el-radio-group v-model="applyForm.gender">
                <el-radio label="男">男</el-radio>
                <el-radio label="女">女</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="年龄段">
              <el-select v-model="applyForm.age_band" placeholder="请选择" style="width:100%">
                <el-option v-for="s in standards" :key="s.年龄段" :label="`${s.年龄段}（${s.补贴标准}）`" :value="s.年龄段" />
              </el-select>
            </el-form-item>
            <el-form-item label="身份证号">
              <el-input v-model="applyForm.id_card" placeholder="选填，系统将脱敏存储" maxlength="18" />
            </el-form-item>
            <el-form-item label="联系电话">
              <el-input v-model="applyForm.phone" placeholder="选填，系统将脱敏存储" maxlength="11" />
            </el-form-item>
            <el-form-item label="家庭住址">
              <el-input v-model="applyForm.address" placeholder="选填，如：XX 小区 XX 栋 XX 室" />
            </el-form-item>
            <el-form-item label="银行卡号">
              <el-input v-model="applyForm.bank_card" placeholder="选填，用于补贴发放" />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="applyForm.remark" type="textarea" :rows="2" placeholder="选填" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleApply">提交登记</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <el-tab-pane label="资格认证" name="certify">
        <div class="panel">
          <el-alert title="对待认证 / 认证过期人员进行年度资格认证，逾期将自动暂停发放" type="warning" show-icon :closable="false" style="margin-bottom:14px" />
          <el-button type="success" :loading="certifying" @click="handleCertify">
            一键完成全部认证（{{ pendingCount }} 人）
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <ElderDetail v-model="detailVisible" :elder-id="detailId" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../api'
import ElderDetail from '../components/ElderDetail.vue'
import { exportCSV } from '../utils/export'

const route = useRoute()

const user = JSON.parse(localStorage.getItem('user') || '{}')
const isCity = computed(() => user.role_level === 1)
const isStreet = computed(() => user.role_level === 3)

const activeTab = ref('archive')
const districts = ref([])
const streets = ref({})
const standards = ref([])
const items = ref([])
const total = ref(0)
const loading = ref(false)
const filter = reactive({ district: '', street: '', age: '', certify: '', suspect: '', page: 1, pageSize: 20 })

const applyForm = reactive({ district: '', street: '', gender: '男', age_band: '', id_card: '', phone: '', address: '', bank_card: '', remark: '' })
const pendingCount = ref(0)
const certifying = ref(false)
const detailVisible = ref(false)
const detailId = ref(null)
const selectedIds = ref([])

const streetOptions = computed(() => {
  const d = isCity.value ? filter.district : user.district
  return d ? (streets.value[d] || []) : []
})
const applyStreetOptions = computed(() => {
  const d = isCity.value ? applyForm.district : user.district
  return d ? (streets.value[d] || []) : []
})

async function loadArchive() {
  loading.value = true
  try {
    const data = await request.get('/elders', { params: { ...filter } })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onDistrictChange() { filter.street = ''; loadArchive() }

async function loadPending() {
  const data = await request.get('/elders', { params: { certify: '待认证', page: 1, pageSize: 1 } })
  pendingCount.value = data.total
}

function onPageChange(p) { filter.page = p; loadArchive() }
function onSizeChange(s) { filter.pageSize = s; filter.page = 1; loadArchive() }

function openDetail(row) { detailId.value = row.id; detailVisible.value = true }

function onSelectionChange(rows) { selectedIds.value = rows.map(r => r.id) }

async function batchCertify() {
  await request.post('/elders/batch', { ids: selectedIds.value, action: 'certify' })
  ElMessage.success(`已完成 ${selectedIds.value.length} 人复审`)
  selectedIds.value = []
  loadArchive()
  loadPending()
}

async function batchStop() {
  await request.post('/elders/batch', { ids: selectedIds.value, action: 'stop' })
  ElMessage.success(`已停发 ${selectedIds.value.length} 人`)
  selectedIds.value = []
  loadArchive()
}

function exportPage() {
  const headers = ['档案号', '区县', '街道', '姓名', '性别', '年龄段', '标准', '认证状态', '疑点', '身份证', '电话', '状态']
  const rows = items.value.map(r => [r.archive_no, r.district, r.street, r.name, r.gender, r.age_band, r.standard, r.certify_status, r.suspect_type, r.id_card, r.phone, r.status])
  exportCSV('老人档案.csv', headers, rows)
}

async function handleApply() {
  if (!applyForm.age_band) { ElMessage.warning('请选择年龄段'); return }
  if (applyForm.id_card && applyForm.id_card.length !== 18) { ElMessage.warning('身份证号应为 18 位'); return }
  if (applyForm.phone && !/^1\d{10}$/.test(applyForm.phone)) { ElMessage.warning('手机号格式不正确'); return }
  const data = await request.post('/elders/apply', applyForm)
  ElMessage.success(data.message || '申领已提交')
  Object.assign(applyForm, { age_band: '', id_card: '', phone: '', address: '', bank_card: '', remark: '' })
  loadPending()
}

async function handleCertify() {
  certifying.value = true
  try {
    const data = await request.post('/elders/certify')
    ElMessage.success(`已完成 ${data.certified_count} 人资格认证`)
    loadPending()
    loadArchive()
  } finally {
    certifying.value = false
  }
}

onMounted(async () => {
  const s = await request.get('/standards')
  districts.value = s.districts
  streets.value = s.streets
  standards.value = s.standards
  loadArchive()
  loadPending()
  if (route.query.open) {
    detailId.value = Number(route.query.open)
    detailVisible.value = true
  }
})

// 已在页面内再次搜索老人时，也能打开详情
watch(() => route.query.open, (val) => {
  if (val) {
    detailId.value = Number(val)
    detailVisible.value = true
  }
})
</script>
