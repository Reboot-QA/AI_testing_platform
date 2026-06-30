<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <span>菜单授权</span>
      </template>

      <el-form label-width="90px" class="permission-form">
        <el-form-item label="选择用户">
          <el-select
            v-model="selectedUserId"
            placeholder="请选择用户"
            style="width: 320px"
            filterable
            @change="loadUserPermissions"
          >
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="`${user.username}${user.full_name ? `（${user.full_name}）` : ''}`"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="selectedUser?.role === 'admin'"
        title="管理员默认拥有全部菜单权限，无需单独授权"
        type="info"
        :closable="false"
        show-icon
        class="admin-alert"
      />

      <div v-else-if="selectedUserId" v-loading="permissionLoading">
        <div class="menu-group">
          <div class="group-title">业务菜单</div>
          <el-checkbox-group v-model="selectedMenus">
            <el-checkbox v-for="item in standaloneBusinessMenus" :key="item.key" :value="item.key">
              {{ item.label }}
            </el-checkbox>
          </el-checkbox-group>
          <div v-for="group in businessMenuGroups" :key="group.key" class="menu-subgroup">
            <div class="subgroup-title">{{ group.label }}</div>
            <el-checkbox-group v-model="selectedMenus">
              <el-checkbox v-for="item in group.items" :key="item.key" :value="item.key">
                {{ item.label }}
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>

        <div class="menu-group">
          <div class="group-title">系统管理</div>
          <el-alert
            title="系统管理菜单仅管理员账号可访问，分配给测试员不会生效"
            type="warning"
            :closable="false"
            show-icon
            class="system-tip"
          />
          <el-checkbox-group v-model="selectedMenus">
            <el-checkbox v-for="item in systemMenus" :key="item.key" :value="item.key">
              {{ item.label }}
            </el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="actions">
          <el-button @click="resetMenus">恢复默认</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存授权</el-button>
        </div>
      </div>

      <el-empty v-else description="请选择用户后进行菜单授权" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { userApi } from '@/api'
import {
  BUSINESS_MENUS,
  BUSINESS_MENU_GROUPS,
  STANDALONE_BUSINESS_MENUS,
  SYSTEM_MENUS,
} from '@/config/menus'

const users = ref([])
const selectedUserId = ref(null)
const selectedMenus = ref([])
const permissionLoading = ref(false)
const saving = ref(false)

const standaloneBusinessMenus = STANDALONE_BUSINESS_MENUS
const businessMenuGroups = BUSINESS_MENU_GROUPS
const systemMenus = SYSTEM_MENUS
const defaultMenus = BUSINESS_MENUS.map((item) => item.key)

const selectedUser = computed(() => users.value.find((item) => item.id === selectedUserId.value))

async function loadUsers() {
  users.value = await userApi.list()
}

async function loadUserPermissions() {
  if (!selectedUserId.value) return
  permissionLoading.value = true
  try {
    const data = await userApi.getPermissions(selectedUserId.value)
    selectedMenus.value = [...data.menu_permissions]
  } finally {
    permissionLoading.value = false
  }
}

function resetMenus() {
  selectedMenus.value = [...defaultMenus]
}

async function handleSave() {
  if (!selectedUserId.value || selectedUser.value?.role === 'admin') return
  saving.value = true
  try {
    const data = await userApi.updatePermissions(selectedUserId.value, selectedMenus.value)
    selectedMenus.value = [...data.menu_permissions]
    ElMessage.success('菜单授权已保存')
  } finally {
    saving.value = false
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.permission-form {
  margin-bottom: 8px;
}

.admin-alert {
  margin-top: 8px;
}

.menu-group {
  margin-top: 20px;
}

.group-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a365d;
  margin-bottom: 12px;
}

.menu-subgroup {
  margin-top: 16px;
}

.subgroup-title {
  font-size: 14px;
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 8px;
}

.system-tip {
  margin-bottom: 12px;
}

.el-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
}

.actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}
</style>
