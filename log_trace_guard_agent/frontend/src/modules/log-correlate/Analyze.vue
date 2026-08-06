<template>
  <div class="g-stack">
    <!-- 运维模式：简洁专业 -->
    <div v-if="mode === 'ops'">
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Connection /></el-icon> 日志联合审查</div>
            <div class="g-card-desc">支持粘贴多源日志或上传文件（.log/.txt/.csv/.json），检测攻击链和跨设备关联事件</div>
          </div>
          <div class="g-actions">
            <el-button size="small" @click="showSample = !showSample">
              {{ showSample ? '收起' : '查看示例' }}
            </el-button>
            <el-button size="small" type="primary" plain @click="fillSample">填充测试日志</el-button>
          </div>
        </div>

        <div v-if="showSample" style="margin-bottom:12px">
          <div class="g-alert g-alert--info">
            <el-icon><InfoFilled /></el-icon>
            <span>示例：SSH暴力破解→提权攻击链</span>
          </div>
          <div class="g-code-block" style="font-size:12px">
            <div class="g-code-body" style="max-height:120px">
              <code>{{ sampleLogs }}</code>
            </div>
          </div>
        </div>

        <el-input
          v-model="input" type="textarea" :rows="8"
          placeholder="粘贴日志内容，每行一条...&#10;Ctrl+Enter 快速提交&#10;&#10;支持安全设备、服务器、数据库、WAF等&#10;中文/英文日志均可识别" class="log-input-area"
          :disabled="loading"
          @keyup.ctrl.enter="submit" @keyup.meta.enter="submit"
        />

        <div class="g-param-row" style="margin-top:12px">
          <div class="g-param-item">
            <label>时间窗口</label>
            <el-input-number v-model="timeWindow" :min="1" :max="1440" size="small" style="width:100px" />
            <span class="g-param-desc">分钟</span>
          </div>
          <div class="g-param-item">
            <label>使用 LLM 分析</label>
            <el-switch v-model="useLlm" size="small" />
            <span class="g-param-desc">{{ useLlm ? 'LLM 语义分析（慢但更准）' : '关键词匹配优先' }}</span>
          </div>
          <div style="flex-grow:1;text-align:right">
            <FileUpload
              ref="fileUploadRef"
              :disabled="loading"
              :upload-api="(formData) => Api.logCorrelate.upload(formData)"
              :cleanup-api="(data) => Api.logCorrelate.cleanup(data)"
              @update:files="onFilesUpdate"
              @upload-success="onUploadSuccess"
            />
          </div>
        </div>

        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" :loading="loading" :disabled="!input.trim() && !uploadedFilePaths.length" @click="submit">
            <el-icon style="margin-right:4px"><Search /></el-icon> 关联分析
          </el-button>
          <el-button :disabled="loading" @click="clear">清空</el-button>
        </div>
      </div>
    </div>

    <!-- 实训模式：带引导 -->
    <template v-else>
      <AlertGuide type="info" title="日志联合审查 — 发现隐蔽攻击链">
        输入多源日志（每行一条），系统自动进行安全攻击链检测。支持中文/英文日志，内置 16 种攻击链模型，关键词匹配不满 60% 时自动降级 LLM 智能分析。
      </AlertGuide>

      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Connection /></el-icon> 日志联合审查</div>
            <div class="g-card-desc">支持粘贴多源日志或上传文件（.log/.txt/.csv/.json），自动检测攻击链和关联事件</div>
          </div>
          <div class="g-actions">
            <el-button size="small" @click="showSample = !showSample">
              {{ showSample ? '收起' : '查看示例' }}
            </el-button>
            <el-button size="small" type="primary" plain @click="fillSample">填充测试日志</el-button>
          </div>
        </div>

        <div v-if="showSample" style="margin-bottom:12px">
          <div class="g-alert g-alert--info">
            <el-icon><InfoFilled /></el-icon>
            <span>示例：SSH暴力破解→提权攻击链</span>
          </div>
          <div class="g-code-block" style="font-size:12px">
            <div class="g-code-body" style="max-height:120px">
              <code>{{ sampleLogs }}</code>
            </div>
          </div>
        </div>

        <el-input
          v-model="input" type="textarea" :rows="8"
          placeholder="在此粘贴日志内容，每行一条日志...&#10;支持粘贴安全设备/服务器日志，Ctrl+Enter 快速提交" class="log-input-area"
          :disabled="loading"
          @keyup.ctrl.enter="submit" @keyup.meta.enter="submit"
        />

        <div class="g-param-row" style="margin-top:12px">
          <div class="g-param-item">
            <label>时间窗口（分钟）</label>
            <el-input-number v-model="timeWindow" :min="1" :max="1440" size="small" style="width:120px" />
            <span class="g-param-desc">事件关联的最大时间跨度</span>
          </div>
          <div class="g-param-item">
            <label>LLM 分析</label>
            <el-switch v-model="useLlm" size="small" />
            <span class="g-param-desc">{{ useLlm ? '语义分析（更准）' : '关键词优先（更快）' }}</span>
          </div>
          <div style="flex-grow:1;text-align:right">
            <FileUpload
              ref="fileUploadRef"
              :disabled="loading"
              :upload-api="(formData) => Api.logCorrelate.upload(formData)"
              :cleanup-api="(data) => Api.logCorrelate.cleanup(data)"
              @update:files="onFilesUpdate"
              @upload-success="onUploadSuccess"
            />
          </div>
        </div>

        <div class="g-input-guide">
          <el-icon><InfoFilled /></el-icon>
          <span>支持粘贴多条日志，Ctrl+Enter 快速提交。支持上传 .log/.txt/.csv/.json 文件（支持多选）。</span>
        </div>

        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" :loading="loading" :disabled="!input.trim() && !uploadedFilePaths.length" @click="submit">
            <el-icon style="margin-right:4px"><Search /></el-icon> 关联分析
          </el-button>
          <el-button :disabled="loading" @click="clear">清空</el-button>
        </div>
      </div>
    </template>

    <!-- ★ 回流通知条 -->
    <div v-if="incomingData" class="g-card" style="border:1px solid var(--el-color-primary);margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:12px;padding:4px 0">
        <el-icon :size="20" color="var(--el-color-primary)"><Connection /></el-icon>
        <span style="flex:1;font-size:13px">
          来自 <strong>{{ incomingData.source === 'trace-splunk' ? '攻击溯源·Splunk 查询' : '外部模块' }}</strong>
          的 {{ incomingData.logs?.length || 0 }} 条日志，将自动进行关联分析
        </span>
        <el-button size="small" @click="incomingData = null; clear()">取消</el-button>
      </div>
    </div>

    <!-- 分析结果 -->
    <div v-if="result" class="g-card slide">
      <!-- 分析概览 -->
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><DataAnalysis /></el-icon> 分析结果</div>
        <div class="g-actions">
          <el-tag v-if="result.method === 'keyword'" type="success" size="small" effect="dark">关键词匹配</el-tag>
          <el-tag v-else-if="result.method === 'llm'" type="warning" size="small" effect="dark">LLM 分析</el-tag>
          <el-tag v-else-if="result.method === 'hybrid'" type="info" size="small" effect="dark">混合模式</el-tag>
          <el-tag v-if="incomingData?.source" type="primary" size="small" effect="plain">回流分析</el-tag>
        </div>
      </div>

      <el-descriptions :column="3" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="总日志行数">{{ result.total_events }}</el-descriptions-item>
        <el-descriptions-item label="攻击链数">
          <el-tag :type="result.chains?.length ? 'danger' : 'success'" size="small">
            {{ result.chains?.length || 0 }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="分析方法">
          <el-tag :type="result.method === 'keyword' ? 'success' : 'warning'" size="small">
            {{ result.method === 'keyword' ? '关键词匹配' : result.method === 'llm' ? 'LLM 语义分析' : '混合分析' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <div v-if="result.source_files?.length" style="margin-bottom:12px">
        <span style="font-size:12px;color:var(--text-tertiary)">数据来源：</span>
        <el-tag v-for="(f, fi) in result.source_files" :key="fi" size="small" type="info" effect="plain" style="margin-right:4px">
          {{ f }}
        </el-tag>
      </div>

      <div class="g-summary" style="margin-bottom:16px">
        <el-alert :title="result.summary" type="info" :closable="false" show-icon />
      </div>

      <!-- 匹配关键词 -->
      <div v-if="result.matched_keywords?.length" style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:6px;font-size:13px">
          <el-icon><Search /></el-icon> 匹配关键词（{{ result.matched_keywords.length }} 个）
        </div>
        <div style="display:flex;gap:4px;flex-wrap:wrap">
          <el-tag v-for="(kw, ki) in result.matched_keywords" :key="ki" size="small" type="info" effect="plain">
            {{ kw }}
          </el-tag>
        </div>
      </div>

      <!-- 攻击链列表 -->
      <div v-if="result.chains?.length" style="margin-top:16px">
        <div style="font-weight:600;margin-bottom:12px;font-size:14px">
          <el-icon><WarningFilled /></el-icon> 检测到 {{ result.chains.length }} 条攻击链
        </div>

        <div v-for="(chain, idx) in result.chains" :key="idx" class="g-chain-card" style="margin-bottom:12px">
          <div class="g-chain-header" style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap">
            <RiskBadge :level="getRiskKey(chain.risk_level)" :label="chain.risk_level" />
            <strong>{{ chain.chain_name }}</strong>
            <el-tag size="small" :type="chain.confidence >= 0.7 ? 'success' : 'warning'">
              置信度: {{ Math.round(chain.confidence * 100) }}%
            </el-tag>
            <el-tag size="small" type="info">事件数: {{ chain.event_count }}</el-tag>
            <el-tag v-if="chain.attack_type" size="small" type="warning">{{ chain.attack_type }}</el-tag>
          </div>
          <div style="font-size:13px;color:var(--text-secondary);margin-bottom:6px">
            {{ chain.description }}
          </div>
          <div v-if="chain.matched_keywords?.length" style="margin-bottom:6px">
            <span style="font-size:12px;color:var(--text-tertiary)">匹配关键词：</span>
            <el-tag v-for="(kw, ki) in chain.matched_keywords" :key="ki" size="small" style="margin-right:4px;margin-bottom:4px" effect="plain">
              {{ kw.length > 30 ? kw.slice(0, 30) + '...' : kw }}
            </el-tag>
          </div>
          <div v-if="chain.indicators?.length" style="margin-bottom:6px">
            <span style="font-size:12px;color:var(--text-tertiary)">指标：</span>
            <span v-for="(ind, ii) in chain.indicators" :key="ii" style="font-size:12px;color:var(--color-danger);margin-right:8px">
              {{ ind }}
            </span>
          </div>
          <div v-if="chain.suggestion" style="margin-top:4px;padding:6px 8px;background:var(--bg-secondary);border-radius:4px;font-size:12px">
            <el-icon><Tickets /></el-icon> 处置建议：{{ chain.suggestion }}
          </div>
          <!-- 联动操作按钮 -->
          <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
            <el-button size="small" type="primary" plain @click="toTraceScript(chain)">
              <el-icon><Document /></el-icon> 生成溯源脚本
            </el-button>
            <el-button v-if="mode !== 'ops'" size="small" type="success" plain @click="toTrainingScenario(chain)">
              <el-icon><Monitor /></el-icon> 下发实训场景
            </el-button>
          </div>
        </div>
      </div>

      <!-- 无攻击链 -->
      <div v-else class="g-alert g-alert--success" style="margin-top:12px">
        <el-icon><CircleCheck /></el-icon>
        <span>未检测到已知攻击链模式。可尝试开启「LLM 分析」重新分析。</span>
        <el-button v-if="!useLlm" size="small" type="primary" style="margin-left:12px" @click="retryWithLLM">
          开启 LLM 重试
        </el-button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide
        title="日志联合审查 — 发现隐蔽攻击链"
        desc="输入多源日志（每行一条），系统自动检测安全攻击链。内置 16 种攻击链规则，支持中文/英文日志，关键词匹配不足时自动降级 LLM 智能分析。"
        action-text="加载攻击链样例"
        @action="fillSample"
      />
    </div>

    <!-- ★ 升级版：溯源脚本结果弹窗（含完整攻击链展示 + 执行按钮） -->
    <el-dialog v-model="linkDialogVisible" :title="linkDialogTitle" width="720px" top="5vh">
      <div v-if="linkLoading" style="text-align:center;padding:40px">
        <el-icon class="is-loading" :size="28"><Loading /></el-icon>
        <div style="margin-top:12px;color:var(--text-secondary)">{{ linkIsScenario ? '正在生成实战场景...' : '正在生成溯源脚本...' }}</div>
      </div>

      <template v-else-if="linkResult">
        <!-- 错误状态 -->
        <div v-if="linkResult.code !== 0 && !linkResult.success" class="g-alert g-alert--warning" style="margin-bottom:12px">
          <el-icon><Warning /></el-icon>
          <span>{{ linkResult.msg || '操作失败' }}</span>
        </div>

        <!-- 成功 — 场景模式 (实战实训) -->
        <template v-if="linkResult.success">
          <!-- 场景模式 -->
          <template v-if="linkIsScenario">
            <div class="g-alert g-alert--success" style="margin-bottom:12px">
              <el-icon><CircleCheck /></el-icon>
              <span>{{ linkScenarioMessage || '实战场景已生成' }}</span>
            </div>
            <div v-if="scenarioInfo" class="g-card" style="margin-bottom:12px;padding:12px">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap">
                <el-tag type="danger" size="small" effect="dark">实战</el-tag>
                <strong style="font-size:15px">{{ scenarioInfo.name }}</strong>
                <RiskBadge :level="diffLevel(scenarioInfo.difficulty)" :label="scenarioInfo.difficulty" />
              </div>
              <div style="font-size:13px;color:var(--text-secondary);margin-bottom:8px">{{ scenarioInfo.description }}</div>
              <div v-if="scenarioInfo.objectives?.length" style="margin-bottom:8px">
                <div style="font-weight:600;font-size:12px;margin-bottom:4px">学习目标：</div>
                <ul style="margin:0;padding-left:16px;font-size:12px;color:var(--text-secondary)">
                  <li v-for="(obj, oi) in scenarioInfo.objectives" :key="oi">{{ obj }}</li>
                </ul>
              </div>
              <div style="font-weight:600;font-size:12px;margin-bottom:6px">实训任务（{{ scenarioTasks.length }} 个）：</div>
              <div v-for="(task, ti) in scenarioTasks" :key="ti" style="padding:6px 8px;margin-bottom:4px;background:var(--bg-secondary);border-radius:4px;font-size:12px">
                <div style="font-weight:500">T{{ ti+1 }}. {{ task.title }}</div>
                <div style="color:var(--text-tertiary);margin-top:2px">{{ task.description }}</div>
              </div>
            </div>
            <el-button type="primary" size="large" style="width:100%" @click="startTrainingFromLink">
              <el-icon><Promotion /></el-icon> 立即进入实训
            </el-button>
          </template>
          <!-- 溯源模式 -->
          <template v-else>
            <div class="g-alert g-alert--success" style="margin-bottom:12px">
              <el-icon><CircleCheck /></el-icon>
              <span>溯源脚本已生成</span>
            </div>

          <!-- 攻击阶段 + 入口 -->
          <el-descriptions :column="2" border size="small" style="margin-bottom:12px">
            <el-descriptions-item label="攻击阶段">
              <el-tag
                :type="linkData?.attack_stage?.includes('数据窃取') ? 'danger' : linkData?.attack_stage?.includes('横向移动') ? 'warning' : 'info'"
                size="small"
              >{{ linkData?.attack_stage || '未知' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="攻击入口">{{ linkData?.entry_point || '未知' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 受影响资产 -->
          <div v-if="linkData?.affected_assets?.length" style="margin-bottom:12px">
            <div style="font-weight:600;margin-bottom:4px;font-size:13px">受影响资产</div>
            <el-tag v-for="(a,i) in linkData.affected_assets" :key="i" type="danger" size="small" style="margin-right:4px;margin-bottom:4px">{{ a }}</el-tag>
          </div>

          <!-- 攻击链事件 — 时间轴 -->
          <div v-if="linkData?.attack_chain?.length" style="margin-bottom:12px">
            <div style="font-weight:600;margin-bottom:6px;font-size:13px">
              <el-icon><Timer /></el-icon> 攻击时间轴（{{ linkData.attack_chain.length }} 个事件）
            </div>
            <div class="timeline">
              <template v-for="(ev,i) in linkData.attack_chain" :key="i">
                <div v-if="i===0||getEventPhase(ev.event_type)!==getEventPhase(linkData.attack_chain[i-1].event_type)" class="phase-label">
                  <el-tag :type="getPhaseTagType(getEventPhase(ev.event_type))" size="small" effect="dark">
                    <el-icon style="margin-right:2px"><Flag /></el-icon>{{ getEventPhase(ev.event_type) }}
                  </el-tag>
                </div>
                <div class="tl-item">
                  <div class="tl-line"></div>
                  <div class="tl-dot" :style="{background:getRiskColor(ev.risk_level)}"></div>
                  <div class="tl-card" :class="riskCardClass(ev.risk_level)">
                    <div class="tl-card-header">
                      <span v-if="ev.timestamp" class="tl-time">{{ ev.timestamp }}</span>
                      <el-tag size="small" type="info" effect="plain" style="font-size:11px">{{ ev.event_type || '事件' }}</el-tag>
                      <RiskBadge v-if="ev.risk_level" :level="ev.risk_level" size="small" />
                    </div>
                    <div class="tl-body">{{ ev.action }}</div>
                    <div class="tl-meta">
                      <el-icon style="margin-right:2px"><Position /></el-icon>{{ ev.source || '未知源' }}
                      <template v-if="ev.target"> <el-icon style="margin:0 2px"><Right /></el-icon> {{ ev.target }}</template>
                    </div>
                    <div v-if="ev.detail" class="tl-detail">{{ ev.detail }}</div>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- 溯源总结 -->
          <div v-if="linkData?.summary" style="font-size:12px;color:var(--text-secondary);margin-bottom:12px;padding:6px 8px;background:var(--bg-secondary);border-radius:4px">
            <strong>总结：</strong>{{ linkData.summary }}
          </div>

          <!-- 检索脚本（可复制 + 可执行） -->
          <div v-if="linkData?.scripts?.length">
            <div style="font-weight:600;margin-bottom:8px;font-size:13px">
              <el-icon><Tickets /></el-icon> 溯源检索脚本（共 {{ linkData.scripts.length }} 个）
            </div>
            <div v-for="(sc, si) in linkData.scripts" :key="si" style="margin-bottom:14px">
              <div style="font-size:13px;font-weight:500;margin-bottom:2px">{{ sc.name }}</div>
              <div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px">{{ sc.description }}</div>
              <CodeBlock :code="sc.code" :lang="sc.lang" />
              <!-- SPL 脚本的执行按钮 -->
              <div v-if="sc.lang === 'spl'" style="display:flex;gap:8px;margin-top:6px">
                <el-button size="small" type="primary" plain @click="executeSplunkInDialog(sc.code)">
                  <el-icon><VideoPlay /></el-icon> 执行查询
                </el-button>
                <el-button size="small" plain @click="openSplunkInDialog(sc.code)">
                  <el-icon><Link /></el-icon> 在 Splunk 中打开
                </el-button>
              </div>
            </div>
          </div>

          <!-- 弹窗内 Splunk 结果 -->
          <div v-if="dialogSplunkResult" class="g-card" style="margin-top:8px;border:1px solid var(--el-border-color-light)">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
              <span style="font-weight:600;font-size:13px"><el-icon><Monitor /></el-icon> Splunk 查询结果</span>
              <el-button size="small" text @click="dialogSplunkResult=null">关闭</el-button>
            </div>
            <el-table :data="dialogSplunkResult.results" border size="small" max-height="300" style="width:100%">
              <el-table-column v-for="(_, key) in dialogSplunkResult.results[0] || {}" :key="key" :prop="key" :label="key" min-width="100" show-overflow-tooltip />
            </el-table>
            <div style="font-size:11px;color:var(--text-tertiary);margin-top:6px">
              共 {{ dialogSplunkResult.event_count }} 条，耗时 {{ dialogSplunkResult.execution_time }}s
            </div>
          </div>
          </template>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import { getSplunkConfig } from '../../utils/splunk'
import { consumeIncoming } from '../../utils/crossModuleStore'
import AlertGuide from '../../components/AlertGuide.vue'
import RiskBadge from '../../components/RiskBadge.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
import FileUpload from '../../components/FileUpload.vue'
import CodeBlock from '../../components/CodeBlock.vue'

// 时间轴辅助函数（与 Trace.vue 一致）
const EVENT_PHASES: Record<string, string> = {
  port_scan: '侦查探测', brute_force: '初始入侵',
  sql_injection: '权限提升/入侵', webshell: '权限提升/入侵',
  suspicious: '权限提升/入侵', privilege_escalation: '权限提升/入侵',
  lateral_move: '横向移动', persistence: '持久化驻留',
  data_exfil: '数据窃取/破坏', c2: '命令控制', ransomware: '破坏',
}
function getEventPhase(eventType: string): string {
  return EVENT_PHASES[eventType] || (eventType === 'unknown' ? '未知阶段' : '可疑行为')
}
function getPhaseTagType(phase: string): string {
  if (phase.includes('窃取') || phase.includes('破坏')) return 'danger'
  if (phase.includes('横向')) return 'warning'
  if (phase.includes('提升') || phase.includes('入侵')) return 'danger'
  if (phase.includes('初始')) return 'warning'
  if (phase.includes('侦查')) return 'info'
  return 'info'
}
function getRiskColor(level: string): string {
  const key = level?.toLowerCase()
  if (key?.startsWith('p0') || key === 'high' || key === 'critical') return '#f56c6c'
  if (key?.startsWith('p1') || key === 'medium' || key === 'major') return '#e6a23c'
  if (key?.startsWith('p2') || key === 'low' || key === 'warning') return '#909399'
  return '#c0c4cc'
}
function riskCardClass(level: string): string {
  const key = level?.toLowerCase()
  if (key?.startsWith('p0') || key === 'high' || key === 'critical') return 'tl-card--high'
  if (key?.startsWith('p1') || key === 'medium' || key === 'major') return 'tl-card--med'
  return ''
}
function diffLevel(d: string): string {
  return d === '高级' ? 'P0' : d === '中级' ? 'P1' : 'P3'
}

defineProps<{ mode?: string }>()

const input = ref('')
const loading = ref(false)
const result = ref<any>(null)
const showSample = ref(false)
const timeWindow = ref(5)
const useLlm = ref(false)
const fileUploadRef = ref<InstanceType<typeof FileUpload> | null>(null)
const uploadedFilePaths = ref<string[]>([])

// ★ 回流数据
const incomingData = ref<any>(null)

// 联动弹窗
const linkDialogVisible = ref(false)
const linkDialogTitle = ref('')
const linkLoading = ref(false)
const linkResult = ref<any>(null)
const linkData = ref<any>(null)
const dialogSplunkLoading = ref(false)
const dialogSplunkResult = ref<any>(null)
// 场景模式（to-scenario vs to-trace 弹窗区分）
const linkIsScenario = ref(false)
const linkScenarioMessage = ref('')
const scenarioInfo = ref<any>(null)
const scenarioTasks = ref<any[]>([])

const sampleLogs = `2024-01-05 12:34:56 web-server sshd[12345]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2
2024-01-05 12:34:57 web-server sshd[12345]: Failed password for root from 192.168.1.100 port 22 ssh2
2024-01-05 12:34:58 web-server sshd[12345]: Failed password for admin from 192.168.1.100 port 22 ssh2
2024-01-05 12:35:01 web-server sshd[12345]: Accepted password for admin from 192.168.1.100 port 22 ssh2
2024-01-05 12:35:30 web-server sudo: admin : TTY=pts/0 ; PWD=/root ; USER=root ; COMMAND=/bin/cat /etc/shadow
2024-01-05 12:36:00 db-server mysqld[6789]: SELECT * FROM users WHERE username = 'admin' OR '1'='1'`

function fillSample() {
  input.value = sampleLogs
  showSample.value = true
}

// FileUpload 组件回调
function onFilesUpdate(files: any[]) {
  uploadedFilePaths.value = files.map(f => f.path)
}

async function onUploadSuccess(_newFiles: any[]) {
  if (uploadedFilePaths.value.length > 0) {
    loading.value = true
    result.value = null
    try {
      const crunchRes = await Api.logCorrelate.fileCrunch({
        file_paths: uploadedFilePaths.value,
        time_window_minutes: timeWindow.value,
        use_llm: useLlm.value,
      })
      if (crunchRes.success) {
        result.value = crunchRes.data
        ElMessage.success(`已分析 ${uploadedFilePaths.value.length} 个文件`)
      } else {
        ElMessage.error(crunchRes.msg || '分析失败')
      }
    } catch (err: any) {
      ElMessage.error('分析失败: ' + (err.message || '未知错误'))
    } finally {
      loading.value = false
    }
  }
}

function clear() {
  fileUploadRef.value?.clearAll()
  input.value = ''
  result.value = null
  uploadedFilePaths.value = []
  incomingData.value = null
}

function getRiskKey(level: string): string {
  const map: Record<string, string> = {
    'P0_高危': 'P0', 'P1_中危': 'P1', 'P2_低危': 'P2', 'P3_低风险': 'P3',
    'critical': 'P0', 'major': 'P1', 'warning': 'P2',
  }
  return map[level] || 'normal'
}

async function submit() {
  const hasUploadedFiles = uploadedFilePaths.value.length > 0
  const hasTextInput = input.value.trim()

  if (!hasUploadedFiles && !hasTextInput) {
    ElMessage.warning('请输入日志内容或上传文件')
    return
  }

  loading.value = true
  result.value = null

  try {
    let res: any
    if (hasUploadedFiles) {
      res = await Api.logCorrelate.fileCrunch({
        file_paths: uploadedFilePaths.value,
        time_window_minutes: timeWindow.value,
        use_llm: useLlm.value,
      })
    } else {
      const lines = input.value.split('\n').filter(l => l.trim())
      res = await Api.logCorrelate.correlate({
        log_lines: lines,
        time_window_minutes: timeWindow.value,
        use_llm: useLlm.value,
      })
    }

    if (res.success) {
      result.value = res.data
    } else {
      ElMessage.error(res.msg || '分析失败')
    }
  } catch (err: any) {
    ElMessage.error('请求失败: ' + (err.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function retryWithLLM() {
  useLlm.value = true
  await submit()
}

// 联动：生成溯源脚本（★ 升级版：传递预分析结果，避免溯源重复解析）
async function toTraceScript(chain: any) {
  linkDialogVisible.value = true
  linkDialogTitle.value = `生成溯源脚本 — ${chain.chain_name}`
  linkLoading.value = true
  linkResult.value = null
  linkData.value = null
  dialogSplunkResult.value = null
  linkIsScenario.value = false

  try {
    const lines = input.value.split('\n').filter(l => l.trim())
    // 构建预分析数据：传递已有检测结果，避免溯源重复跑正则
    const preAnalyzed: any = {}
    if (chain.matched_keywords?.length) {
      preAnalyzed.matched_keywords = chain.matched_keywords
    }
    if (chain.indicators?.length) {
      preAnalyzed.indicators = chain.indicators
    }
    if (chain.matched_line_indices?.length) {
      preAnalyzed.matched_line_indices = chain.matched_line_indices
    }
    const res = await Api.logCorrelate.toTrace({
      log_lines: lines.slice(0, 100),
      chain_name: chain.chain_name || '',
      attack_type: chain.chain_name || 'unknown',
      pre_analyzed: Object.keys(preAnalyzed).length > 0 ? preAnalyzed : undefined,
    })
    linkResult.value = res
    // 解析出 data 中的溯源信息
    if (res.success && res.data) {
      linkData.value = res.data
    }
  } catch (err: any) {
    linkResult.value = { code: -1, msg: err.message || '请求失败' }
  } finally {
    linkLoading.value = false
  }
}

// 联动：下发实训场景（★ 增强版：传递完整 chain_data 以生成动态场景）
async function toTrainingScenario(chain: any) {
  linkDialogVisible.value = true
  linkDialogTitle.value = `下发实训场景 — ${chain.chain_name}`
  linkLoading.value = true
  linkResult.value = null
  linkData.value = null
  dialogSplunkResult.value = null

  try {
    const lines = input.value.split('\n').filter(l => l.trim())
    const res = await Api.logCorrelate.toScenario({
      log_lines: lines.slice(0, 50),
      chain_name: chain.chain_name || '',
      chain_description: chain.description || '',
      // ★ 传递完整攻击链数据，后端据此用 LLM 生成专属实战场景
      chain_data: {
        chain_name: chain.chain_name,
        description: chain.description,
        risk_level: chain.risk_level,
        confidence: chain.confidence,
        matched_keywords: chain.matched_keywords,
        matched_line_indices: chain.matched_line_indices,
        indicators: chain.indicators,
        suggestion: chain.suggestion,
        temporal: chain.temporal,  // 含 timeline、stages_observed 等
      },
    })
    linkResult.value = res
    // 提取场景数据用于弹窗展示
    linkIsScenario.value = true
    if (res.success && res.data?.scenarios?.[0]) {
      const s = res.data.scenarios[0]
      scenarioInfo.value = s.scenario || {}
      scenarioTasks.value = s.tasks || []
      linkScenarioMessage.value = res.data.message || '实战场景已生成'
    }
  } catch (err: any) {
    linkResult.value = { code: -1, msg: err.message || '请求失败' }
  } finally {
    linkLoading.value = false
  }
}

// 从弹窗导航到实训答题
function startTrainingFromLink() {
  if (scenarioInfo.value && scenarioInfo.value.scenario_id) {
    linkDialogVisible.value = false
    // 复用 Scenarios.vue → Submit.vue 的 sessionStorage 数据传递
    const scenario = {
      scenario: scenarioInfo.value,
      tasks: scenarioTasks.value,
      total_tasks: scenarioTasks.value.length,
      completed_tasks: 0,
    }
    sessionStorage.setItem('current-training-scenario', JSON.stringify(scenario))
    window.location.hash = '#/training/submit'
  } else {
    ElMessage.warning('场景数据异常，无法进入实训')
  }
}

// 弹窗内执行 Splunk 查询
async function executeSplunkInDialog(spl: string) {
  const cfg = getSplunkConfig()
  if (!cfg) { ElMessage.warning('请先在导航栏设置中配置 Splunk'); return }
  dialogSplunkLoading.value = true
  dialogSplunkResult.value = null
  try {
    const r = await Api.scriptGen.splunkSearch({ spl_query: spl, splunk_config: cfg })
    if (r.success) dialogSplunkResult.value = r.data
    else ElMessage.error(r.msg || 'Splunk 查询失败')
  } catch {
    ElMessage.error('Splunk 请求失败')
  } finally {
    dialogSplunkLoading.value = false
  }
}

async function openSplunkInDialog(spl: string) {
  const cfg = getSplunkConfig()
  if (!cfg) { ElMessage.warning('请先配置 Splunk'); return }
  try {
    const r = await Api.scriptGen.splunkOpenUrl({ spl_query: spl, splunk_config: cfg })
    if (r.success && r.data?.open_url) window.open(r.data.open_url, '_blank')
    else ElMessage.error(r.msg || '无法生成 Splunk 链接')
  } catch {
    ElMessage.error('请求失败')
  }
}

// ★ 检查回流数据（组件挂载时自动检查）
function checkIncoming() {
  const data = consumeIncoming()
  if (data && data.logs?.length) {
    incomingData.value = data
    input.value = data.logs.join('\n')
    useLlm.value = true  // 回流分析默认启用 LLM
    showSample.value = false
    // 自动提交分析（延迟一帧确保 UI 渲染完毕）
    ElMessage.info(`收到 ${data.logs.length} 条来自溯源模块的日志，正在自动分析...`)
    setTimeout(() => submit(), 300)
  }
}

onMounted(() => {
  checkIncoming()
})
</script>

<style scoped>
.g-param-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.g-param-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.g-param-item label {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}
.g-param-desc {
  font-size: 12px;
  color: var(--text-tertiary, #86909C);
}
.g-chain-card {
  padding: 12px;
  border: 1px solid var(--border-color, #e5e6eb);
  border-radius: 6px;
  background: var(--bg-primary, #fff);
}
.g-summary {
  font-size: 13px;
}
/* 时间轴样式（与 Trace.vue 一致） */
.timeline { position:relative; padding-left:20px }
.phase-label { position:relative; padding:8px 0 4px; margin-left:-20px }
.tl-item { position:relative; padding:0 0 8px 20px; display:flex }
.tl-line {
  position:absolute; left:9px; top:0; bottom:0; width:2px;
  background:linear-gradient(to bottom,var(--el-border-color-light),var(--el-border-color-darker))
}
.tl-item:last-child .tl-line { display:none }
.tl-dot {
  position:absolute; left:0; top:6px; width:20px; height:20px; border-radius:50%;
  border:3px solid #fff; box-shadow:0 1px 4px rgba(0,0,0,0.15); z-index:1;
  display:flex; align-items:center; justify-content:center; flex-shrink:0
}
.tl-card {
  flex:1; padding:8px 10px; border-radius:6px; border:1px solid var(--el-border-color-light);
  background:var(--el-fill-color-light); transition:border-color .2s
}
.tl-card--high { border-left:3px solid #f56c6c; background:#fef0f0 }
.tl-card--med  { border-left:3px solid #e6a23c; background:#fdf6ec }
.tl-card-header { display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:2px }
.tl-time { font-size:12px; font-weight:600; color:var(--el-text-color-primary); min-width:130px }
.tl-body  { font-size:13px; color:var(--el-text-color-primary); margin:2px 0 }
.tl-meta  { font-size:12px; color:var(--el-text-color-secondary); display:flex; align-items:center; gap:2px; flex-wrap:wrap }
.tl-detail { font-size:11px; color:var(--el-text-color-placeholder); margin-top:2px }
</style>
