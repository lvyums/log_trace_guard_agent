<template>
  <div class="g-stack">
    <!-- 运维模式：简洁专业 -->
    <div v-if="mode === 'ops'">
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Connection /></el-icon> 安全威胁狩猎</div>
            <div class="g-card-desc">输入多源日志，检测攻击链和跨设备关联事件</div>
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
            <input
              ref="fileInputRef"
              type="file"
              accept=".log,.txt,.csv,.json"
              style="display:none"
              @change="onFileSelected"
            />
            <el-button size="small" :disabled="loading" @click="triggerFilePicker">
              <el-icon style="margin-right:4px"><Upload /></el-icon> 上传日志文件
            </el-button>
          </div>
        </div>

        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" :loading="loading" :disabled="!input.trim()" @click="submit">
            <el-icon style="margin-right:4px"><Search /></el-icon> 关联分析
          </el-button>
          <el-button :disabled="loading" @click="clear">清空</el-button>
        </div>
      </div>
    </div>

    <!-- 实训模式：带引导 -->
    <template v-else>
      <AlertGuide type="info" title="安全威胁狩猎 — 发现隐蔽攻击链">
        输入多源日志（每行一条），系统自动进行安全攻击链检测。支持中文/英文日志，内置 16 种攻击链模型，关键词匹配不满 60% 时自动降级 LLM 智能分析。
      </AlertGuide>

      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Connection /></el-icon> 安全威胁狩猎</div>
            <div class="g-card-desc">输入多源日志，自动检测攻击链和关联事件</div>
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
            <input
              ref="fileInputRef"
              type="file"
              accept=".log,.txt,.csv"
              style="display:none"
              @change="onFileSelected"
            />
            <el-button size="small" :disabled="loading" @click="triggerFilePicker">
              <el-icon style="margin-right:4px"><Upload /></el-icon> 上传日志文件
            </el-button>
          </div>
        </div>

        <div class="g-input-guide">
          <el-icon><InfoFilled /></el-icon>
          <span>支持粘贴多条日志，Ctrl+Enter 快速提交。支持上传 .log/.txt 文件。</span>
        </div>

        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" :loading="loading" :disabled="!input.trim()" @click="submit">
            <el-icon style="margin-right:4px"><Search /></el-icon> 关联分析
          </el-button>
          <el-button :disabled="loading" @click="clear">清空</el-button>
        </div>
      </div>
    </template>

    <!-- 分析结果 -->
    <div v-if="result" class="g-card slide">
      <!-- 分析概览 -->
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><DataAnalysis /></el-icon> 分析结果</div>
        <div class="g-actions">
          <el-tag v-if="result.method === 'keyword'" type="success" size="small" effect="dark">关键词匹配</el-tag>
          <el-tag v-else-if="result.method === 'llm'" type="warning" size="small" effect="dark">LLM 分析</el-tag>
          <el-tag v-else-if="result.method === 'hybrid'" type="info" size="small" effect="dark">混合模式</el-tag>
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
            <el-button size="small" type="success" plain @click="toTrainingScenario(chain)">
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
        title="安全威胁狩猎 — 发现隐蔽攻击链"
        desc="输入多源日志（每行一条），系统自动检测安全攻击链。内置 16 种攻击链规则，支持中文/英文日志，关键词匹配不足时自动降级 LLM 智能分析。"
        action-text="加载攻击链样例"
        @action="fillSample"
      />
    </div>

    <!-- 联动结果弹窗 -->
    <el-dialog v-model="linkDialogVisible" :title="linkDialogTitle" width="600px">
      <div v-if="linkLoading" style="text-align:center;padding:30px">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <div style="margin-top:8px">正在处理...</div>
      </div>
      <div v-else-if="linkResult" style="white-space:pre-wrap;font-size:13px;line-height:1.8">
        <div v-if="linkResult.code === 0">
          <div class="g-alert g-alert--success">
            <el-icon><CircleCheck /></el-icon>
            <span>{{ linkResult.msg || linkResult.data?.msg || '操作成功' }}</span>
          </div>
          <div v-if="linkResult.data?.trace_script" style="margin-top:12px">
            <div style="font-weight:600;margin-bottom:6px">生成的脚本：</div>
            <div class="g-code-block">
              <div class="g-code-body" style="max-height:300px">
                <code>{{ linkResult.data.trace_script }}</code>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="g-alert g-alert--warning">
          <el-icon><Warning /></el-icon>
          <span>{{ linkResult.msg || '操作失败' }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import RiskBadge from '../../components/RiskBadge.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'

defineProps<{ mode?: string }>()

const input = ref('')
const loading = ref(false)
const result = ref<any>(null)
const showSample = ref(false)
const timeWindow = ref(5)
const useLlm = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

// 联动弹窗
const linkDialogVisible = ref(false)
const linkDialogTitle = ref('')
const linkLoading = ref(false)
const linkResult = ref<any>(null)

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

function triggerFilePicker() {
  fileInputRef.value?.click()
}

function onFileSelected(event: Event) {
  const el = event.target as HTMLInputElement
  const file = el.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target?.result as string
    if (text) {
      input.value = text
      ElMessage.success(`已读取文件：${file.name}（${file.size} 字节，${text.split('\n').length} 行）`)
    }
    el.value = '' // 重置 input，允许重复选择
  }
  reader.onerror = () => {
    ElMessage.error('文件读取失败')
  }
  reader.readAsText(file)
}

function clear() {
  input.value = ''
  result.value = null
}

function getRiskKey(level: string): string {
  const map: Record<string, string> = {
    'P0_高危': 'P0', 'P1_中危': 'P1', 'P2_低危': 'P2', 'P3_低风险': 'P3',
    'critical': 'P0', 'major': 'P1', 'warning': 'P2',
  }
  return map[level] || 'normal'
}

async function submit() {
  if (!input.value.trim()) {
    ElMessage.warning('请输入日志内容')
    return
  }

  loading.value = true
  result.value = null

  try {
    const lines = input.value.split('\n').filter(l => l.trim())
    const payload: any = {
      log_lines: lines,
      time_window_minutes: timeWindow.value,
      detailed: true,
    }
    if (useLlm.value) {
      payload.use_llm = true
    }
    const res = await Api.logCorrelate.correlate(payload)

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

// 联动：生成溯源脚本
async function toTraceScript(chain: any) {
  linkDialogVisible.value = true
  linkDialogTitle.value = `生成溯源脚本 — ${chain.chain_name}`
  linkLoading.value = true
  linkResult.value = null

  try {
    const lines = input.value.split('\n').filter(l => l.trim())
    const res = await Api.logCorrelate.toTrace({
      log_lines: lines.slice(0, 100),
      chain_name: chain.chain_name || '',
      attack_type: chain.chain_name || 'unknown',
    })
    linkResult.value = res
  } catch (err: any) {
    linkResult.value = { code: -1, msg: err.message || '请求失败' }
  } finally {
    linkLoading.value = false
  }
}

// 联动：下发实训场景
async function toTrainingScenario(chain: any) {
  linkDialogVisible.value = true
  linkDialogTitle.value = `下发实训场景 — ${chain.chain_name}`
  linkLoading.value = true
  linkResult.value = null

  try {
    const lines = input.value.split('\n').filter(l => l.trim())
    const res = await Api.logCorrelate.toScenario({
      log_lines: lines.slice(0, 10),
      chain_name: chain.chain_name || '',
      chain_description: chain.description || '',
    })
    linkResult.value = res
  } catch (err: any) {
    linkResult.value = { code: -1, msg: err.message || '请求失败' }
  } finally {
    linkLoading.value = false
  }
}
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
</style>
