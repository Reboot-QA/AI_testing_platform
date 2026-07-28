<template>
  <div class="h-full">
    <el-card shadow="never" class="h-full">
      <template #header>
        <span>菜单授权</span>
      </template>

      <el-form label-width="90px" class="permission-form">
        <el-form-item label="选择部门">
          <el-select
            v-model="selectedDepartmentId"
            placeholder="请选择部门"
            style="width: 320px"
            filterable
            @change="loadDepartmentPermissions"
          >
            <el-option
              v-for="dept in departments"
              :key="dept.id"
              :label="dept.name"
              :value="dept.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <el-alert
        title="同部门用户共享以下菜单权限，保存后该部门下所有用户立即生效"
        type="info"
        :closable="false"
        show-icon
        class="admin-alert"
      />

      <div v-if="selectedDepartmentId" v-loading="permissionLoading">
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
          <el-checkbox-group v-model="selectedMenus">
            <el-checkbox v-for="item in systemMenus" :key="item.key" :value="item.key">
              {{ item.label }}
            </el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="menu-group">
          <div class="group-title">日志管理</div>
          <div v-for="group in logMenuGroups" :key="group.key" class="menu-subgroup">
            <el-checkbox-group v-model="selectedMenus">
              <el-checkbox v-for="item in group.items" :key="item.key" :value="item.key">
                {{ item.label }}
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>

        <div class="actions">
          <el-button @click="resetMenus">恢复默认</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存授权</el-button>
        </div>
      </div>

      <el-empty v-else description="请选择部门后进行菜单授权" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { departmentApi } from '@/api'
import {
  BUSINESS_MENUS,
  BUSINESS_MENU_GROUPS,
  LOG_MENU_GROUPS,
  STANDALONE_BUSINESS_MENUS,
  SYSTEM_MENUS,
} from '@/config/menus'
import type { Department } from '@/types/common'

const departments = ref<Department[]>([])
const selectedDepartmentId = ref<number | null>(null)
const selectedMenus = ref<string[]>([])
const permissionLoading = ref(false)
const saving = ref(false)

const standaloneBusinessMenus = STANDALONE_BUSINESS_MENUS
const businessMenuGroups = BUSINESS_MENU_GROUPS
const systemMenus = SYSTEM_MENUS
const logMenuGroups = LOG_MENU_GROUPS
const defaultMenus = BUSINESS_MENUS.map((item) => item.key)

async function loadDepartments() {
  departments.value = await departmentApi.list()
}

async function loadDepartmentPermissions() {
  if (!selectedDepartmentId.value) return
  permissionLoading.value = true
  try {
    const data = await departmentApi.getPermissions(selectedDepartmentId.value)
    selectedMenus.value = [...data.menu_permissions]
  } finally {
    permissionLoading.value = false
  }
}

function resetMenus() {
  selectedMenus.value = [...defaultMenus]
}

async function handleSave() {
  if (!selectedDepartmentId.value) return
  saving.value = true
  try {
    const data = await departmentApi.updatePermissions(
      selectedDepartmentId.value,
      selectedMenus.value,
    )
    selectedMenus.value = [...data.menu_permissions]
    ElMessage.success('部门菜单授权已保存')
  } finally {
    saving.value = false
  }
}

onMounted(loadDepartments)
</script>

<style scoped>
.permission-form {
  margin-bottom: var(--ax-space-2);
}

.admin-alert {
  margin-top: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
}

.menu-group {
  margin-top: var(--ax-space-5);
}

.group-title {
  font-size: var(--ax-text-title-sm-size);
  font-weight: 600;
  color: var(--ax-text);
  margin-bottom: var(--ax-space-3);
}

.menu-subgroup {
  margin-top: var(--ax-space-4);
}

.subgroup-title {
  font-size: var(--ax-text-body-size);
  font-weight: 600;
  color: var(--ax-text-tertiary);
  margin-bottom: var(--ax-space-2);
}

.el-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ax-space-3) var(--ax-space-6);
}

.actions {
  margin-top: var(--ax-space-6);
  display: flex;
  gap: var(--ax-space-3);
}
</style>
