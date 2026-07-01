<template>
  <div class="api-automation">
    <div class="toolbar">
      <el-select v-model="projectId" placeholder="选择项目" style="width: 260px" @change="handleProjectChange">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-button type="primary" :disabled="!projectId" @click="reloadAll">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <div class="main-content">
      <div v-if="activeTab === 'env'">
        <el-card shadow="never">
          <div class="pane-toolbar">
            <el-button type="primary" :disabled="!projectId" @click="openEnvDialog()">
              <el-icon><Plus /></el-icon> 新建环境
            </el-button>
          </div>
          <el-table v-loading="envLoading" :data="environments" stripe>
            <el-table-column prop="name" label="环境名称" min-width="140" />
            <el-table-column prop="base_url" label="Base URL" min-width="220" show-overflow-tooltip />
            <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openEnvDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="removeEnv(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <div v-else-if="activeTab === 'suite'">
        <el-row :gutter="16">
          <el-col :span="4">
            <el-card shadow="never" class="suite-card">
              <template #header>
                <div class="card-header">
                  <span>测试套件</span>
                  <el-dropdown trigger="click" :disabled="!projectId" @command="handleCreateCommand">
                    <el-button type="primary" link :disabled="!projectId">
                      新建<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="folder">新建目录</el-dropdown-item>
                        <el-dropdown-item command="suite">新建套件</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </template>
              <div v-loading="suiteLoading" class="suite-tree-wrap">
                <el-tree
                  v-if="suiteTree.length"
                  ref="suiteTreeRef"
                  :data="suiteTree"
                  node-key="id"
                  :props="suiteTreeProps"
                  highlight-current
                  default-expand-all
                  draggable
                  :expand-on-click-node="false"
                  :allow-drag="allowSuiteTreeDrag"
                  :allow-drop="allowSuiteTreeDrop"
                  @node-click="handleSuiteTreeClick"
                  @node-drop="handleSuiteTreeDrop"
                >
                  <template #default="{ data }">
                    <div
                      class="suite-tree-node"
                      :class="{
                        active: !data.is_folder && data.id === suiteId,
                        folder: data.is_folder,
                        'case-drop-target': caseDragOverId === data.id,
                      }"
                      @dragover.prevent="handleCaseDragOver(data)"
                      @dragleave="handleCaseDragLeave(data)"
                      @drop.prevent="handleCaseDrop(data)"
                    >
                      <el-icon class="suite-tree-icon">
                        <Folder v-if="data.is_folder" />
                        <Document v-else />
                      </el-icon>
                      <span class="suite-tree-label" :title="data.name">{{ data.name }}</span>
                      <template v-if="!data.is_folder">
                        <el-tag size="small" class="suite-tree-tag">{{ data.case_count }} 条</el-tag>
                      </template>
                      <div class="suite-tree-actions" @click.stop @mousedown.stop>
                        <el-dropdown trigger="click" @command="(cmd) => handleSuiteTreeCommand(cmd, data)">
                          <el-button link type="primary" size="small">操作</el-button>
                          <template #dropdown>
                            <el-dropdown-menu>
                              <el-dropdown-item v-if="data.is_folder" command="add-folder">新建子目录</el-dropdown-item>
                              <el-dropdown-item v-if="data.is_folder" command="add-suite">新建套件</el-dropdown-item>
                              <el-dropdown-item command="edit">{{ data.is_folder ? '编辑目录' : '编辑套件' }}</el-dropdown-item>
                              <el-dropdown-item command="copy">复制</el-dropdown-item>
                              <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                            </el-dropdown-menu>
                          </template>
                        </el-dropdown>
                      </div>
                    </div>
                  </template>
                </el-tree>
                <el-empty v-else-if="!suiteLoading" description="暂无目录或套件" />
              </div>
            </el-card>
          </el-col>

          <el-col :span="20">
            <el-card shadow="never" class="case-workspace-card">
              <template #header>
                <div class="card-header">
                  <span>接口调试</span>
                  <div class="header-actions">
                    <el-button :disabled="!suiteId" @click="openImportDialog()">
                      <el-icon><Upload /></el-icon> 导入抓包
                    </el-button>
                    <el-button :disabled="!suiteId" @click="openSwaggerDialog()">
                      <el-icon><Upload /></el-icon> 导入 Swagger
                    </el-button>
                    <el-button
                      type="success"
                      :disabled="!suiteId || running"
                      :loading="running"
                      @click="handleRunSuite"
                    >
                      <el-icon><VideoPlay /></el-icon> 执行套件
                    </el-button>
                  </div>
                </div>
              </template>
              <div class="case-workspace">
                <div class="case-list-panel">
                  <div class="panel-title-row">
                    <el-checkbox
                      v-if="cases.length"
                      :model-value="isAllCasesSelected"
                      :indeterminate="isCaseSelectionIndeterminate"
                      @change="toggleSelectAllCases"
                      @click.stop
                    />
                    <span class="panel-title">用例列表</span>
                    <el-button
                      v-if="selectedCaseIds.length"
                      link
                      type="danger"
                      size="small"
                      :loading="caseBatchDeleting"
                      @click="batchRemoveCases"
                    >
                      批量删除({{ selectedCaseIds.length }})
                    </el-button>
                  </div>
                  <div v-loading="caseLoading" class="case-mini-list">
                    <div
                      v-for="item in cases"
                      :key="item.id"
                      class="case-mini-item"
                      :class="{ active: activeCaseId === item.id, dragging: draggingCaseId === item.id }"
                      draggable="true"
                      @click="selectCase(item)"
                      @dragstart="handleCaseDragStart($event, item)"
                      @dragend="handleCaseDragEnd"
                    >
                      <div class="case-mini-top">
                        <el-checkbox
                          :model-value="selectedCaseIds.includes(item.id)"
                          @click.stop
                          @change="(checked) => toggleCaseSelection(item.id, checked)"
                        />
                        <span class="case-mini-name">{{ item.name }}</span>
                        <el-button link type="danger" size="small" @mousedown.stop @click.stop="removeCase(item)">删</el-button>
                      </div>
                      <div class="case-mini-meta">
                        <el-tag :type="methodType[item.method] || 'info'" size="small">{{ item.method }}</el-tag>
                        <span class="case-mini-path">{{ item.path }}</span>
                      </div>
                    </div>
                    <el-empty v-if="!cases.length && !caseLoading" description="暂无用例，请新建" :image-size="48" />
                  </div>
                </div>
                <div class="case-editor-panel">
                  <ApiCaseEditor
                    v-if="suiteId"
                    ref="caseEditorRef"
                    :suite-id="suiteId"
                    :case-data="activeCase"
                    :environments="environments"
                    :suite-environment-id="currentSuite?.environment_id"
                    :case-count="cases.length"
                    @saved="onCaseSaved"
                    @new="onNewCase"
                    @import="openImportDialog()"
                  />
                  <el-empty v-else description="请先选择测试套件" />
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <div v-else-if="activeTab === 'report'">
        <el-card shadow="never">
          <el-table v-loading="reportLoading" :data="runs" stripe @row-click="viewReport">
            <el-table-column prop="id" label="报告 ID" width="90" />
            <el-table-column prop="suite_name" label="套件" min-width="160" />
            <el-table-column prop="status" label="结果" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType[row.status]">{{ statusLabel[row.status] || row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="通过率" width="120">
              <template #default="{ row }">
                <span :class="row.pass_rate >= 100 ? 'text-success' : 'text-danger'">{{ row.pass_rate }}%</span>
              </template>
            </el-table-column>
            <el-table-column label="通过/失败/总数" width="160">
              <template #default="{ row }">
                {{ row.passed_count }}/{{ row.failed_count }}/{{ row.total_count }}
              </template>
            </el-table-column>
            <el-table-column label="耗时" width="100">
              <template #default="{ row }">{{ formatDuration(row.duration_ms) }}</template>
            </el-table-column>
            <el-table-column prop="started_at" label="执行时间" min-width="170">
              <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click.stop="viewReport(row)">查看报告</el-button>
                <el-button link type="danger" @click.stop="removeRun(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <div v-else-if="activeTab === 'schedule'">
        <el-card shadow="never">
          <el-alert
            title="定时任务按服务器本地时间调度。保存后会重新计算「下次执行」；若今日设定时刻已过，将安排到明天同一时刻。到点后会自动执行，也可使用「立即执行」验证。"
            type="info"
            :closable="false"
            show-icon
            class="schedule-tip"
          />
          <div class="pane-toolbar">
            <el-button type="primary" :disabled="!projectId" @click="openScheduleDialog()">
              <el-icon><Plus /></el-icon> 新建定时任务
            </el-button>
          </div>
          <el-table v-loading="scheduleLoading" :data="schedules" stripe>
            <el-table-column prop="name" label="任务名称" min-width="140" />
            <el-table-column prop="suite_name" label="测试套件" min-width="140" />
            <el-table-column prop="schedule_desc" label="执行计划" min-width="140" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-switch
                  v-model="row.enabled"
                  :loading="scheduleTogglingId === row.id"
                  @change="(val) => handleToggleSchedule(row, val)"
                />
              </template>
            </el-table-column>
            <el-table-column label="上次执行" min-width="170">
              <template #default="{ row }">
                <div v-if="row.last_run_at">{{ formatTime(row.last_run_at) }}</div>
                <div v-else class="text-muted">-</div>
                <el-tag v-if="row.last_run_status" :type="statusType[row.last_run_status]" size="small">
                  {{ statusLabel[row.last_run_status] || row.last_run_status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="下次执行" min-width="170">
              <template #default="{ row }">
                {{ row.enabled && row.next_run_at ? formatTime(row.next_run_at) : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button link type="success" :loading="scheduleRunningId === row.id" @click="handleRunScheduleNow(row)">
                  立即执行
                </el-button>
                <el-button link type="primary" @click="openScheduleDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="removeSchedule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </div>

    <!-- 环境对话框 -->
    <el-dialog v-model="envDialogVisible" :title="envEditing ? '编辑环境' : '新建环境'" width="560px">
      <el-form ref="envFormRef" :model="envForm" :rules="envRules" label-width="100px">
        <el-form-item label="环境名称" prop="name">
          <el-input v-model="envForm.name" />
        </el-form-item>
        <el-form-item label="Base URL" prop="base_url">
          <el-input v-model="envForm.base_url" placeholder="https://api.example.com" />
        </el-form-item>
        <el-form-item label="默认请求头">
          <el-input v-model="envForm.default_headers" type="textarea" :rows="4" placeholder='{"Content-Type":"application/json"}' />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="envForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="envDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="envSaving" @click="saveEnv">保存</el-button>
      </template>
    </el-dialog>

    <!-- 目录对话框 -->
    <el-dialog v-model="folderDialogVisible" :title="folderEditing ? '编辑目录' : '新建目录'" width="480px">
      <el-form ref="folderFormRef" :model="folderForm" :rules="folderRules" label-width="100px">
        <el-form-item label="目录名称" prop="name">
          <el-input v-model="folderForm.name" placeholder="例如：登录模块" />
        </el-form-item>
        <el-form-item label="上级目录">
          <el-tree-select
            v-model="folderForm.parent_id"
            :data="folderTreeOptions"
            :props="folderSelectProps"
            check-strictly
            clearable
            placeholder="留空表示根目录"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="folderForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="folderDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="folderSaving" @click="saveFolder">保存</el-button>
      </template>
    </el-dialog>

    <!-- 套件对话框 -->
    <el-dialog v-model="suiteDialogVisible" :title="suiteEditing ? '编辑套件' : '新建套件'" width="520px">
      <el-form ref="suiteFormRef" :model="suiteForm" :rules="suiteRules" label-width="100px">
        <el-form-item label="套件名称" prop="name">
          <el-input v-model="suiteForm.name" />
        </el-form-item>
        <el-form-item label="上级目录">
          <el-tree-select
            v-model="suiteForm.parent_id"
            :data="suiteFolderTreeOptions"
            :props="folderSelectProps"
            check-strictly
            clearable
            placeholder="留空表示根目录"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="执行环境" prop="environment_id">
          <el-select v-model="suiteForm.environment_id" style="width: 100%" placeholder="选择环境">
            <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="suiteForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="suiteDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="suiteSaving" @click="saveSuite">保存</el-button>
      </template>
    </el-dialog>

    <!-- 抓包导入 -->
    <el-dialog v-model="importDialogVisible" title="导入抓包数据" width="760px">
      <el-alert
        title="支持浏览器 DevTools 的 fetch/cURL，以及 Charles 的 Copy cURL Request、Copy Request，将自动解析 URL、方法、请求头、请求体并生成用例"
        type="info"
        :closable="false"
        show-icon
        class="import-tip"
      />
      <el-form label-width="100px" class="import-form">
        <el-form-item label="抓包内容">
          <el-input
            v-model="importRawText"
            type="textarea"
            :rows="12"
            placeholder="粘贴 Copy as fetch / Copy as cURL / Charles Copy cURL Request / Charles Copy Request..."
          />
        </el-form-item>
        <el-form-item label="用例名称">
          <el-input v-model="importCaseName" placeholder="可选，默认按 方法+路径 自动生成" />
        </el-form-item>
        <el-form-item label="自动环境">
          <el-switch v-model="importAutoEnv" />
          <span class="form-tip inline-tip">根据抓包 URL 自动创建/关联环境 Base URL</span>
        </el-form-item>
      </el-form>

      <div v-if="importPreview.length" class="import-preview">
        <div class="preview-title">解析预览（{{ importPreview.length }} 条）</div>
        <el-table :data="importPreview" size="small" border>
          <el-table-column prop="name" label="用例名称" min-width="140" />
          <el-table-column prop="method" label="方法" width="80" />
          <el-table-column prop="path" label="路径" min-width="160" show-overflow-tooltip />
          <el-table-column prop="base_url" label="Base URL" min-width="180" show-overflow-tooltip />
        </el-table>
      </div>

      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button :disabled="!importRawText.trim()" :loading="importParsing" @click="handleParseCapture">
          解析预览
        </el-button>
        <el-button
          type="primary"
          :disabled="!importPreview.length"
          :loading="importSaving"
          @click="handleImportCapture"
        >
          确认导入
        </el-button>
      </template>
    </el-dialog>

    <!-- Swagger 导入 -->
    <el-dialog v-model="swaggerDialogVisible" title="导入 Swagger 文档" width="760px">
      <el-alert
        title="支持 OpenAPI 2.0 / 3.x 的 JSON 或 YAML，可从文档内容或 URL 解析接口并批量生成用例"
        type="info"
        :closable="false"
        show-icon
        class="import-tip"
      />
      <el-form label-width="100px" class="import-form">
        <el-form-item label="数据来源">
          <div class="swagger-source-group">
            <div
              class="swagger-source-card"
              :class="{ active: swaggerSourceType === 'content' }"
              @click="swaggerSourceType = 'content'"
            >
              <div class="source-card-main">
                <span class="source-card-icon">{{ '{}' }}</span>
                <span class="source-card-label">Swagger</span>
              </div>
              <span class="source-card-radio" :class="{ checked: swaggerSourceType === 'content' }" />
            </div>
            <div
              class="swagger-source-card"
              :class="{ active: swaggerSourceType === 'url' }"
              @click="swaggerSourceType = 'url'"
            >
              <div class="source-card-main">
                <span class="source-card-icon">{{ '{}' }}</span>
                <span class="source-card-label">Swagger URL</span>
              </div>
              <span class="source-card-radio" :class="{ checked: swaggerSourceType === 'url' }" />
            </div>
          </div>
        </el-form-item>
        <el-form-item v-if="swaggerSourceType === 'content'" label="文档内容">
          <el-input
            v-model="swaggerRawText"
            type="textarea"
            :rows="12"
            placeholder="粘贴 Swagger / OpenAPI JSON 或 YAML..."
          />
        </el-form-item>
        <el-form-item v-else label="文档 URL">
          <el-input
            v-model="swaggerUrl"
            placeholder="https://example.com/v3/api-docs 或 swagger.json"
          />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input
            v-model="swaggerBaseUrl"
            placeholder="可选，文档未配置 servers/host 时可手动指定，如 https://api.example.com"
          />
        </el-form-item>
        <el-form-item label="自动环境">
          <el-switch v-model="swaggerAutoEnv" />
          <span class="form-tip inline-tip">根据 Swagger servers/host 自动创建/关联环境 Base URL</span>
        </el-form-item>
      </el-form>

      <div v-if="swaggerPreview.length" class="import-preview">
        <div class="preview-title">解析预览（{{ swaggerPreview.length }} 条）</div>
        <el-table :data="swaggerPreview" size="small" border max-height="280">
          <el-table-column prop="name" label="用例名称" min-width="140" />
          <el-table-column prop="method" label="方法" width="80" />
          <el-table-column prop="path" label="路径" min-width="160" show-overflow-tooltip />
          <el-table-column prop="base_url" label="Base URL" min-width="180" show-overflow-tooltip />
        </el-table>
      </div>

      <template #footer>
        <el-button @click="swaggerDialogVisible = false">取消</el-button>
        <el-button :disabled="!canParseSwagger" :loading="swaggerParsing" @click="handleParseSwagger">
          解析预览
        </el-button>
        <el-button
          type="primary"
          :disabled="!swaggerPreview.length"
          :loading="swaggerSaving"
          @click="handleImportSwagger"
        >
          确认导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 定时任务对话框 -->
    <el-dialog v-model="scheduleDialogVisible" :title="scheduleEditing ? '编辑定时任务' : '新建定时任务'" width="560px">
      <el-form ref="scheduleFormRef" :model="scheduleForm" :rules="scheduleRules" label-width="100px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="scheduleForm.name" placeholder="例如：每日回归" />
        </el-form-item>
        <el-form-item label="测试套件" prop="suite_id">
          <el-select v-model="scheduleForm.suite_id" style="width: 100%" placeholder="选择套件">
            <el-option v-for="s in runnableSuites" :key="s.id" :label="suiteOptionLabel(s)" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="调度类型" prop="schedule_type">
          <el-select v-model="scheduleForm.schedule_type" style="width: 100%">
            <el-option label="每天固定时间" value="daily" />
            <el-option label="每周固定时间" value="weekly" />
            <el-option label="间隔执行" value="interval" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="scheduleForm.schedule_type === 'weekly'" label="星期" prop="week_day">
          <el-select v-model="scheduleForm.week_day" style="width: 100%">
            <el-option v-for="item in weekDays" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="scheduleForm.schedule_type !== 'interval'" label="执行时间" prop="run_time">
          <el-time-picker
            v-model="scheduleForm.run_time"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="选择时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="scheduleForm.schedule_type === 'interval'" label="间隔(分钟)" prop="interval_minutes">
          <el-input-number v-model="scheduleForm.interval_minutes" :min="5" :max="10080" style="width: 100%" />
          <div class="form-tip">最少 5 分钟，建议不低于 15 分钟</div>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="scheduleForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="scheduleSaving" @click="saveSchedule">保存</el-button>
      </template>
    </el-dialog>

    <!-- 可视化报告 -->
    <el-drawer v-model="reportVisible" size="72%" title="测试报告">
      <div v-if="reportDetail" v-loading="reportDetailLoading" class="report-panel">
        <div class="report-summary">
          <div class="summary-card">
            <div class="summary-label">执行结果</div>
            <el-tag :type="statusType[reportDetail.status]" size="large">
              {{ statusLabel[reportDetail.status] || reportDetail.status }}
            </el-tag>
          </div>
          <div class="summary-card">
            <div class="summary-label">通过率</div>
            <el-progress type="dashboard" :percentage="reportDetail.pass_rate" :color="progressColor" />
          </div>
          <div class="summary-card">
            <div class="summary-label">通过 / 失败 / 总数</div>
            <div class="summary-value">
              <span class="text-success">{{ reportDetail.passed_count }}</span>
              /
              <span class="text-danger">{{ reportDetail.failed_count }}</span>
              /
              {{ reportDetail.total_count }}
            </div>
          </div>
          <div class="summary-card">
            <div class="summary-label">总耗时</div>
            <div class="summary-value">{{ formatDuration(reportDetail.duration_ms) }}</div>
          </div>
        </div>

        <el-divider content-position="left">用例执行明细</el-divider>

        <el-collapse v-model="expandedSteps">
          <el-collapse-item
            v-for="step in reportDetail.step_results"
            :key="step.id"
            :name="step.id"
          >
            <template #title>
              <div class="step-title">
                <el-tag :type="statusType[step.status]" size="small">
                  {{ statusLabel[step.status] || step.status }}
                </el-tag>
                <span class="step-method">{{ step.method }}</span>
                <span class="step-name">{{ step.case_name }}</span>
                <span class="step-duration">{{ formatDuration(step.duration_ms) }}</span>
              </div>
            </template>

            <div class="step-detail">
              <div class="detail-block">
                <div class="detail-label">请求 URL</div>
                <div class="detail-url">{{ step.url }}</div>
              </div>

              <el-row :gutter="16">
                <el-col :span="12">
                  <div class="detail-block">
                    <div class="detail-label">请求头</div>
                    <pre class="code-block">{{ step.request_headers || '-' }}</pre>
                  </div>
                  <div class="detail-block">
                    <div class="detail-label">请求体</div>
                    <pre class="code-block">{{ step.request_body || '-' }}</pre>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="detail-block">
                    <div class="detail-label">响应状态</div>
                    <div>{{ step.response_status ?? '-' }}</div>
                  </div>
                  <div class="detail-block">
                    <div class="detail-label">响应头</div>
                    <pre class="code-block">{{ step.response_headers || '-' }}</pre>
                  </div>
                  <div class="detail-block">
                    <div class="detail-label">响应体</div>
                    <pre class="code-block">{{ step.response_body || '-' }}</pre>
                  </div>
                </el-col>
              </el-row>

              <div v-if="step.error_message" class="detail-block">
                <el-alert :title="step.error_message" type="error" show-icon :closable="false" />
              </div>

              <div class="detail-block">
                <div class="detail-label">断言结果</div>
                <el-table :data="step.assertion_results" size="small" border>
                  <el-table-column prop="type" label="类型" width="120" />
                  <el-table-column prop="message" label="说明" min-width="220" />
                  <el-table-column label="期望" min-width="120">
                    <template #default="{ row }">{{ formatValue(row.expected) }}</template>
                  </el-table-column>
                  <el-table-column label="实际" min-width="120">
                    <template #default="{ row }">{{ formatValue(row.actual) }}</template>
                  </el-table-column>
                  <el-table-column label="结果" width="80">
                    <template #default="{ row }">
                      <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
                        {{ row.passed ? '通过' : '失败' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Document, Folder } from '@element-plus/icons-vue'
import { projectApi, apiAutomationApi } from '@/api'
import ApiCaseEditor from '@/components/ApiCaseEditor.vue'

const route = useRoute()
const router = useRouter()
const projects = ref([])
const projectId = ref(null)
const activeTab = computed(() => route.meta.apiTab || 'suite')

const environments = ref([])
const suites = ref([])
const cases = ref([])
const runs = ref([])
const schedules = ref([])

const envLoading = ref(false)
const suiteLoading = ref(false)
const caseLoading = ref(false)
const reportLoading = ref(false)
const scheduleLoading = ref(false)
const running = ref(false)

const suiteId = ref(null)
const activeFolderId = ref(null)
const activeCaseId = ref(null)
const draggingCaseId = ref(null)
const caseDragOverId = ref(null)
const caseMoving = ref(false)
const selectedCaseIds = ref([])
const caseBatchDeleting = ref(false)
const caseEditorRef = ref(null)
const suiteTreeRef = ref(null)

const envDialogVisible = ref(false)
const folderDialogVisible = ref(false)
const suiteDialogVisible = ref(false)
const reportVisible = ref(false)
const importDialogVisible = ref(false)
const swaggerDialogVisible = ref(false)
const scheduleDialogVisible = ref(false)

const envEditing = ref(null)
const folderEditing = ref(null)
const suiteEditing = ref(null)
const scheduleEditing = ref(null)

const envSaving = ref(false)
const folderSaving = ref(false)
const suiteSaving = ref(false)
const reportDetailLoading = ref(false)
const importParsing = ref(false)
const importSaving = ref(false)
const swaggerParsing = ref(false)
const swaggerSaving = ref(false)
const scheduleSaving = ref(false)
const scheduleTogglingId = ref(null)
const scheduleRunningId = ref(null)

const importRawText = ref('')
const importCaseName = ref('')
const importAutoEnv = ref(true)
const importPreview = ref([])

const swaggerSourceType = ref('content')
const swaggerRawText = ref('')
const swaggerUrl = ref('')
const swaggerBaseUrl = ref('')
const swaggerAutoEnv = ref(true)
const swaggerPreview = ref([])

const canParseSwagger = computed(() => {
  if (!suiteId.value) return false
  if (swaggerSourceType.value === 'url') {
    return Boolean(swaggerUrl.value.trim())
  }
  return Boolean(swaggerRawText.value.trim())
})

const reportDetail = ref(null)
const expandedSteps = ref([])

const envFormRef = ref()
const folderFormRef = ref()
const suiteFormRef = ref()
const scheduleFormRef = ref()

const weekDays = [
  { label: '周一', value: 0 },
  { label: '周二', value: 1 },
  { label: '周三', value: 2 },
  { label: '周四', value: 3 },
  { label: '周五', value: 4 },
  { label: '周六', value: 5 },
  { label: '周日', value: 6 },
]
const statusLabel = { passed: '通过', failed: '失败', running: '执行中' }
const statusType = { passed: 'success', failed: 'danger', running: 'warning' }
const methodType = { GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }

const envForm = reactive({
  name: '',
  base_url: '',
  default_headers: '{"Content-Type":"application/json"}',
  description: '',
})

const suiteForm = reactive({
  name: '',
  environment_id: null,
  description: '',
  parent_id: null,
})

const folderForm = reactive({
  name: '',
  description: '',
  parent_id: null,
})

const suiteTreeProps = { children: 'children', label: 'name' }
const folderSelectProps = { children: 'children', label: 'label', value: 'value' }

const envRules = {
  name: [{ required: true, message: '请输入环境名称', trigger: 'blur' }],
  base_url: [{ required: true, message: '请输入 Base URL', trigger: 'blur' }],
}

const suiteRules = {
  name: [{ required: true, message: '请输入套件名称', trigger: 'blur' }],
  environment_id: [{ required: true, message: '请选择执行环境', trigger: 'change' }],
}

const folderRules = {
  name: [{ required: true, message: '请输入目录名称', trigger: 'blur' }],
}

const scheduleForm = reactive({
  name: '',
  suite_id: null,
  schedule_type: 'daily',
  run_time: '09:00',
  week_day: 0,
  interval_minutes: 60,
  enabled: true,
})

const scheduleRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  suite_id: [{ required: true, message: '请选择测试套件', trigger: 'change' }],
  schedule_type: [{ required: true, message: '请选择调度类型', trigger: 'change' }],
  run_time: [{ required: true, message: '请选择执行时间', trigger: 'change' }],
  week_day: [{ required: true, message: '请选择星期', trigger: 'change' }],
  interval_minutes: [{ required: true, message: '请输入间隔分钟', trigger: 'change' }],
}

const progressColor = computed(() => [
  { color: '#f56c6c', percentage: 60 },
  { color: '#e6a23c', percentage: 80 },
  { color: '#67c23a', percentage: 100 },
])

const currentSuite = computed(() => suites.value.find((s) => s.id === suiteId.value && !s.is_folder) || null)
const activeCase = computed(() => cases.value.find((c) => c.id === activeCaseId.value) || null)
const runnableSuites = computed(() => suites.value.filter((item) => !item.is_folder))
const isAllCasesSelected = computed(
  () => cases.value.length > 0 && selectedCaseIds.value.length === cases.value.length,
)
const isCaseSelectionIndeterminate = computed(
  () => selectedCaseIds.value.length > 0 && selectedCaseIds.value.length < cases.value.length,
)

function buildSuiteTree(items) {
  const map = new Map()
  items.forEach((item) => {
    map.set(item.id, { ...item, children: [] })
  })
  const roots = []
  map.forEach((node) => {
    if (node.parent_id && map.has(node.parent_id)) {
      map.get(node.parent_id).children.push(node)
    } else {
      roots.push(node)
    }
  })
  const sortNodes = (nodes) => {
    nodes.sort((a, b) => {
      if (a.is_folder !== b.is_folder) return a.is_folder ? -1 : 1
      if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order
      return a.id - b.id
    })
    nodes.forEach((node) => {
      if (node.children?.length) sortNodes(node.children)
    })
  }
  sortNodes(roots)
  return roots
}

const suiteTree = computed(() => buildSuiteTree(suites.value))

function collectDescendantIds(items, rootId) {
  const ids = new Set()
  const walk = (parentId) => {
    items.filter((item) => item.parent_id === parentId).forEach((child) => {
      ids.add(child.id)
      walk(child.id)
    })
  }
  walk(rootId)
  return ids
}

function buildFolderSelectOptions(items, excludeId = null) {
  const excluded = new Set()
  if (excludeId) {
    excluded.add(excludeId)
    collectDescendantIds(items, excludeId).forEach((id) => excluded.add(id))
  }
  const folders = items.filter((item) => item.is_folder && !excluded.has(item.id))
  const map = new Map()
  folders.forEach((item) => {
    map.set(item.id, { value: item.id, label: item.name, children: [] })
  })
  const roots = []
  folders.forEach((item) => {
    const node = map.get(item.id)
    if (item.parent_id && map.has(item.parent_id)) {
      map.get(item.parent_id).children.push(node)
    } else {
      roots.push(node)
    }
  })
  const sortNodes = (nodes) => {
    nodes.sort((a, b) => a.label.localeCompare(b.label, 'zh-CN'))
    nodes.forEach((node) => {
      if (node.children?.length) sortNodes(node.children)
    })
  }
  sortNodes(roots)
  return roots
}

const folderTreeOptions = computed(() =>
  buildFolderSelectOptions(suites.value, folderEditing.value?.id ?? null),
)

const suiteFolderTreeOptions = computed(() =>
  buildFolderSelectOptions(suites.value, null),
)

function suitePathLabel(item) {
  const names = []
  let current = item
  const byId = new Map(suites.value.map((row) => [row.id, row]))
  while (current) {
    names.unshift(current.name)
    current = current.parent_id ? byId.get(current.parent_id) : null
  }
  return names.join(' / ')
}

function suiteOptionLabel(item) {
  const path = suitePathLabel(item)
  return path === item.name ? item.name : path
}

function formatDuration(ms) {
  if (!ms && ms !== 0) return '-'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function formatTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function formatValue(value) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

async function loadProjects() {
  projects.value = await projectApi.list()
  if (projects.value.length && !projectId.value) {
    projectId.value = projects.value[0].id
    await reloadAll()
  }
}

async function reloadAll() {
  if (!projectId.value) return
  await Promise.all([loadEnvironments(), loadSuites(), loadRuns(), loadSchedules()])
}

function handleProjectChange() {
  suiteId.value = null
  activeFolderId.value = null
  activeCaseId.value = null
  cases.value = []
  reloadAll()
}

async function loadEnvironments() {
  if (!projectId.value) return
  envLoading.value = true
  try {
    environments.value = await apiAutomationApi.listEnvironments(projectId.value)
  } finally {
    envLoading.value = false
  }
}

async function loadSuites() {
  if (!projectId.value) return
  suiteLoading.value = true
  try {
    suites.value = await apiAutomationApi.listSuites(projectId.value)
    const selected = suites.value.find((item) => item.id === suiteId.value)
    if (suiteId.value && (!selected || selected.is_folder)) {
      suiteId.value = null
      activeCaseId.value = null
      cases.value = []
    }
    await nextTick()
    if (suiteId.value && suiteTreeRef.value) {
      suiteTreeRef.value.setCurrentKey(suiteId.value)
    }
  } finally {
    suiteLoading.value = false
  }
}

async function loadCases() {
  if (!suiteId.value) {
    cases.value = []
    selectedCaseIds.value = []
    return
  }
  caseLoading.value = true
  try {
    cases.value = await apiAutomationApi.listCases(suiteId.value)
    selectedCaseIds.value = selectedCaseIds.value.filter((id) => cases.value.some((item) => item.id === id))
  } finally {
    caseLoading.value = false
  }
}

function toggleSelectAllCases(checked) {
  selectedCaseIds.value = checked ? cases.value.map((item) => item.id) : []
}

function toggleCaseSelection(id, checked) {
  if (checked) {
    if (!selectedCaseIds.value.includes(id)) {
      selectedCaseIds.value = [...selectedCaseIds.value, id]
    }
    return
  }
  selectedCaseIds.value = selectedCaseIds.value.filter((item) => item !== id)
}

async function batchRemoveCases() {
  if (!selectedCaseIds.value.length) return
  await ElMessageBox.confirm(
    `确认删除选中的 ${selectedCaseIds.value.length} 条用例？此操作不可恢复。`,
    '批量删除',
    { type: 'warning' },
  )
  caseBatchDeleting.value = true
  try {
    const result = await apiAutomationApi.batchDeleteCases({ case_ids: selectedCaseIds.value })
    if (selectedCaseIds.value.includes(activeCaseId.value)) {
      activeCaseId.value = null
    }
    selectedCaseIds.value = []
    ElMessage.success(result.message || '删除成功')
    await loadCases()
    await loadSuites()
  } finally {
    caseBatchDeleting.value = false
  }
}

async function loadRuns() {
  if (!projectId.value) return
  reportLoading.value = true
  try {
    runs.value = await apiAutomationApi.listRuns({ project_id: projectId.value })
  } finally {
    reportLoading.value = false
  }
}

async function loadSchedules() {
  if (!projectId.value) return
  scheduleLoading.value = true
  try {
    schedules.value = await apiAutomationApi.listSchedules(projectId.value)
  } finally {
    scheduleLoading.value = false
  }
}

function openScheduleDialog(row = null) {
  scheduleEditing.value = row
  scheduleForm.name = row?.name || ''
  scheduleForm.suite_id = row?.suite_id || suiteId.value || suites.value[0]?.id || null
  scheduleForm.schedule_type = row?.schedule_type || 'daily'
  scheduleForm.run_time = row?.run_time || '09:00'
  scheduleForm.week_day = row?.week_day ?? 0
  scheduleForm.interval_minutes = row?.interval_minutes || 60
  scheduleForm.enabled = row?.enabled ?? true
  scheduleDialogVisible.value = true
}

async function saveSchedule() {
  const fields = ['name', 'suite_id', 'schedule_type']
  if (scheduleForm.schedule_type === 'weekly') fields.push('week_day')
  if (scheduleForm.schedule_type !== 'interval') fields.push('run_time')
  if (scheduleForm.schedule_type === 'interval') fields.push('interval_minutes')
  await scheduleFormRef.value.validateField(fields)
  scheduleSaving.value = true
  try {
    const payload = {
      name: scheduleForm.name,
      suite_id: scheduleForm.suite_id,
      schedule_type: scheduleForm.schedule_type,
      run_time: scheduleForm.run_time,
      enabled: scheduleForm.enabled,
    }
    if (scheduleForm.schedule_type === 'weekly') {
      payload.week_day = scheduleForm.week_day
    }
    if (scheduleForm.schedule_type === 'interval') {
      payload.interval_minutes = scheduleForm.interval_minutes
    }
    if (scheduleEditing.value) {
      const updated = await apiAutomationApi.updateSchedule(scheduleEditing.value.id, payload)
      ElMessage.success(`定时任务已更新，下次执行：${formatTime(updated.next_run_at)}`)
    } else {
      const created = await apiAutomationApi.createSchedule({ ...payload, project_id: projectId.value })
      ElMessage.success(`定时任务已创建，下次执行：${formatTime(created.next_run_at)}`)
    }
    scheduleDialogVisible.value = false
    await loadSchedules()
  } finally {
    scheduleSaving.value = false
  }
}

async function handleToggleSchedule(row, enabled) {
  scheduleTogglingId.value = row.id
  try {
    await apiAutomationApi.updateSchedule(row.id, { enabled })
    ElMessage.success(enabled ? '已启用定时任务' : '已暂停定时任务')
    await loadSchedules()
  } catch {
    row.enabled = !enabled
  } finally {
    scheduleTogglingId.value = null
  }
}

async function handleRunScheduleNow(row) {
  scheduleRunningId.value = row.id
  try {
    const result = await apiAutomationApi.runScheduleNow(row.id)
    ElMessage.success(result.message || '执行完成')
    await router.push('/api-automation/reports')
    await Promise.all([loadSchedules(), loadRuns(), loadSuites()])
    if (result.run_id) {
      await viewReport({ id: result.run_id })
    }
  } finally {
    scheduleRunningId.value = null
  }
}

async function removeSchedule(row) {
  await ElMessageBox.confirm(`确认删除定时任务「${row.name}」？`, '提示', { type: 'warning' })
  await apiAutomationApi.deleteSchedule(row.id)
  ElMessage.success('删除成功')
  await loadSchedules()
}

function handleCaseDragStart(event, item) {
  draggingCaseId.value = item.id
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('application/x-api-case-id', String(item.id))
  event.dataTransfer.setData('text/plain', String(item.id))
}

function handleCaseDragEnd() {
  draggingCaseId.value = null
  caseDragOverId.value = null
}

function handleCaseDragOver(data) {
  if (!draggingCaseId.value) return
  caseDragOverId.value = data.id
}

function handleCaseDragLeave(data) {
  if (caseDragOverId.value === data.id) {
    caseDragOverId.value = null
  }
}

function findFirstExecutableSuiteUnder(folderId) {
  const direct = suites.value
    .filter((item) => item.parent_id === folderId && !item.is_folder)
    .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
  if (direct.length) return direct[0].id

  const subFolders = suites.value
    .filter((item) => item.parent_id === folderId && item.is_folder)
    .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
  for (const folder of subFolders) {
    const nested = findFirstExecutableSuiteUnder(folder.id)
    if (nested) return nested
  }
  return null
}

async function resolveCaseDropTargetSuite(data) {
  if (!data.is_folder) return data.id

  const existing = findFirstExecutableSuiteUnder(data.id)
  if (existing) return existing

  const folder = suites.value.find((item) => item.id === data.id)
  const environmentId = currentSuite.value?.environment_id || environments.value[0]?.id
  if (!environmentId) {
    ElMessage.warning('请先配置执行环境后再移动用例')
    return null
  }

  const created = await apiAutomationApi.createSuite({
    project_id: projectId.value,
    name: `${folder?.name || '新'}套件`,
    parent_id: data.id,
    is_folder: false,
    environment_id: environmentId,
  })
  await loadSuites()
  return created.id
}

async function handleCaseDrop(data) {
  const caseId = draggingCaseId.value
  caseDragOverId.value = null
  draggingCaseId.value = null
  if (!caseId || caseMoving.value) return

  const caseItem = cases.value.find((item) => item.id === caseId)
  if (!caseItem) return

  caseMoving.value = true
  try {
    const targetSuiteId = await resolveCaseDropTargetSuite(data)
    if (!targetSuiteId || caseItem.suite_id === targetSuiteId) return

    await apiAutomationApi.copyCase(caseId, { suite_id: targetSuiteId })
    ElMessage.success('用例已复制到目标套件')
    await loadSuites()
  } catch {
    await loadSuites()
  } finally {
    caseMoving.value = false
  }
}

function handleCreateCommand(command) {
  if (command === 'folder') {
    openFolderDialog(null, activeFolderId.value)
    return
  }
  openSuiteDialog(null, activeFolderId.value)
}

function allowSuiteTreeDrag() {
  return true
}

function allowSuiteTreeDrop(draggingNode, dropNode, type) {
  const dragId = draggingNode.data.id
  const dropId = dropNode.data.id
  if (dragId === dropId) return false

  const descendantIds = collectDescendantIds(suites.value, dragId)
  if (descendantIds.has(dropId)) return false

  if (type === 'inner') {
    return dropNode.data.is_folder
  }
  return true
}

function resolveSuiteDropParentId(dropNode, dropType) {
  if (dropType === 'inner') {
    return dropNode.data.id
  }
  const parentNode = dropNode.parent
  if (!parentNode || parentNode.level === 0) {
    return null
  }
  return parentNode.data.id
}

async function handleSuiteTreeDrop(draggingNode, dropNode, dropType) {
  const dragData = draggingNode.data
  const nextParentId = resolveSuiteDropParentId(dropNode, dropType)
  if (dragData.parent_id === nextParentId || (dragData.parent_id == null && nextParentId == null)) {
    return
  }

  try {
    await apiAutomationApi.updateSuite(dragData.id, { parent_id: nextParentId })
    ElMessage.success('移动成功')
    await loadSuites()
  } catch {
    await loadSuites()
  }
}

function handleSuiteTreeClick(data) {
  if (data.is_folder) {
    activeFolderId.value = data.id
    return
  }
  selectSuite(data.id)
}

function handleSuiteTreeCommand(command, data) {
  if (command === 'add-folder') {
    openFolderDialog(null, data.id)
    return
  }
  if (command === 'add-suite') {
    openSuiteDialog(null, data.id)
    return
  }
  if (command === 'edit') {
    if (data.is_folder) {
      openFolderDialog(data)
    } else {
      openSuiteDialog(data)
    }
    return
  }
  if (command === 'copy') {
    copySuite(data)
    return
  }
  if (command === 'delete') {
    if (data.is_folder) {
      removeFolder(data)
    } else {
      removeSuite(data)
    }
  }
}

function selectSuite(id) {
  suiteId.value = id
  activeFolderId.value = suites.value.find((item) => item.id === id)?.parent_id ?? null
  activeCaseId.value = null
  nextTick(() => {
    suiteTreeRef.value?.setCurrentKey(id)
  })
  loadCases().then(() => {
    if (cases.value.length) {
      activeCaseId.value = cases.value[0].id
    }
  })
}

function selectCase(item) {
  activeCaseId.value = item.id
}

function onNewCase() {
  activeCaseId.value = null
}

async function onCaseSaved(savedId) {
  await loadEnvironments()
  await loadCases()
  await loadSuites()
  if (savedId) {
    activeCaseId.value = savedId
  } else if (cases.value.length && !activeCaseId.value) {
    activeCaseId.value = cases.value[cases.value.length - 1].id
  }
}

function openEnvDialog(row = null) {
  envEditing.value = row
  envForm.name = row?.name || ''
  envForm.base_url = row?.base_url || ''
  envForm.default_headers = row?.default_headers || '{"Content-Type":"application/json"}'
  envForm.description = row?.description || ''
  envDialogVisible.value = true
}

async function saveEnv() {
  await envFormRef.value.validate()
  envSaving.value = true
  try {
    if (envEditing.value) {
      await apiAutomationApi.updateEnvironment(envEditing.value.id, { ...envForm })
      ElMessage.success('环境已更新')
    } else {
      await apiAutomationApi.createEnvironment({ ...envForm, project_id: projectId.value })
      ElMessage.success('环境已创建')
    }
    envDialogVisible.value = false
    await loadEnvironments()
  } finally {
    envSaving.value = false
  }
}

async function removeEnv(row) {
  await ElMessageBox.confirm(`确认删除环境「${row.name}」？`, '提示', { type: 'warning' })
  await apiAutomationApi.deleteEnvironment(row.id)
  ElMessage.success('删除成功')
  await loadEnvironments()
}

function openFolderDialog(row = null, parentId = null) {
  folderEditing.value = row
  folderForm.name = row?.name || ''
  folderForm.description = row?.description || ''
  folderForm.parent_id = row ? row.parent_id : parentId ?? null
  folderDialogVisible.value = true
}

async function saveFolder() {
  await folderFormRef.value.validate()
  folderSaving.value = true
  try {
    const payload = {
      name: folderForm.name,
      description: folderForm.description,
      parent_id: folderForm.parent_id,
      is_folder: true,
    }
    if (folderEditing.value) {
      await apiAutomationApi.updateSuite(folderEditing.value.id, payload)
      ElMessage.success('目录已更新')
    } else {
      const created = await apiAutomationApi.createSuite({
        ...payload,
        project_id: projectId.value,
      })
      activeFolderId.value = created.id
      ElMessage.success('目录已创建')
    }
    folderDialogVisible.value = false
    await loadSuites()
  } finally {
    folderSaving.value = false
  }
}

async function removeFolder(row) {
  await ElMessageBox.confirm(`确认删除目录「${row.name}」？`, '提示', { type: 'warning' })
  await apiAutomationApi.deleteSuite(row.id)
  if (activeFolderId.value === row.id) {
    activeFolderId.value = null
  }
  ElMessage.success('删除成功')
  await loadSuites()
}

function openSuiteDialog(row = null, parentId = null) {
  suiteEditing.value = row
  suiteForm.name = row?.name || ''
  suiteForm.environment_id = row?.environment_id || environments.value[0]?.id || null
  suiteForm.description = row?.description || ''
  suiteForm.parent_id = row ? row.parent_id : parentId ?? null
  suiteDialogVisible.value = true
}

async function saveSuite() {
  await suiteFormRef.value.validate()
  suiteSaving.value = true
  try {
    if (suiteEditing.value) {
      await apiAutomationApi.updateSuite(suiteEditing.value.id, {
        ...suiteForm,
        is_folder: false,
      })
      ElMessage.success('套件已更新')
    } else {
      const created = await apiAutomationApi.createSuite({
        ...suiteForm,
        project_id: projectId.value,
        is_folder: false,
      })
      suiteId.value = created.id
      ElMessage.success('套件已创建')
    }
    suiteDialogVisible.value = false
    await loadSuites()
    await loadCases()
  } finally {
    suiteSaving.value = false
  }
}

async function removeSuite(row) {
  await ElMessageBox.confirm(`确认删除套件「${row.name}」？`, '提示', { type: 'warning' })
  await apiAutomationApi.deleteSuite(row.id)
  if (suiteId.value === row.id) {
    suiteId.value = null
    activeCaseId.value = null
    cases.value = []
  }
  ElMessage.success('删除成功')
  await loadSuites()
}

async function copySuite(row) {
  const label = row.is_folder ? '目录' : '套件'
  await ElMessageBox.confirm(`确认复制${label}「${row.name}」？`, '复制', { type: 'info' })
  const copied = await apiAutomationApi.copySuite(row.id)
  ElMessage.success('复制成功')
  await loadSuites()
  if (!copied.is_folder) {
    selectSuite(copied.id)
  }
}

async function removeCase(row) {
  await ElMessageBox.confirm(`确认删除用例「${row.name}」？`, '提示', { type: 'warning' })
  await apiAutomationApi.deleteCase(row.id)
  if (activeCaseId.value === row.id) {
    activeCaseId.value = null
  }
  ElMessage.success('删除成功')
  await loadCases()
  await loadSuites()
}

function openImportDialog() {
  importRawText.value = ''
  importCaseName.value = ''
  importAutoEnv.value = true
  importPreview.value = []
  importDialogVisible.value = true
}

async function handleParseCapture() {
  if (!suiteId.value || !importRawText.value.trim()) return
  importParsing.value = true
  try {
    const data = await apiAutomationApi.parseCapture({
      suite_id: suiteId.value,
      raw_text: importRawText.value,
      case_name: importCaseName.value || undefined,
      auto_environment: importAutoEnv.value,
    })
    importPreview.value = data.items || []
    if (!importPreview.value.length) {
      ElMessage.warning('未解析到可导入的接口')
    } else {
      ElMessage.success(data.message || '解析成功')
    }
  } finally {
    importParsing.value = false
  }
}

async function handleImportCapture() {
  if (!suiteId.value || !importRawText.value.trim()) return
  importSaving.value = true
  try {
    const data = await apiAutomationApi.importCapture({
      suite_id: suiteId.value,
      raw_text: importRawText.value,
      case_name: importCaseName.value || undefined,
      auto_environment: importAutoEnv.value,
    })
    ElMessage.success(data.message || '导入成功')
    importDialogVisible.value = false
    await Promise.all([loadEnvironments(), loadCases(), loadSuites()])
    if (data.case_ids?.length) {
      activeCaseId.value = data.case_ids[data.case_ids.length - 1]
    }
    if (data.environment_id) {
      const suite = suites.value.find((item) => item.id === suiteId.value)
      if (suite) suite.environment_id = data.environment_id
    }
  } finally {
    importSaving.value = false
  }
}

function openSwaggerDialog() {
  swaggerSourceType.value = 'content'
  swaggerRawText.value = ''
  swaggerUrl.value = ''
  swaggerBaseUrl.value = ''
  swaggerAutoEnv.value = true
  swaggerPreview.value = []
  swaggerDialogVisible.value = true
}

function buildSwaggerPayload(preview) {
  return {
    suite_id: suiteId.value,
    source_type: swaggerSourceType.value,
    raw_text: swaggerSourceType.value === 'content' ? swaggerRawText.value : undefined,
    swagger_url: swaggerSourceType.value === 'url' ? swaggerUrl.value : undefined,
    base_url: swaggerBaseUrl.value || undefined,
    auto_environment: swaggerAutoEnv.value,
    preview,
  }
}

async function handleParseSwagger() {
  if (!canParseSwagger.value) return
  swaggerParsing.value = true
  try {
    const data = await apiAutomationApi.parseSwagger(buildSwaggerPayload(true))
    swaggerPreview.value = data.items || []
    if (!swaggerPreview.value.length) {
      ElMessage.warning('未解析到可导入的接口')
    } else {
      ElMessage.success(data.message || '解析成功')
    }
  } finally {
    swaggerParsing.value = false
  }
}

async function handleImportSwagger() {
  if (!canParseSwagger.value || !swaggerPreview.value.length) return
  swaggerSaving.value = true
  try {
    const data = await apiAutomationApi.importSwagger(buildSwaggerPayload(false))
    ElMessage.success(data.message || '导入成功')
    swaggerDialogVisible.value = false
    await Promise.all([loadEnvironments(), loadCases(), loadSuites()])
    if (data.case_ids?.length) {
      activeCaseId.value = data.case_ids[data.case_ids.length - 1]
    }
    if (data.environment_id) {
      const suite = suites.value.find((item) => item.id === suiteId.value)
      if (suite) suite.environment_id = data.environment_id
    }
  } finally {
    swaggerSaving.value = false
  }
}

async function handleRunSuite() {
  running.value = true
  try {
    const result = await apiAutomationApi.runSuite(suiteId.value)
    ElMessage.success(result.message || '执行完成')
    await router.push('/api-automation/reports')
    await Promise.all([loadSuites(), loadRuns()])
    await viewReport({ id: result.run_id })
  } finally {
    running.value = false
  }
}

async function viewReport(row) {
  reportVisible.value = true
  reportDetailLoading.value = true
  try {
    reportDetail.value = await apiAutomationApi.getRun(row.id)
    expandedSteps.value = reportDetail.value.step_results
      .filter((item) => item.status === 'failed')
      .map((item) => item.id)
    if (!expandedSteps.value.length && reportDetail.value.step_results.length) {
      expandedSteps.value = [reportDetail.value.step_results[0].id]
    }
  } finally {
    reportDetailLoading.value = false
  }
}

async function removeRun(row) {
  await ElMessageBox.confirm(`确认删除报告 #${row.id}？`, '提示', { type: 'warning' })
  await apiAutomationApi.deleteRun(row.id)
  ElMessage.success('删除成功')
  await loadRuns()
}

onMounted(loadProjects)

let schedulePollTimer = null
watch(
  activeTab,
  (tab) => {
    if (schedulePollTimer) {
      clearInterval(schedulePollTimer)
      schedulePollTimer = null
    }
    if (tab === 'schedule' && projectId.value) {
      loadSchedules()
      schedulePollTimer = setInterval(() => {
        if (activeTab.value === 'schedule' && projectId.value) {
          loadSchedules()
        }
      }, 20000)
    } else if (tab === 'report' && projectId.value) {
      loadRuns()
    } else if (tab === 'env' && projectId.value) {
      loadEnvironments()
    } else if (tab === 'suite' && projectId.value) {
      Promise.all([loadEnvironments(), loadSuites()])
    }
  },
  { immediate: true }
)
onUnmounted(() => {
  if (schedulePollTimer) clearInterval(schedulePollTimer)
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.main-content {
  background: #fff;
  padding: 16px;
  border-radius: 8px;
}

.pane-toolbar,
.card-header,
.header-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.suite-card {
  min-height: 520px;
}

.suite-card :deep(.el-card__header) {
  padding: 10px 12px;
}

.suite-card :deep(.el-card__body) {
  padding: 8px;
}

.suite-tree-wrap {
  min-height: 120px;
  max-height: calc(100vh - 220px);
  overflow: auto;
}

.suite-tree-wrap :deep(.el-tree-node__content) {
  height: auto;
  min-height: 34px;
  padding: 4px 0;
  cursor: grab;
}

.suite-tree-wrap :deep(.el-tree-node__content:active) {
  cursor: grabbing;
}

.suite-tree-node {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  min-width: 0;
  padding: 2px 4px 2px 0;
  border-radius: 4px;
}

.suite-tree-node.active {
  background: #ebf8ff;
}

.suite-tree-node.folder {
  font-weight: 600;
}

.suite-tree-icon {
  flex-shrink: 0;
  color: #909399;
}

.suite-tree-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.suite-tree-tag {
  flex-shrink: 0;
  transform: scale(0.88);
  transform-origin: center;
}

.suite-tree-actions {
  flex-shrink: 0;
  margin-left: auto;
}

.suite-tree-actions :deep(.el-button) {
  padding: 0 4px;
  font-size: 12px;
}

.form-tip {
  margin-top: 6px;
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
}

.inline-tip {
  margin-top: 0;
  margin-left: 10px;
}

.import-tip {
  margin-bottom: 16px;
}

.schedule-tip {
  margin-bottom: 16px;
}

.import-form {
  margin-top: 8px;
}

.swagger-source-group {
  display: flex;
  gap: 16px;
  width: 100%;
}

.swagger-source-card {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  background: #fff;
}

.swagger-source-card.active {
  border-color: #f97316;
  box-shadow: 0 0 0 1px rgba(249, 115, 22, 0.15);
}

.source-card-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.source-card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #22c55e;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}

.source-card-label {
  font-size: 15px;
  color: #303133;
}

.source-card-radio {
  width: 16px;
  height: 16px;
  border: 2px solid #dcdfe6;
  border-radius: 50%;
  flex-shrink: 0;
}

.source-card-radio.checked {
  border-color: #f97316;
  background: radial-gradient(circle at center, #f97316 0 5px, transparent 6px);
}

.case-workspace-card :deep(.el-card__body) {
  padding: 0;
}

.case-workspace {
  display: flex;
  min-height: 560px;
}

.case-list-panel {
  width: 180px;
  flex-shrink: 0;
  border-right: 1px solid #ebeef5;
  background: #fafafa;
}

.panel-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #ebeef5;
}

.panel-title-row .panel-title {
  flex: 1;
  padding: 0;
  border-bottom: none;
}

.panel-title {
  padding: 12px 14px;
  font-weight: 600;
  color: #1a365d;
  border-bottom: 1px solid #ebeef5;
}

.case-mini-list {
  max-height: 520px;
  overflow-y: auto;
  padding: 8px;
}

.suite-tree-node.case-drop-target {
  background: #e6fffa;
  outline: 1px dashed #38b2ac;
}

.case-mini-item {
  padding: 10px;
  margin-bottom: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  cursor: grab;
  transition: all 0.15s;
}

.case-mini-item.dragging {
  opacity: 0.55;
  border-style: dashed;
  border-color: #38b2ac;
}

.case-mini-item:active {
  cursor: grabbing;
}

.case-mini-item:hover,
.case-mini-item.active {
  border-color: #3182ce;
  background: #ebf8ff;
}

.case-mini-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 6px;
}

.case-mini-top :deep(.el-checkbox) {
  flex-shrink: 0;
  height: auto;
  margin-right: 0;
}

.case-mini-name {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-mini-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.case-mini-path {
  font-size: 11px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-editor-panel {
  flex: 1;
  min-width: 0;
  padding: 12px;
}

.import-preview {
  margin-top: 16px;
}

.preview-title {
  font-weight: 600;
  color: #1a365d;
  margin-bottom: 10px;
}

.report-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.summary-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}

.summary-label {
  color: #718096;
  font-size: 13px;
  margin-bottom: 10px;
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  color: #1a365d;
}

.step-title {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.step-method {
  font-weight: 600;
  color: #3182ce;
}

.step-name {
  flex: 1;
}

.step-duration {
  color: #718096;
  font-size: 12px;
}

.detail-block {
  margin-bottom: 14px;
}

.detail-label {
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 6px;
}

.detail-url {
  word-break: break-all;
  color: #2d3748;
}

.code-block {
  background: #1a202c;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  overflow: auto;
  max-height: 220px;
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.text-success {
  color: #38a169;
}

.text-danger {
  color: #e53e3e;
}

.text-muted {
  color: #909399;
  font-size: 12px;
}

@media (max-width: 1200px) {
  .report-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
