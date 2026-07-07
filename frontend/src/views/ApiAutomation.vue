<template>
  <div class="api-automation">
    <div class="toolbar">
      <el-select v-model="projectId" placeholder="选择项目" style="width: 260px" @change="handleProjectChange">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-button type="primary" :disabled="!projectId" @click="reloadAll">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
      <div v-if="activeTab === 'report'" class="report-search-bar">
        <el-date-picker
          v-model="reportDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 260px"
          clearable
        />
        <el-input
          v-model="reportExecutorFilter"
          placeholder="执行人"
          clearable
          style="width: 140px"
          @keyup.enter="searchReports"
        />
        <el-select
          v-model="reportTriggerFilter"
          placeholder="触发方式"
          clearable
          style="width: 120px"
        >
          <el-option label="手动" value="manual" />
          <el-option label="定时" value="schedule" />
        </el-select>
        <el-button type="primary" :disabled="!projectId" @click="searchReports">查询</el-button>
        <el-button :disabled="!projectId" @click="resetReportSearch">重置</el-button>
      </div>
    </div>

    <div class="main-content">
      <div v-if="activeTab === 'env'">
        <el-card shadow="never">
          <div class="pane-toolbar">
            <el-button type="primary" :disabled="!projectId" @click="openEnvDialog()">
              <el-icon><Plus /></el-icon> 新建环境
            </el-button>
            <el-button :disabled="!projectId" @click="openGlobalVarDialog()">全局变量</el-button>
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
        <button
          type="button"
          class="assistant-hidden-trigger"
          data-assistant="suites.open_create_suite_dialog"
          tabindex="-1"
          aria-hidden="true"
          @click="openSuiteDialog()"
        />
        <el-row :gutter="16">
          <el-col :span="4">
            <el-card shadow="never" class="suite-card">
              <template #header>
                <div class="card-header">
                  <span>测试套件</span>
                  <el-dropdown trigger="click" :disabled="!projectId" @command="handleCreateCommand">
                    <el-button type="primary" link :disabled="!projectId" data-assistant="suites.create_btn">
                      新建<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="folder">新建目录</el-dropdown-item>
                        <el-dropdown-item command="suite" data-assistant="suites.create_suite_menu">新建套件</el-dropdown-item>
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
                    <el-button :disabled="!suiteId" data-assistant="suites.swagger_import_btn" @click="openSwaggerDialog()">
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
                    :global-variables="globalVariablesMap"
                    :suite-environment-id="currentSuite?.environment_id"
                    :case-count="cases.length"
                    :selected-case-ids="selectedCaseIds"
                    :batch-generating="caseBatchGenerating"
                    @saved="onCaseSaved"
                    @new="onNewCase"
                    @import="openImportDialog()"
                    @batch-generate-data="batchGenerateCaseData"
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
          <div class="pane-toolbar">
            <el-dropdown
              :disabled="!selectedRunIds.length"
              @command="batchExportRuns"
            >
              <el-button
                type="primary"
                plain
                :disabled="!selectedRunIds.length"
                :loading="runBatchExporting"
              >
                批量导出{{ selectedRunIds.length ? `(${selectedRunIds.length})` : '' }}
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
                  <el-dropdown-item command="word">导出 Word</el-dropdown-item>
                  <el-dropdown-item command="pdf">导出 PDF</el-dropdown-item>
                  <el-dropdown-item command="json">导出 JSON</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button
              type="danger"
              plain
              :disabled="!selectedRunIds.length"
              :loading="runBatchDeleting"
              @click="batchRemoveRuns"
            >
              批量删除{{ selectedRunIds.length ? `(${selectedRunIds.length})` : '' }}
            </el-button>
          </div>
          <el-table
            ref="reportTableRef"
            v-loading="reportLoading"
            :data="runs"
            stripe
            @row-click="viewReport"
            @selection-change="onRunSelectionChange"
          >
            <el-table-column type="selection" width="48" />
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
            <el-table-column label="触发方式" width="100">
              <template #default="{ row }">{{ reportTriggerType(row.triggered_by) }}</template>
            </el-table-column>
            <el-table-column label="执行人" width="100">
              <template #default="{ row }">{{ reportExecutorName(row.triggered_by) }}</template>
            </el-table-column>
            <el-table-column label="耗时" width="100">
              <template #default="{ row }">{{ formatDuration(row.duration_ms) }}</template>
            </el-table-column>
            <el-table-column label="报告时间" min-width="170">
              <template #default="{ row }">{{ formatReportTime(row.started_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right" align="center">
              <template #default="{ row }">
                <div class="report-row-actions">
                  <el-button link type="primary" @click.stop="viewReport(row)">查看报告</el-button>
                  <el-dropdown trigger="click" @command="(format) => exportRun(row, format)">
                    <el-button
                      link
                      type="success"
                      :loading="runExportingId === row.id"
                      @click.stop
                    >
                      导出
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="excel">Excel</el-dropdown-item>
                        <el-dropdown-item command="word">Word</el-dropdown-item>
                        <el-dropdown-item command="pdf">PDF</el-dropdown-item>
                        <el-dropdown-item command="json">JSON</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                  <el-button link type="danger" @click.stop="removeRun(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="reportCurrentPage"
              v-model:page-size="reportPageSize"
              :total="reportTotal"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              background
              @current-change="loadRuns"
              @size-change="handleReportPageSizeChange"
            />
          </div>
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
            <el-table-column prop="suite_name" label="测试套件" min-width="180" show-overflow-tooltip />
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
            <el-table-column label="操作" width="300" fixed="right">
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  :disabled="!(row.last_run_ids?.length || row.last_run_id)"
                  @click="viewScheduleLastReport(row)"
                >
                  查看报告
                </el-button>
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
    <el-dialog v-model="envDialogVisible" :title="envEditing ? '编辑环境' : '新建环境'" width="720px">
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
        <el-form-item label="环境变量">
          <div class="env-variables-panel">
            <div class="form-tip">在当前环境下可用，可用 <code v-pre>{{变量名}}</code> 引用；接口提取为「环境变量」时会自动写入此处</div>
            <ApiKvParamTable v-model:rows="envVariableRows" key-label="变量名" value-label="变量值" />
          </div>
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

    <!-- 全局变量对话框 -->
    <el-dialog v-model="globalVarDialogVisible" title="全局变量" width="720px">
      <div class="form-tip global-var-tip">
        跨所有环境永久有效，除非手动删除。适合存放与环境无关的固定配置。
      </div>
      <ApiKvParamTable v-model:rows="globalVariableRows" key-label="变量名" value-label="变量值" />
      <template #footer>
        <el-button @click="globalVarDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="globalVarSaving" @click="saveGlobalVariables">保存</el-button>
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
          <el-input v-model="suiteForm.name" data-assistant="suites.form.name" />
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
          <el-select
            v-model="suiteForm.environment_id"
            data-assistant="suites.form.environment"
            style="width: 100%"
            placeholder="选择环境"
          >
            <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="suiteForm.description" data-assistant="suites.form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="suiteDialogVisible = false">取消</el-button>
        <el-button type="primary" data-assistant="suites.form.submit" :loading="suiteSaving" @click="saveSuite">保存</el-button>
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
    <el-dialog v-model="swaggerDialogVisible" title="导入 Swagger 文档" width="920px">
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
              data-assistant="suites.swagger_source_url"
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
        <el-form-item v-if="swaggerSourceType === 'content'" label="文档内容" required>
          <el-input
            v-model="swaggerRawText"
            type="textarea"
            :rows="12"
            placeholder="粘贴 Swagger / OpenAPI JSON 或 YAML..."
          />
        </el-form-item>
        <el-form-item v-else label="文档 URL" required>
          <el-input
            v-model="swaggerUrl"
            data-assistant="suites.swagger_url_input"
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
          <el-table-column prop="input_params" label="入参" min-width="260" show-overflow-tooltip />
          <el-table-column prop="base_url" label="Base URL" min-width="180" show-overflow-tooltip />
        </el-table>
      </div>

      <template #footer>
        <el-button @click="swaggerDialogVisible = false">取消</el-button>
        <el-button
          data-assistant="suites.swagger_parse_btn"
          :disabled="!canParseSwagger"
          :loading="swaggerParsing"
          @click="handleParseSwagger"
        >
          解析预览
        </el-button>
        <el-button
          :disabled="!swaggerPreview.length"
          :loading="swaggerAiGenerating"
          @click="handleSwaggerAiGenerate"
        >
          <el-icon><MagicStick /></el-icon> AI 造数
        </el-button>
        <el-button
          type="primary"
          data-assistant="suites.swagger_confirm_btn"
          :disabled="!swaggerPreview.length"
          :loading="swaggerSaving"
          @click="handleImportSwagger"
        >
          确认导入
        </el-button>
      </template>
    </el-dialog>

    <!-- Swagger AI 造数日志 -->
    <el-dialog
      v-model="swaggerAiLogVisible"
      title="Swagger AI 造数日志"
      width="680px"
      :close-on-click-modal="!swaggerAiGenerating"
      :show-close="!swaggerAiGenerating"
    >
      <div class="ai-generate-progress-block">
        <div class="ai-generate-progress-head">
          <span>{{ swaggerAiStatusText }}</span>
          <span>{{ swaggerAiProgress }}%</span>
        </div>
        <el-progress
          :percentage="swaggerAiProgress"
          :status="swaggerAiProgress >= 100 && !swaggerAiGenerating ? 'success' : undefined"
          :striped="swaggerAiGenerating"
          :striped-flow="swaggerAiGenerating"
        />
      </div>
      <div ref="swaggerAiLogRef" class="ai-generate-log-panel">
        <div
          v-for="(line, index) in swaggerAiLogs"
          :key="index"
          class="ai-generate-log-line"
          :class="`log-${line.type}`"
        >
          <span class="log-time">{{ line.time }}</span>
          <span class="log-text">{{ line.text }}</span>
        </div>
        <el-empty v-if="!swaggerAiLogs.length" description="等待开始..." :image-size="48" />
      </div>
      <template #footer>
        <el-button :disabled="swaggerAiGenerating" @click="swaggerAiLogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- AI 生成数据日志 -->
    <el-dialog
      v-model="aiGenerateLogVisible"
      title="AI 生成数据日志"
      width="680px"
      :close-on-click-modal="!caseBatchGenerating"
      :show-close="!caseBatchGenerating"
    >
      <div class="ai-generate-progress-block">
        <div class="ai-generate-progress-head">
          <span>{{ aiGenerateStatusText }}</span>
          <span>{{ aiGenerateProgress }}%</span>
        </div>
        <el-progress
          :percentage="aiGenerateProgress"
          :status="aiGenerateProgress >= 100 && !caseBatchGenerating ? 'success' : undefined"
          :striped="caseBatchGenerating"
          :striped-flow="caseBatchGenerating"
        />
      </div>
      <div ref="aiGenerateLogRef" class="ai-generate-log-panel">
        <div
          v-for="(line, index) in aiGenerateLogs"
          :key="index"
          class="ai-generate-log-line"
          :class="`log-${line.type}`"
        >
          <span class="log-time">{{ line.time }}</span>
          <span class="log-text">{{ line.text }}</span>
        </div>
        <el-empty v-if="!aiGenerateLogs.length" description="等待开始..." :image-size="48" />
      </div>
      <template #footer>
        <el-button :disabled="caseBatchGenerating" @click="aiGenerateLogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 套件执行日志 -->
    <el-dialog
      v-model="suiteRunLogVisible"
      title="套件执行日志"
      width="720px"
      :close-on-click-modal="!running"
      :show-close="!running"
    >
      <div class="ai-generate-progress-block">
        <div class="ai-generate-progress-head">
          <span>{{ suiteRunStatusText }}</span>
          <span>{{ suiteRunProgress }}%</span>
        </div>
        <el-progress
          :percentage="suiteRunProgress"
          :status="suiteRunProgress >= 100 && !running ? (suiteRunFailedCount > 0 ? 'exception' : 'success') : undefined"
          :striped="running"
          :striped-flow="running"
        />
      </div>
      <div ref="suiteRunLogRef" class="ai-generate-log-panel">
        <div
          v-for="(line, index) in suiteRunLogs"
          :key="index"
          class="ai-generate-log-line"
          :class="`log-${line.type}`"
        >
          <span class="log-time">{{ line.time }}</span>
          <span class="log-text">{{ line.text }}</span>
        </div>
        <el-empty v-if="!suiteRunLogs.length" description="等待开始..." :image-size="48" />
      </div>
      <template #footer>
        <el-button :disabled="running" @click="suiteRunLogVisible = false">关闭</el-button>
        <el-button
          v-if="suiteRunResultId"
          type="primary"
          :disabled="running"
          @click="openSuiteRunReport"
        >
          查看报告
        </el-button>
      </template>
    </el-dialog>

    <!-- 定时任务对话框 -->
    <el-dialog v-model="scheduleDialogVisible" :title="scheduleEditing ? '编辑定时任务' : '新建定时任务'" width="560px">
      <el-form ref="scheduleFormRef" :model="scheduleForm" :rules="scheduleRules" label-width="100px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="scheduleForm.name" placeholder="例如：每日回归" />
        </el-form-item>
        <el-form-item label="测试套件" prop="suite_ids">
          <el-select
            v-model="scheduleForm.suite_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            style="width: 100%"
            placeholder="选择套件（可多选）"
          >
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
    <el-drawer v-model="reportVisible" size="75%" class="report-drawer">
      <template #header>
        <div v-if="reportDetail" class="report-drawer-header">
          <div class="report-drawer-main">
            <div class="report-drawer-title-row">
              <div class="report-drawer-title">测试报告</div>
              <span v-if="reportDetail.suite_name" class="report-drawer-suite">{{ reportDetail.suite_name }}</span>
              <span v-if="reportSuiteSections.length > 1" class="report-drawer-suite-count">
                共 {{ reportSuiteSections.length }} 个套件
              </span>
            </div>
            <div class="report-drawer-meta">
              <div class="report-meta-item">
                <span class="report-meta-label">开始执行</span>
                <span class="report-meta-value">{{ formatReportTime(reportDetail.started_at) }}</span>
              </div>
              <div class="report-meta-divider" />
              <div class="report-meta-item">
                <span class="report-meta-label">结束执行</span>
                <span class="report-meta-value">{{ formatReportTime(reportDetail.finished_at) }}</span>
              </div>
            </div>
          </div>
        </div>
        <span v-else>测试报告</span>
      </template>
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
            <div class="summary-value report-count-value">
              <button
                type="button"
                class="report-count-btn text-success"
                :class="{ active: reportStepFilter === 'passed' }"
                @click="setReportStepFilter('passed')"
              >
                {{ reportDetail.passed_count }}
              </button>
              /
              <button
                type="button"
                class="report-count-btn text-danger"
                :class="{ active: reportStepFilter === 'failed' }"
                @click="setReportStepFilter('failed')"
              >
                {{ reportDetail.failed_count }}
              </button>
              /
              <button
                type="button"
                class="report-count-btn"
                :class="{ active: reportStepFilter === 'all' }"
                @click="setReportStepFilter('all')"
              >
                {{ reportDetail.total_count }}
              </button>
            </div>
          </div>
          <div class="summary-card">
            <div class="summary-label">总耗时</div>
            <div class="summary-value">{{ formatDuration(reportDetail.duration_ms) }}</div>
          </div>
        </div>

        <el-divider content-position="left">
          用例执行明细
          <span v-if="reportStepFilter !== 'all'" class="report-filter-tip">
            （{{ reportStepFilter === 'passed' ? '仅通过' : '仅失败' }}，共 {{ filteredReportSteps.length }} 条）
          </span>
        </el-divider>

        <el-empty
          v-if="!displayReportSections.length || !filteredReportSteps.length"
          :description="reportStepFilter === 'passed' ? '暂无通过用例' : reportStepFilter === 'failed' ? '暂无失败用例' : '暂无用例'"
          :image-size="64"
        />

        <div v-else class="report-section-list">
          <div
            v-for="section in displayReportSections"
            :key="section.run_id"
            class="report-suite-section"
          >
            <el-divider content-position="left">
              <span class="report-suite-title">{{ section.suite_name || '未命名套件' }}</span>
              <span class="report-suite-meta">
                {{ section.passed_count }}/{{ section.failed_count }}/{{ section.total_count }}
                · {{ formatDuration(section.duration_ms) }}
              </span>
            </el-divider>

            <el-empty
              v-if="!section.step_results.length"
              :description="reportStepFilter === 'passed' ? '该套件暂无通过用例' : '该套件暂无失败用例'"
              :image-size="48"
            />

            <el-collapse v-else v-model="expandedSteps" class="report-steps">
              <el-collapse-item
                v-for="(step, index) in section.step_results"
                :key="step.id"
                :name="step.id"
              >
                <template #title>
                  <div class="step-title">
                    <span class="step-index">{{ index + 1 }}</span>
                    <el-tag :type="statusType[step.status]" size="small" effect="light">
                      {{ statusLabel[step.status] || step.status }}
                    </el-tag>
                    <span :class="['step-method', `step-method-${(step.method || '').toLowerCase()}`]">
                      {{ step.method }}
                    </span>
                    <span class="step-name">{{ step.case_name }}</span>
                    <span v-if="step.response_status != null" :class="['step-status-code', stepStatusClass(step.response_status)]">
                      {{ step.response_status }}
                    </span>
                    <span class="step-duration">{{ formatDuration(step.duration_ms) }}</span>
                  </div>
                </template>

                <ApiReportStepDetail :step="step" />
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Document, Folder, MagicStick } from '@element-plus/icons-vue'
import { projectApi, apiAutomationApi } from '@/api'
import ApiCaseEditor from '@/components/ApiCaseEditor.vue'
import ApiKvParamTable from '@/components/ApiKvParamTable.vue'
import ApiReportStepDetail from '@/components/ApiReportStepDetail.vue'
import { emptyKvRow } from '@/utils/apiCaseConfig'
import { registerAssistantHandler, unregisterAssistantHandler } from '@/utils/assistantActionRegistry'

const ASSISTANT_HANDLER_NAMES = [
  'apiAutomation.ensureProject',
  'apiAutomation.ensureEnvironment',
  'apiAutomation.createSuite',
  'apiAutomation.selectFirstSuite',
  'apiAutomation.openSwaggerImport',
  'apiAutomation.setSwaggerUrl',
  'apiAutomation.parseSwagger',
  'apiAutomation.confirmSwaggerImport',
]

const route = useRoute()
const router = useRouter()
const projects = ref([])
const projectId = ref(null)
const activeTab = computed(() => route.meta.apiTab || 'suite')

const environments = ref([])
const globalVariablesMap = ref({})
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
const selectedRunIds = ref([])
const caseBatchDeleting = ref(false)
const runBatchDeleting = ref(false)
const runBatchExporting = ref(false)
const runExportingId = ref(null)
const caseBatchGenerating = ref(false)
const aiGenerateLogVisible = ref(false)
const aiGenerateLogs = ref([])
const aiGenerateLogRef = ref(null)
const aiGenerateProgress = ref(0)
const aiGenerateStatusText = ref('等待开始')
const suiteRunLogVisible = ref(false)
const suiteRunLogs = ref([])
const suiteRunLogRef = ref(null)
const suiteRunProgress = ref(0)
const suiteRunStatusText = ref('等待开始')
const suiteRunResultId = ref(null)
const suiteRunFailedCount = ref(0)
const AI_GENERATE_CHUNK_SIZE = 8
const caseEditorRef = ref(null)
const reportTableRef = ref(null)
const reportCurrentPage = ref(1)
const reportPageSize = ref(10)
const reportTotal = ref(0)
const reportDateRange = ref(null)
const reportExecutorFilter = ref('')
const reportTriggerFilter = ref('')
const suiteTreeRef = ref(null)

const envDialogVisible = ref(false)
const globalVarDialogVisible = ref(false)
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
const globalVarSaving = ref(false)
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
const swaggerAiGenerating = ref(false)
const swaggerAiLogVisible = ref(false)
const swaggerAiLogs = ref([])
const swaggerAiLogRef = ref(null)
const swaggerAiProgress = ref(0)
const swaggerAiStatusText = ref('等待开始')
const SWAGGER_AI_CHUNK_SIZE = 8

const canParseSwagger = computed(() => {
  if (!suiteId.value) return false
  if (swaggerSourceType.value === 'url') {
    return Boolean(swaggerUrl.value.trim())
  }
  return Boolean(swaggerRawText.value.trim())
})

const reportDetail = ref(null)
const expandedSteps = ref([])
const reportStepFilter = ref('all')

function filterReportSteps(steps = []) {
  if (reportStepFilter.value === 'passed') {
    return steps.filter((step) => step.status === 'passed')
  }
  if (reportStepFilter.value === 'failed') {
    return steps.filter((step) => step.status === 'failed')
  }
  return steps
}

const reportSuiteSections = computed(() => {
  if (!reportDetail.value) return []
  if (reportDetail.value.suite_sections?.length) {
    return reportDetail.value.suite_sections
  }
  return [{
    run_id: reportDetail.value.id,
    suite_id: reportDetail.value.suite_id,
    suite_name: reportDetail.value.suite_name,
    status: reportDetail.value.status,
    total_count: reportDetail.value.total_count,
    passed_count: reportDetail.value.passed_count,
    failed_count: reportDetail.value.failed_count,
    duration_ms: reportDetail.value.duration_ms,
    pass_rate: reportDetail.value.pass_rate,
    step_results: reportDetail.value.step_results || [],
  }]
})

const displayReportSections = computed(() =>
  reportSuiteSections.value
    .map((section) => ({
      ...section,
      step_results: filterReportSteps(section.step_results || []),
    }))
    .filter((section) => section.step_results.length || reportStepFilter.value === 'all'),
)

const filteredReportSteps = computed(() =>
  displayReportSections.value.flatMap((section) => section.step_results),
)

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

const envVariableRows = ref([emptyKvRow()])
const globalVariableRows = ref([emptyKvRow()])

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
  suite_ids: [],
  schedule_type: 'daily',
  run_time: '09:00',
  week_day: 0,
  interval_minutes: 60,
  enabled: true,
})

const scheduleRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  suite_ids: [{
    validator: (_rule, value, callback) => {
      if (!value?.length) callback(new Error('请至少选择一个测试套件'))
      else callback()
    },
    trigger: 'change',
  }],
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

function formatReportTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  const pad = (num) => String(num).padStart(2, '0')
  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function reportTimeFileToken(value) {
  if (!value) return 'unknown'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'unknown'
  const pad = (num) => String(num).padStart(2, '0')
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
}

function reportTriggerType(triggeredBy) {
  if (triggeredBy && String(triggeredBy).startsWith('schedule:')) return '定时'
  return '手动'
}

function reportExecutorName(triggeredBy) {
  if (!triggeredBy) return '-'
  const value = String(triggeredBy)
  if (value.startsWith('schedule:')) return '系统'
  if (value === 'manual') return '-'
  return value
}

function stepStatusClass(statusCode) {
  const code = Number(statusCode)
  if (code >= 200 && code < 300) return 'is-success'
  if (code >= 400 && code < 500) return 'is-warning'
  if (code >= 500) return 'is-danger'
  return 'is-muted'
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
  await Promise.all([loadEnvironments(), loadGlobalVariables(), loadSuites(), loadRuns(), loadSchedules()])
}

function handleProjectChange() {
  suiteId.value = null
  activeFolderId.value = null
  activeCaseId.value = null
  cases.value = []
  reportCurrentPage.value = 1
  resetReportSearch(false)
  reloadAll()
}

function buildReportQueryParams() {
  const params = {
    project_id: projectId.value,
    page: reportCurrentPage.value,
    page_size: reportPageSize.value,
  }
  if (reportDateRange.value?.length === 2) {
    params.started_from = `${reportDateRange.value[0]}T00:00:00`
    params.started_to = `${reportDateRange.value[1]}T23:59:59`
  }
  const executor = reportExecutorFilter.value.trim()
  if (executor) params.executor = executor
  if (reportTriggerFilter.value) params.trigger_type = reportTriggerFilter.value
  return params
}

function searchReports() {
  reportCurrentPage.value = 1
  loadRuns()
}

function resetReportSearch(reload = true) {
  reportDateRange.value = null
  reportExecutorFilter.value = ''
  reportTriggerFilter.value = ''
  reportCurrentPage.value = 1
  if (reload) loadRuns()
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

async function loadGlobalVariables() {
  if (!projectId.value) {
    globalVariablesMap.value = {}
    return
  }
  try {
    const data = await apiAutomationApi.getGlobalVariables(projectId.value)
    globalVariablesMap.value = data.variables || {}
  } catch {
    globalVariablesMap.value = {}
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

async function batchGenerateCaseData() {
  if (!selectedCaseIds.value.length) return

  const caseIds = [...selectedCaseIds.value]
  aiGenerateLogs.value = []
  aiGenerateProgress.value = 0
  aiGenerateStatusText.value = '准备批量生成...'
  aiGenerateLogVisible.value = true
  caseBatchGenerating.value = true

  appendAiGenerateLog(`开始批量生成，共 ${caseIds.length} 条用例`, 'info')

  let totalUpdated = 0
  let totalFailed = 0
  let totalSkipped = 0
  let processed = 0

  try {
    for (let offset = 0; offset < caseIds.length; offset += AI_GENERATE_CHUNK_SIZE) {
      const chunk = caseIds.slice(offset, offset + AI_GENERATE_CHUNK_SIZE)
      const end = Math.min(offset + AI_GENERATE_CHUNK_SIZE, caseIds.length)
      const percent = Math.round((offset / caseIds.length) * 100)
      aiGenerateProgress.value = percent
      aiGenerateStatusText.value = `正在处理 ${offset + 1}-${end} / ${caseIds.length} 条用例`
      appendAiGenerateLog(`正在处理第 ${offset + 1}-${end} 条...`, 'info')

      const result = await apiAutomationApi.batchGenerateCaseData({ case_ids: chunk })
      processed = end
      totalUpdated += result.updated_count || 0
      totalFailed += result.failed_count || 0
      totalSkipped += result.skipped_count || 0
      aiGenerateProgress.value = Math.round((processed / caseIds.length) * 100)
      aiGenerateStatusText.value = `已完成 ${processed} / ${caseIds.length} 条`

      for (const item of result.items || []) {
        appendAiGenerateLog(item.log || `[${item.case_name}] ${item.message}`, item.success ? 'success' : 'warn')
      }
    }

    aiGenerateStatusText.value = '正在刷新用例列表...'
    aiGenerateProgress.value = 98
    await loadCases()
    aiGenerateProgress.value = 100
    aiGenerateStatusText.value = `批量生成完成：成功 ${totalUpdated} 条，跳过 ${totalSkipped} 条，失败 ${totalFailed} 条`

    appendAiGenerateLog(
      `批量生成完成：成功 ${totalUpdated} 条，跳过 ${totalSkipped} 条，失败 ${totalFailed} 条`,
      totalUpdated > 0 ? 'success' : 'warn',
    )

    if (totalUpdated > 0) {
      ElMessage.success(`成功为 ${totalUpdated} 条用例生成并保存数据`)
    } else {
      ElMessage.warning('未成功保存任何用例数据，请查看日志')
    }
  } catch (error) {
    aiGenerateProgress.value = 100
    aiGenerateStatusText.value = '批量生成失败'
    appendAiGenerateLog(error?.response?.data?.detail || error?.message || '批量生成失败', 'error')
    ElMessage.error('批量生成失败，请查看日志')
  } finally {
    caseBatchGenerating.value = false
  }
}

function appendAiGenerateLog(text, type = 'info') {
  aiGenerateLogs.value.push({
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    text,
    type,
  })
  nextTick(() => {
    const panel = aiGenerateLogRef.value
    if (panel) {
      panel.scrollTop = panel.scrollHeight
    }
  })
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
    const data = await apiAutomationApi.listRuns(buildReportQueryParams())
    runs.value = data.items || []
    reportTotal.value = data.total || 0
    const maxPage = Math.max(1, Math.ceil(reportTotal.value / reportPageSize.value) || 1)
    if (reportCurrentPage.value > maxPage) {
      reportCurrentPage.value = maxPage
      if (maxPage !== data.page) {
        return loadRuns()
      }
    }
    selectedRunIds.value = []
    reportTableRef.value?.clearSelection()
  } finally {
    reportLoading.value = false
  }
}

function handleReportPageSizeChange() {
  reportCurrentPage.value = 1
  loadRuns()
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
  if (row?.suite_ids?.length) {
    scheduleForm.suite_ids = [...row.suite_ids]
  } else if (row?.suite_id) {
    scheduleForm.suite_ids = [row.suite_id]
  } else if (suiteId.value) {
    scheduleForm.suite_ids = [suiteId.value]
  } else if (runnableSuites.value[0]?.id) {
    scheduleForm.suite_ids = [runnableSuites.value[0].id]
  } else {
    scheduleForm.suite_ids = []
  }
  scheduleForm.schedule_type = row?.schedule_type || 'daily'
  scheduleForm.run_time = row?.run_time || '09:00'
  scheduleForm.week_day = row?.week_day ?? 0
  scheduleForm.interval_minutes = row?.interval_minutes || 60
  scheduleForm.enabled = row?.enabled ?? true
  scheduleDialogVisible.value = true
}

async function saveSchedule() {
  const fields = ['name', 'suite_ids', 'schedule_type']
  if (scheduleForm.schedule_type === 'weekly') fields.push('week_day')
  if (scheduleForm.schedule_type !== 'interval') fields.push('run_time')
  if (scheduleForm.schedule_type === 'interval') fields.push('interval_minutes')
  await scheduleFormRef.value.validateField(fields)
  scheduleSaving.value = true
  try {
    const payload = {
      name: scheduleForm.name,
      suite_ids: [...scheduleForm.suite_ids],
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
    await Promise.all([loadSchedules(), loadRuns(), loadSuites()])
    if (result.run_ids?.length) {
      await loadReportDetail(result.run_ids)
    } else if (result.run_id) {
      await loadReportDetail([result.run_id])
    }
  } finally {
    scheduleRunningId.value = null
  }
}

async function viewScheduleLastReport(row) {
  const runIds = row.last_run_ids?.length
    ? row.last_run_ids
    : row.last_run_id
      ? [row.last_run_id]
      : []
  await loadReportDetail(runIds)
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
  await loadGlobalVariables()
  await loadCases()
  await loadSuites()
  if (savedId) {
    activeCaseId.value = savedId
  } else if (cases.value.length && !activeCaseId.value) {
    activeCaseId.value = cases.value[cases.value.length - 1].id
  }
}

function variablesJsonToRows(jsonText) {
  try {
    const parsed = JSON.parse(jsonText || '{}')
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return [emptyKvRow()]
    }
    const entries = Object.entries(parsed)
    if (!entries.length) return [emptyKvRow()]
    return entries.map(([key, value]) => ({
      key,
      value: value == null ? '' : String(value),
      enabled: true,
      desc: '',
    }))
  } catch {
    return [emptyKvRow()]
  }
}

function variableRowsToJson(rows) {
  const result = {}
  for (const row of rows || []) {
    if (row.enabled === false) continue
    const key = row.key?.trim()
    if (key) result[key] = row.value ?? ''
  }
  return JSON.stringify(result, null, 2)
}

function openEnvDialog(row = null) {
  envEditing.value = row
  envForm.name = row?.name || ''
  envForm.base_url = row?.base_url || ''
  envForm.default_headers = row?.default_headers || '{"Content-Type":"application/json"}'
  envForm.description = row?.description || ''
  envVariableRows.value = variablesJsonToRows(row?.variables || '{}')
  envDialogVisible.value = true
}

async function openGlobalVarDialog() {
  if (!projectId.value) return
  globalVarDialogVisible.value = true
  try {
    const data = await apiAutomationApi.getGlobalVariables(projectId.value)
    globalVariableRows.value = variablesJsonToRows(JSON.stringify(data.variables || {}))
  } catch {
    globalVariableRows.value = [emptyKvRow()]
  }
}

async function saveGlobalVariables() {
  if (!projectId.value) return
  globalVarSaving.value = true
  try {
    const payload = {}
    for (const row of globalVariableRows.value) {
      if (row.enabled === false) continue
      const key = row.key?.trim()
      if (key) payload[key] = row.value ?? ''
    }
    await apiAutomationApi.updateGlobalVariables(projectId.value, { variables: payload })
    ElMessage.success('全局变量已保存')
    globalVarDialogVisible.value = false
    await loadGlobalVariables()
  } finally {
    globalVarSaving.value = false
  }
}

async function saveEnv() {
  await envFormRef.value.validate()
  envSaving.value = true
  try {
    const payload = {
      ...envForm,
      variables: variableRowsToJson(envVariableRows.value),
    }
    if (envEditing.value) {
      await apiAutomationApi.updateEnvironment(envEditing.value.id, payload)
      ElMessage.success('环境已更新')
    } else {
      await apiAutomationApi.createEnvironment({ ...payload, project_id: projectId.value })
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
    items: preview ? undefined : swaggerPreview.value,
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

async function handleSwaggerAiGenerate() {
  if (!swaggerPreview.value.length) return

  swaggerAiLogs.value = []
  swaggerAiProgress.value = 0
  swaggerAiStatusText.value = '准备生成...'
  swaggerAiLogVisible.value = true
  swaggerAiGenerating.value = true

  const items = [...swaggerPreview.value]
  appendSwaggerAiLog(`开始为 ${items.length} 条接口生成测试数据`, 'info')

  let totalUpdated = 0
  let totalSkipped = 0
  let totalFailed = 0
  let totalFallback = 0
  let processed = 0

  try {
    for (let offset = 0; offset < items.length; offset += SWAGGER_AI_CHUNK_SIZE) {
      const chunk = items.slice(offset, offset + SWAGGER_AI_CHUNK_SIZE)
      const end = Math.min(offset + SWAGGER_AI_CHUNK_SIZE, items.length)
      swaggerAiProgress.value = Math.round((offset / items.length) * 100)
      swaggerAiStatusText.value = `正在处理 ${offset + 1}-${end} / ${items.length} 条接口`
      appendSwaggerAiLog(`正在处理第 ${offset + 1}-${end} 条...`, 'info')

      const data = await apiAutomationApi.swaggerGenerateData({ items: chunk })
      for (let i = 0; i < (data.items || []).length; i++) {
        swaggerPreview.value[offset + i] = data.items[i]
      }
      processed = end
      totalUpdated += data.updated_count || 0
      totalSkipped += data.skipped_count || 0
      totalFailed += data.failed_count || 0
      totalFallback += data.fallback_count || 0
      swaggerAiProgress.value = Math.round((processed / items.length) * 100)
      swaggerAiStatusText.value = `已完成 ${processed} / ${items.length} 条`

      for (const detail of data.details || []) {
        const logType = detail.success ? 'success' : detail.skipped ? 'warn' : 'error'
        appendSwaggerAiLog(detail.log || `[${detail.name}] ${detail.message}`, logType)
      }
    }

    swaggerAiProgress.value = 100
    swaggerAiStatusText.value = `造数完成：成功 ${totalUpdated} 条，跳过 ${totalSkipped} 条，失败 ${totalFailed} 条`
    appendSwaggerAiLog(
      `造数完成：成功 ${totalUpdated} 条，跳过 ${totalSkipped} 条，失败 ${totalFailed} 条`
      + (totalFallback ? `，${totalFallback} 条改用 Mock` : ''),
      totalUpdated > 0 ? 'success' : 'warn',
    )

    if (totalUpdated > 0) {
      ElMessage.success(`已为 ${totalUpdated} 条接口生成测试数据`)
    } else if (totalSkipped > 0 && !totalFailed) {
      ElMessage.warning('所选接口均无入参，无法生成数据')
    } else {
      ElMessage.warning('未生成任何接口数据，请查看日志')
    }
  } catch (error) {
    swaggerAiProgress.value = 100
    swaggerAiStatusText.value = '造数失败'
    appendSwaggerAiLog(error?.response?.data?.detail || error?.message || 'AI 造数失败', 'error')
    ElMessage.error('AI 造数失败，请查看日志')
  } finally {
    swaggerAiGenerating.value = false
  }
}

function appendSwaggerAiLog(text, type = 'info') {
  swaggerAiLogs.value.push({
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    text,
    type,
  })
  nextTick(() => {
    const panel = swaggerAiLogRef.value
    if (panel) {
      panel.scrollTop = panel.scrollHeight
    }
  })
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
  if (!suiteId.value) return

  suiteRunLogs.value = []
  suiteRunProgress.value = 0
  suiteRunStatusText.value = '准备执行...'
  suiteRunResultId.value = null
  suiteRunFailedCount.value = 0
  suiteRunLogVisible.value = true
  running.value = true

  try {
    await apiAutomationApi.runSuiteStream(suiteId.value, handleSuiteRunEvent)
  } catch (error) {
    suiteRunProgress.value = 100
    suiteRunStatusText.value = '执行失败'
    appendSuiteRunLog(error?.message || '套件执行失败', 'error')
    ElMessage.error(error?.message || '套件执行失败')
  } finally {
    running.value = false
  }
}

function handleSuiteRunEvent(event) {
  if (event.type === 'start') {
    suiteRunStatusText.value = event.message || '开始执行...'
    appendSuiteRunLog(event.message || '开始执行...', 'info')
    return
  }

  if (event.type === 'step') {
    const total = event.total || 1
    suiteRunProgress.value = Math.min(99, Math.round((event.index / total) * 100))
    suiteRunStatusText.value = `正在执行 ${event.index}/${total}`
    const statusText = statusLabel[event.status] || event.status
    const httpPart = event.response_status ? `，HTTP ${event.response_status}` : ''
    const errPart = event.error_message ? ` — ${event.error_message}` : ''
    appendSuiteRunLog(
      `[${event.index}/${total}] ${event.method} ${event.case_name} — ${statusText} (${Math.round(event.duration_ms || 0)}ms${httpPart})${errPart}`,
      event.status === 'passed' ? 'success' : 'error',
    )
    return
  }

  if (event.type === 'done') {
    suiteRunProgress.value = 100
    suiteRunResultId.value = event.run_id
    suiteRunFailedCount.value = event.failed_count || 0
    suiteRunStatusText.value = event.message || '执行完成'
    appendSuiteRunLog(event.message || '执行完成', event.failed_count > 0 ? 'warn' : 'success')
    ElMessage.success(event.message || '执行完成')
    Promise.all([loadSuites(), loadRuns()])
    return
  }

  if (event.type === 'error') {
    suiteRunProgress.value = 100
    suiteRunStatusText.value = '执行失败'
    appendSuiteRunLog(event.message || '执行失败', 'error')
    throw new Error(event.message || '执行失败')
  }
}

function appendSuiteRunLog(text, type = 'info') {
  suiteRunLogs.value.push({
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    text,
    type,
  })
  nextTick(() => {
    const panel = suiteRunLogRef.value
    if (panel) {
      panel.scrollTop = panel.scrollHeight
    }
  })
}

async function openSuiteRunReport() {
  if (!suiteRunResultId.value) return
  suiteRunLogVisible.value = false
  await router.push('/api-automation/reports')
  await viewReport({ id: suiteRunResultId.value })
}

async function loadReportDetail(runIds) {
  const ids = (runIds || []).filter(Boolean)
  if (!ids.length) {
    ElMessage.warning('暂无执行报告')
    return
  }
  reportVisible.value = true
  reportDetailLoading.value = true
  try {
    if (ids.length > 1) {
      reportDetail.value = await apiAutomationApi.getCombinedRun(ids)
    } else {
      reportDetail.value = await apiAutomationApi.getRun(ids[0])
    }
    reportStepFilter.value = 'all'
    expandedSteps.value = []
  } finally {
    reportDetailLoading.value = false
  }
}

async function viewReport(row) {
  await loadReportDetail([row.id])
}

function setReportStepFilter(filter) {
  reportStepFilter.value = filter
  expandedSteps.value = []
}

async function removeRun(row) {
  await ElMessageBox.confirm(`确认删除报告「${formatReportTime(row.started_at)}」？`, '提示', { type: 'warning' })
  await apiAutomationApi.deleteRun(row.id)
  ElMessage.success('删除成功')
  await loadRuns()
}

function onRunSelectionChange(rows) {
  selectedRunIds.value = (rows || []).map((row) => row.id)
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function buildRunExportFilename(row, format, count = 1) {
  const extMap = { excel: 'xlsx', word: 'docx', pdf: 'pdf', json: 'json' }
  const ext = extMap[format] || 'xlsx'
  if (count === 1 && row?.started_at) {
    const suite = String(row.suite_name || 'report').replace(/[/\\]/g, '_')
    return `测试报告_${reportTimeFileToken(row.started_at)}_${suite}.${ext}`
  }
  return `测试报告_批量导出_${count}条.${ext}`
}

async function exportRun(row, format = 'excel') {
  runExportingId.value = row.id
  try {
    const blob = await apiAutomationApi.exportRun(row.id, format)
    downloadBlob(blob, buildRunExportFilename(row, format))
    ElMessage.success('导出成功')
  } finally {
    runExportingId.value = null
  }
}

async function batchExportRuns(format = 'excel') {
  if (!selectedRunIds.value.length) return
  runBatchExporting.value = true
  try {
    const blob = await apiAutomationApi.batchExportRuns({
      run_ids: selectedRunIds.value,
      format,
    })
    downloadBlob(blob, buildRunExportFilename(null, format, selectedRunIds.value.length))
    ElMessage.success('导出成功')
  } finally {
    runBatchExporting.value = false
  }
}

async function batchRemoveRuns() {
  if (!selectedRunIds.value.length) return
  await ElMessageBox.confirm(
    `确认删除选中的 ${selectedRunIds.value.length} 条测试报告？此操作不可恢复。`,
    '批量删除',
    { type: 'warning' },
  )
  runBatchDeleting.value = true
  try {
    const result = await apiAutomationApi.batchDeleteRuns({ run_ids: selectedRunIds.value })
    ElMessage.success(result.message || '删除成功')
    await loadRuns()
  } finally {
    runBatchDeleting.value = false
  }
}

onMounted(async () => {
  registerApiAutomationAssistantHandlers()
  await loadProjects()
})

function registerApiAutomationAssistantHandlers() {
  registerAssistantHandler('apiAutomation.ensureProject', async () => {
    if (!projectId.value) {
      if (!projects.value.length) {
        await loadProjects()
      } else {
        projectId.value = projects.value[0].id
        await reloadAll()
      }
    }
    if (!projectId.value) {
      throw new Error('请先创建项目')
    }
  })

  registerAssistantHandler('apiAutomation.ensureEnvironment', async (payload = {}) => {
    if (!projectId.value) {
      throw new Error('请先选择项目')
    }
    if (!environments.value.length) {
      await loadEnvironments()
    }
    if (!environments.value.length) {
      await apiAutomationApi.createEnvironment({
        project_id: projectId.value,
        name: payload.name || '默认环境',
        base_url: payload.base_url || 'http://127.0.0.1',
        default_headers: '{"Content-Type":"application/json"}',
        variables: '{}',
        description: '由 AI 助手自动创建',
      })
      await loadEnvironments()
    }
    if (!environments.value.length) {
      throw new Error('无法创建执行环境，请先在「环境管理」中手动配置')
    }
  })

  registerAssistantHandler('apiAutomation.createSuite', async (payload = {}) => {
    if (!projectId.value) {
      if (!projects.value.length) {
        await loadProjects()
      }
      if (projects.value.length) {
        projectId.value = projects.value[0].id
        await reloadAll()
      }
    }
    if (!projectId.value) {
      throw new Error('请先创建项目')
    }

    if (!environments.value.length) {
      await loadEnvironments()
    }
    if (!environments.value.length) {
      await apiAutomationApi.createEnvironment({
        project_id: projectId.value,
        name: payload.env_name || '默认环境',
        base_url: payload.base_url || 'http://127.0.0.1',
        default_headers: '{"Content-Type":"application/json"}',
        variables: '{}',
        description: '由 AI 助手自动创建',
      })
      await loadEnvironments()
    }
    if (!environments.value.length) {
      throw new Error('无法创建执行环境，请先在「环境管理」中手动配置')
    }

    const suiteName = (payload.name || 'AI测试套件').trim()
    if (!suiteName) {
      throw new Error('套件名称不能为空')
    }

    openSuiteDialog(null, payload.parent_id ?? activeFolderId.value ?? null)
    suiteForm.name = suiteName
    suiteForm.description = payload.description || ''
    suiteForm.environment_id = payload.environment_id || environments.value[0]?.id || null
    await nextTick()
    await saveSuite()
  })

  registerAssistantHandler('apiAutomation.selectFirstSuite', async (payload = {}) => {
    if (!projectId.value) {
      throw new Error('请先选择项目')
    }
    if (!suites.value.length) {
      await loadSuites()
    }
    if (!suiteId.value) {
      const first = suites.value.find((item) => !item.is_folder)
      if (first) {
        selectSuite(first.id)
        await nextTick()
        return
      }
      if (payload.auto_create === false) {
        throw new Error('当前项目下没有测试套件，请先新建套件')
      }
      if (!environments.value.length) {
        await loadEnvironments()
      }
      if (!environments.value.length) {
        await apiAutomationApi.createEnvironment({
          project_id: projectId.value,
          name: '默认环境',
          base_url: payload.base_url || 'http://127.0.0.1',
          default_headers: '{"Content-Type":"application/json"}',
          variables: '{}',
          description: '由 AI 助手自动创建',
        })
        await loadEnvironments()
      }
      openSuiteDialog(null, activeFolderId.value ?? null)
      suiteForm.name = payload.name || 'AI测试套件'
      suiteForm.description = payload.description || ''
      suiteForm.environment_id = environments.value[0]?.id || null
      await nextTick()
      await saveSuite()
    }
  })

  registerAssistantHandler('apiAutomation.openSwaggerImport', async () => {
    if (!suiteId.value) {
      throw new Error('请先选择测试套件')
    }
    openSwaggerDialog()
    swaggerSourceType.value = 'url'
    await nextTick()
  })

  registerAssistantHandler('apiAutomation.setSwaggerUrl', async (payload = {}) => {
    const url = payload.url || ''
    if (!url) {
      throw new Error('缺少 Swagger URL')
    }
    swaggerSourceType.value = 'url'
    swaggerUrl.value = url
    await nextTick()
  })

  registerAssistantHandler('apiAutomation.parseSwagger', async () => {
    if (!canParseSwagger.value) {
      throw new Error('Swagger URL 未填写')
    }
    await handleParseSwagger()
    if (!swaggerPreview.value.length) {
      throw new Error('未解析到可导入的接口，请检查 URL 是否为 OpenAPI 文档地址')
    }
  })

  registerAssistantHandler('apiAutomation.confirmSwaggerImport', async () => {
    if (!swaggerPreview.value.length) {
      throw new Error('请先解析预览接口')
    }
    await handleImportSwagger()
  })
}

function unregisterApiAutomationAssistantHandlers() {
  for (const name of ASSISTANT_HANDLER_NAMES) {
    unregisterAssistantHandler(name)
  }
}

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
  unregisterApiAutomationAssistantHandlers()
})
</script>

<style scoped>
.assistant-hidden-trigger {
  position: absolute;
  width: 0;
  height: 0;
  padding: 0;
  margin: 0;
  border: 0;
  opacity: 0;
  pointer-events: none;
  overflow: hidden;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.report-search-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-left: auto;
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

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.report-row-actions {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  white-space: nowrap;
}

.report-row-actions :deep(.el-dropdown) {
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
}

.report-row-actions :deep(.el-button.is-link) {
  vertical-align: middle;
  height: auto;
  padding-top: 0;
  padding-bottom: 0;
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

.env-variables-panel {
  width: 100%;
}

.env-variables-panel .form-tip {
  margin-top: 0;
  margin-bottom: 8px;
}

.global-var-tip {
  margin-top: 0;
  margin-bottom: 12px;
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
  flex-wrap: wrap;
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

.ai-generate-progress-block {
  margin-bottom: 12px;
}

.ai-generate-progress-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: #475569;
}

.ai-generate-log-panel {
  max-height: 420px;
  overflow-y: auto;
  padding: 12px;
  background: #0f172a;
  border-radius: 8px;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
}

.ai-generate-log-line {
  display: flex;
  gap: 10px;
  line-height: 1.7;
  color: #e2e8f0;
}

.ai-generate-log-line .log-time {
  flex-shrink: 0;
  color: #94a3b8;
}

.ai-generate-log-line.log-success .log-text {
  color: #4ade80;
}

.ai-generate-log-line.log-warn .log-text {
  color: #fbbf24;
}

.ai-generate-log-line.log-error .log-text {
  color: #f87171;
}

.ai-generate-log-line.log-info .log-text {
  color: #cbd5e1;
}

.report-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.report-drawer-header {
  width: 100%;
  padding-right: 8px;
}

.report-drawer-main {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.report-drawer-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.report-drawer-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.3;
}

.report-drawer-suite {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 13px;
  font-weight: 500;
}

.report-drawer-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.report-meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 180px;
}

.report-meta-label {
  font-size: 12px;
  color: #64748b;
}

.report-meta-value {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.report-meta-divider {
  width: 1px;
  height: 36px;
  background: #e2e8f0;
}

.report-drawer-sub {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
  font-size: 13px;
  color: #64748b;
}

.report-drawer-time {
  padding-left: 10px;
  border-left: 1px solid #e2e8f0;
}

.report-drawer-suite-count {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  font-weight: 500;
}

.report-section-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-suite-section {
  padding-bottom: 4px;
}

.report-suite-title {
  font-weight: 600;
  color: #1e293b;
}

.report-suite-meta {
  margin-left: 10px;
  color: #64748b;
  font-size: 12px;
  font-weight: 400;
}

.report-panel {
  padding-bottom: 8px;
}

.report-steps :deep(.el-collapse-item) {
  margin-bottom: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

.report-steps :deep(.el-collapse-item__header) {
  height: auto;
  min-height: 52px;
  padding: 10px 16px;
  background: #fafbfc;
  border-bottom: none;
  line-height: 1.4;
}

.report-steps :deep(.el-collapse-item.is-active .el-collapse-item__header) {
  border-bottom: 1px solid #e2e8f0;
}

.report-steps :deep(.el-collapse-item__wrap) {
  border-top: none;
}

.report-steps :deep(.el-collapse-item__content) {
  padding: 16px 18px 18px;
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

.report-count-value {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.report-count-btn {
  border: none;
  background: transparent;
  padding: 0 4px;
  font: inherit;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s, box-shadow 0.15s;
}

.report-count-btn:hover {
  background: rgba(49, 130, 206, 0.08);
}

.report-count-btn.active {
  box-shadow: inset 0 0 0 2px currentColor;
}

.report-filter-tip {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 400;
  color: #909399;
}

.step-title {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding-right: 8px;
}

.step-index {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #eef2ff;
  font-size: 12px;
  font-weight: 700;
  color: #4338ca;
}

.step-method {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
}

.step-method-get { background: #dcfce7; color: #166534; }
.step-method-post { background: #dbeafe; color: #1d4ed8; }
.step-method-put { background: #fef3c7; color: #b45309; }
.step-method-patch { background: #e0e7ff; color: #4338ca; }
.step-method-delete { background: #fee2e2; color: #b91c1c; }

.step-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #334155;
  font-weight: 500;
}

.step-status-code {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}

.step-status-code.is-success { background: #dcfce7; color: #15803d; }
.step-status-code.is-warning { background: #ffedd5; color: #c2410c; }
.step-status-code.is-danger { background: #fee2e2; color: #b91c1c; }
.step-status-code.is-muted { background: #f1f5f9; color: #64748b; }

.step-duration {
  flex-shrink: 0;
  color: #64748b;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
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

  .report-meta-divider {
    display: none;
  }

  .report-drawer-meta {
    gap: 12px;
  }
}
</style>
