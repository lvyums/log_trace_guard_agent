<template>
  <div class="g-stack">
    <AlertGuide type="info" title="日志联合审查 — 发现隐蔽攻击链">
      输入多源日志（每行一条），系统自动构建统一时间线、按实体进行关联分析，检测已知攻击链模式。
      支持SSH、Web、防火墙、数据库等多种日志类型混合输入。
    </AlertGuide>

    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Connection /></el-icon> 关联分析</div>
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
          <span>示例：SSH暴力破解攻击链</span>
        </div>
        <div class="g-code-block" style="font-size:12px">
          <div class="g-code-body" style="max-height:120px">
            <code>{{ sampleLogs }}</code>
          </div>
        </div>
      </div>

      <el-input
        v-model="input" type="textarea" :rows="8"
        placeholder="在此粘贴日志内容，每行一条日志..." class="log-input-area"
        :disabled="loading"
        @keyup.ctrl.enter="submit" @keyup.meta.enter="submit"
      />

      <div class="g-param-row" style="margin-top:12px">
        <div class="g-param-item">
          <label>时间窗口（分钟）</label>
          <el-input-number v-model="timeWindow" :min="1" :max="1440" size="small" style="width:120px" />
          <span class="g-param-desc">事件关联的最大时间跨度</span>
        </div>
      </div>

      <div class="g-input-guide">
        <el-icon><InfoFilled /></el-icon>
        <span>支持粘贴多条日志，Ctrl+Enter 快速提交。最大支持500行。</span>
      </div>

      <div class="g-actions" style="margin-top:12px">
        <el-button type="primary" :loading="loading" :disabled="!input.trim()" @click="submit">
          <el-icon style="margin-right:4px"><Search /></el-icon> 关联分析
        </el-button>
        <el-button :disabled="loading" @click="clear">清空</el-button>
      </div>
    </div>

    <!-- 分析结果 -->
    <div v-if="result" class="g-card slide">
      <!-- 分析概览 -->
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><DataAnalysis /></el-icon> 分析结果</div>
      </div>

      <el-descriptions :column="3" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="总事件数">{{ result.total_events }}</el-descriptions-item>
        <el-descriptions-item label="设备类型">{{ result.device_types?.join(', ') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="关联实体数">{{ result.entities?.length || 0 }}</el-descriptions-item>
      </el-descriptions>

      <div class="g-summary" style="margin-bottom:16px">
        <el-alert :title="result.summary" type="info" :closable="false" show-icon />
      </div>

      <!-- 攻击链列表 -->
      <div v-if="result.chains?.length" style="margin-top:16px">
        <div style="font-weight:600;margin-bottom:12px;font-size:14px">
          <el-icon><WarningFilled /></el-icon> 检测到 {{ result.chains.length }} 条攻击链
        </div>

        <div v-for="(chain, idx) in result.chains" :key="idx" class="g-chain-card" style="margin-bottom:12px">
          <div class="g-chain-header" style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            <RiskBadge :level="getRiskKey(chain.risk_level)" :label="chain.risk_level" />
            <strong>{{ chain.chain_name }}</strong>
            <el-tag size="small" type="info">置信度: {{ Math.round(chain.confidence * 100) }}%</el-tag>
            <el-tag size="small" type="info">事件数: {{ chain.event_count }}</el-tag>
          </div>
          <div style="font-size:13px;color:var(--text-secondary);margin-bottom:6px">
            {{ chain.description }}
          </div>
          <div v-if="chain.matched_stages?.length" style="margin-bottom:6px">
            <span style="font-size:12px;color:var(--text-tertiary)">匹配阶段：</span>
            <el-tag v-for="(stage, si) in chain.matched_stages" :key="si" size="small" style="margin-right:4px;margin-bottom:4px">
              {{ stage }}
            </el-tag>
          </div>
          <div v-if="chain.indicators?.length" style="margin-bottom:6px">
            <span style="font-size:12px;color:var(--text-tertiary)">指标：</span>
            <span v-for="(ind, ii) in chain.indicators" :key="ii" style="font-size:12px;color:var(--color-danger);margin-right:8px">
              {{ ind }}
            </span>
          </div>
          <div v-if="chain.suggestion" style="margin-top:4px;padding:6px 8px;background:var(--bg-secondary);border-radius:4px;font-size:12px">
            <el-icon><Tickets /></el-icon> 建议：{{ chain.suggestion }}
          </div>
          <div style="margin-top:6px">
            <el-button size="small" text @click="toggleChainDetail(idx)">
              {{ expandedChains.includes(idx) ? '收起详情' : '查看事件详情' }}
            </el-button>
          </div>
          <div v-if="expandedChains.includes(idx) && chain.events?.length" style="margin-top:8px">
            <div v-for="(evt, ei) in chain.events" :key="ei" class="g-event-item" style="padding:4px 0;font-size:12px;border-bottom:1px solid var(--border-color);">
              <el-descriptions :column="2" size="mini" border>
                <el-descriptions-item label="时间">{{ evt.timestamp || '-' }}</el-descriptions-item>
                <el-descriptions-item label="设备">{{ evt.device_type }}</el-descriptions-item>
                <el-descriptions-item label="源IP">{{ evt.src_ip || '-' }}</el-descriptions-item>
                <el-descriptions-item label="目标IP">{{ evt.dst_ip || '-' }}</el-descriptions-item>
                <el-descriptions-item label="用户">{{ evt.user || '-' }}</el-descriptions-item>
                <el-descriptions-item label="状态">{{ evt.status || '-' }}</el-descriptions-item>
                <el-descriptions-item label="原始日志" :span="2">
                  <code style="word-break:break-all;font-size:11px">{{ evt.raw_log }}</code>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </div>
        </div>
      </div>

      <!-- 无攻击链 -->
      <div v-else class="g-alert g-alert--success" style="margin-top:12px">
        <el-icon><CircleCheck /></el-icon>
        <span>未检测到已知攻击链模式</span>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide
        title="日志联合审查 — 发现隐蔽攻击链"
        desc="输入多源日志（每行一条），系统自动构建时间线、进行实体关联、检测已知攻击链模式。"
        action-text="加载攻击链样例"
        @action="fillSample"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { APP_CONFIG, getRiskLevel } from '../../config'
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
const expandedChains = ref<number[]>([])

const sampleLogs = `<22>Jan  5 12:34:56 web-server sshd[12345]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2
<22>Jan  5 12:34:57 web-server sshd[12345]: Failed password for root from 192.168.1.100 port 22 ssh2
<22>Jan  5 12:34:58 web-server sshd[12345]: Failed password for admin from 192.168.1.100 port 22 ssh2
<22>Jan  5 12:35:01 web-server sshd[12345]: Accepted password for admin from 192.168.1.100 port 22 ssh2
<22>Jan  5 12:35:30 web-server sudo: admin : TTY=pts/0 ; PWD=/root ; USER=root ; COMMAND=/bin/cat /etc/shadow
<22>Jan  5 12:36:00 db-server mysqld[6789]: 2024-01-05 12:36:00  SELECT * FROM users WHERE username = 'admin' OR '1'='1'`

function fillSample() {
  input.value = sampleLogs
  showSample.value = true
}

function clear() {
  input.value = ''
  result.value = null
  expandedChains.value = []
}

function toggleChainDetail(idx: number) {
  const pos = expandedChains.value.indexOf(idx)
  if (pos >= 0) {
    expandedChains.value.splice(pos, 1)
  } else {
    expandedChains.value.push(idx)
  }
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
  expandedChains.value = []

  try {
    const lines = input.value.split('\n').filter(l => l.trim())
    const res = await Api.logCorrelate.correlate({
      log_lines: lines,
      time_window_minutes: timeWindow.value,
      detailed: true,
    })

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
.g-event-item + .g-event-item {
  margin-top: 8px;
}
.g-summary {
  font-size: 13px;
}
</style>