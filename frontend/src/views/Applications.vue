<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="申领工单" name="list">
        <div class="panel">
          <el-form :inline="true">
            <el-form-item label="审核状态">
              <el-select v-model="filter.status" placeholder="全部" clearable style="width:150px" @change="load">
                <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>
            <el-button type="primary" plain @click="load">刷新</el-button>
          </el-form>
          <el-table :data="items" border stripe v-loading="loading" empty-text="暂无申领工单">
            <el-table-column prop="apply_no" label="申领编号" width="160" />
            <el-table-column prop="district" label="区县" width="100" />
            <el-table-column prop="street" label="街道" width="130" />
            <el-table-column prop="name" label="姓名(脱敏)" width="100" />
            <el-table-column prop="gender" label="性别" width="60" />
            <el-table-column prop="age_band" label="年龄段" width="120" />
            <el-table-column prop="standard" label="标准" width="90" />
            <el-table-column prop="channel" label="申领渠道" width="130" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <template v-if="row.status === '待街道审核' || row.status === '待区县审批'">
                  <el-button link type="success" @click="review(row, 'approve')">通过</el-button>
                  <el-button link type="danger" @click="review(row, 'reject')">驳回</el-button>
                </template>
                <span v-else style="color:#c0c4cc">—</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="新增申领" name="apply">
        <div class="panel">
          <el-form :model="form" label-width="100px" style="max-width:600px">
            <el-form-item label="申领区县" v-if="isCity">
              <el-select v-model="form.district" style="width:100%" @change="form.street=''">
                <el-option v-for="d in districts" :key="d" :label="d" :value="d" />
              </el-select>
            </el-form-item>
            <el-form-item label="申领街道" v-if="!isStreet">
              <el-select v-model="form.street" style="width:100%">
                <el-option v-for="s in streetOptions" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>
            <el-form-item label="性别">
              <el-radio-group v-model="form.gender">
                <el-radio label="男">男</el-radio>
                <el-radio label="女">女</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="年龄段">
              <el-select v-model="form.age_band" style="width:100%">
                <el-option v-for="s in standards" :key="s.年龄段" :label="`${s.年龄段}（${s.补贴标准}）`" :value="s.年龄段" />
              </el-select>
            </el-form-item>
            <el-form-item label="申领渠道">
              <el-select v-model="form.channel" style="width:100%">
                <el-option v-for="c in channelOptions" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
            <el-form-item label="身份证号">
              <el-input v-model="form.id_card" placeholder="选填，系统将脱敏存储" maxlength="18" />
            </el-form-item>
            <el-form-item label="联系电话">
              <el-input v-model="form.phone" placeholder="选填，系统将脱敏存储" maxlength="11" />
            </el-form-item>
            <el-form-item label="家庭住址">
              <el-input v-model="form.address" placeholder="选填，如：XX 小区 XX 栋 XX 室" />
            </el-form-item>
            <el-form-item label="银行卡号">
              <el-input v-model="form.bank_card" placeholder="选填，用于补贴发放" />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="如：本人现场申请、子女代办等" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="submitApply">提交申领</el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const isCity = computed(() => user.role_level === 1)
const isStreet = computed(() => user.role_level === 3)

const activeTab = ref('list')
const districts = ref([])
const streets = ref({})
const standards = ref([])
const channels = ref([])
const items = ref([])
const loading = ref(false)
const filter = reactive({ status: '' })
const statuses = ['待街道审核', '待区县审批', '已建档', '已驳回']

const form = reactive({ district: '', street: '', gender: '男', age_band: '', channel: '', id_card: '', phone: '', address: '', bank_card: '', remark: '' })

const streetOptions = computed(() => {
  const d = isCity.value ? form.district : user.district
  return d ? (streets.value[d] || []) : []
})
const channelOptions = computed(() => [...channels.value, '线下村（居）委会'])

function statusTag(s) {
  return { 待街道审核: 'warning', 待区县审批: 'primary', 已建档: 'success', 已驳回: 'danger' }[s] || 'info'
}

async function load() {
  loading.value = true
  try {
    const data = await request.get('/applications', { params: filter })
    items.value = data.items
  } finally {
    loading.value = false
  }
}

async function review(row, action) {
  const tip = action === 'approve'
    ? (row.status === '待街道审核' ? '街道审核通过，进入区县审批' : '区县审批通过，将建档纳入发放')
    : '确认驳回该申领？'
  try {
    await ElMessageBox.confirm(tip, '审核确认', { type: action === 'approve' ? 'success' : 'warning' })
  } catch (e) {
    return
  }
  await request.post(`/applications/${row.id}/review`, { action })
  ElMessage.success(action === 'approve' ? '审核通过' : '已驳回')
  load()
}

async function submitApply() {
  if (!form.age_band) { ElMessage.warning('请选择年龄段'); return }
  if (form.id_card && form.id_card.length !== 18) { ElMessage.warning('身份证号应为 18 位'); return }
  if (form.phone && !/^1\d{10}$/.test(form.phone)) { ElMessage.warning('手机号格式不正确'); return }
  const data = await request.post('/elders/apply', form)
  ElMessage.success(data.message)
  resetForm()
}

function resetForm() {
  Object.assign(form, { gender: '男', age_band: '', channel: '', id_card: '', phone: '', address: '', bank_card: '', remark: '' })
}

onMounted(async () => {
  const s = await request.get('/standards')
  districts.value = s.districts
  streets.value = s.streets
  standards.value = s.standards
  channels.value = s.channels
  load()
})
</script>
