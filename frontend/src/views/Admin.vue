<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <!-- 用户管理 -->
      <el-tab-pane label="用户管理" name="users">
        <div class="panel">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px">
            <div class="panel-title" style="margin:0">监管账号</div>
            <el-button type="primary" @click="openAdd">新增账号</el-button>
          </div>
          <el-table :data="users" border stripe>
            <el-table-column prop="username" label="账号" width="140" />
            <el-table-column prop="name" label="姓名" width="110" />
            <el-table-column label="角色" width="90">
              <template #default="{ row }">
                <el-tag :type="{ 1: 'danger', 2: 'warning', 3: 'info' }[row.role_level]" size="small">{{ roleName(row.role_level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="district" label="管辖区县" width="110" />
            <el-table-column prop="street" label="管辖街道" width="130" />
            <el-table-column prop="dept_name" label="部门" min-width="150" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.active ? 'success' : 'info'" size="small">{{ row.active ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link :type="row.active ? 'danger' : 'success'" @click="toggleUser(row)">{{ row.active ? '停用' : '启用' }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 审计日志 -->
      <el-tab-pane label="审计日志" name="logs">
        <div class="panel">
          <el-table :data="logs" border stripe max-height="560">
            <el-table-column prop="created_at" label="时间" width="170" />
            <el-table-column prop="user_name" label="操作人" width="110" />
            <el-table-column prop="role" label="角色" width="80" />
            <el-table-column prop="action" label="操作" width="150" />
            <el-table-column prop="target" label="对象" min-width="200" />
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 消息中心 -->
      <el-tab-pane label="消息中心" name="messages">
        <div class="panel">
          <el-table :data="messages" border stripe max-height="560">
            <el-table-column prop="category" label="类型" width="90">
              <template #default="{ row }">
                <el-tag :type="{ 预警: 'danger', 待办: 'warning', 通知: 'info', 政策: 'primary' }[row.category]" size="small">{{ row.category }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" width="260" />
            <el-table-column prop="content" label="内容" min-width="260" />
            <el-table-column prop="created_at" label="时间" width="120" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.read ? 'info' : 'danger'" size="small">{{ row.read ? '已读' : '未读' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button v-if="!row.read" link type="primary" @click="readMsg(row)">标记已读</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="dialogVisible" title="新增账号" width="460px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="账号"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" show-password /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_level" style="width:100%">
            <el-option label="市级" :value="1" />
            <el-option label="区县" :value="2" />
            <el-option label="街道" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="管辖区县" v-if="form.role_level >= 2">
          <el-select v-model="form.district" style="width:100%" @change="form.street=''">
            <el-option v-for="d in districts" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="管辖街道" v-if="form.role_level === 3">
          <el-select v-model="form.street" style="width:100%">
            <el-option v-for="s in (streets[form.district] || [])" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门"><el-input v-model="form.dept_name" placeholder="如：雁塔区民政局" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAdd">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api'

const user = JSON.parse(localStorage.getItem('user') || '{}')
const activeTab = ref('users')
const users = ref([])
const logs = ref([])
const messages = ref([])
const districts = ref([])
const streets = ref({})
const dialogVisible = ref(false)
const form = reactive({ username: '', password: '', name: '', role_level: 2, district: '', street: '', dept_name: '' })

function roleName(l) { return { 1: '市级', 2: '区县', 3: '街道' }[l] || '用户' }

async function loadUsers() { users.value = (await request.get('/users')).items }
async function loadLogs() { logs.value = (await request.get('/audit-logs')).items }
async function loadMessages() { messages.value = (await request.get('/messages')).items }

function openAdd() {
  Object.assign(form, { username: '', password: '', name: '', role_level: 2, district: '', street: '', dept_name: '' })
  dialogVisible.value = true
}

async function submitAdd() {
  if (!form.username || !form.password || !form.name) { ElMessage.warning('请填写账号、密码、姓名'); return }
  await request.post('/users', form)
  ElMessage.success('账号已创建')
  dialogVisible.value = false
  loadUsers()
}

async function toggleUser(row) {
  const r = await request.post(`/users/${row.id}/toggle`)
  ElMessage.success(r.active ? '已启用' : '已停用')
  loadUsers()
}

async function readMsg(row) {
  await request.post(`/messages/${row.id}/read`)
  loadMessages()
}

onMounted(async () => {
  const s = await request.get('/standards')
  districts.value = s.districts
  streets.value = s.streets
  if (user.role_level === 1) {
    loadUsers()
    loadLogs()
  }
  loadMessages()
})
</script>
