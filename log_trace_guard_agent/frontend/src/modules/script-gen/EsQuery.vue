<template>
  <div class="g-stack">
    <AlertGuide type="info" title="ES查询用于安全事件检索">
      生成的DSL可直接在Kibana Dev Tools中执行。大规模检索时使用scroll API避免超时。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Search /></el-icon> ES 查询生成</div>
          <div class="g-card-desc">用自然语言描述查询需求，自动生成 Elasticsearch 查询语句</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
      </div>
      <el-input v-model="description" type="textarea" :rows="3" placeholder="用自然语言描述你要查询的内容..." :disabled="loading" />
      <div class="g-input-guide"><el-icon><InfoFilled /></el-icon><span>描述越详细生成越精准，可包含：时间范围、字段条件、排序方式</span></div>
      <el-input v-model="indexPattern" placeholder="索引模式（可选）：如 logstash-*" style="margin-top:12px" :disabled="loading" />
      <div class="g-actions" style="margin-top:12px">
        <el-button type="primary" @click="submit" :loading="loading">生成查询</el-button>
        <el-tooltip :disabled="hasEsConfig" content="请先在系统设置中配置 ES 连接" placement="top">
          <el-button :disabled="!hasEsConfig || !result" @click="executeQuery" :loading="executing">执行查询</el-button>
        </el-tooltip>
      </div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-title" style="margin-bottom:12px"><el-icon><Monitor /></el-icon> ES 查询语句</div>
      <CodeBlock :code="result.query" lang="json" />
    </div>
    <!-- ES 执行结果 -->
    <div v-if="esResult" class="g-card" style="margin-top:12px;border:1px solid var(--el-border-color-light)">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
        <div style="font-weight:600;font-size:13px"><el-icon><Monitor /></el-icon> ES 查询结果</div>
        <el-button size="small" text @click="esResult=null">关闭</el-button>
      </div>
      <el-table :data="esResult.results" border size="small" max-height="400" style="width:100%">
        <el-table-column prop="_index" label="索引" min-width="120" show-overflow-tooltip />
        <el-table-column label="内容" min-width="300">
          <template #default="{ row }">
            <span style="font-family:monospace;font-size:12px">{{ formatSource(row.source) }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div style="font-size:12px;color:var(--text-tertiary);margin-top:8px">
        共 {{ esResult.total }} 条匹配，耗时 {{ esResult.took }}ms
      </div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="描述查询需求" desc="用自然语言描述查询条件，AI生成ES查询DSL" action-text="填充示例" @action="fillSample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import { getEsConfig } from '../../utils/splunk'
import AlertGuide from '../../components/AlertGuide.vue'
import CodeBlock from '../../components/CodeBlock.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
defineProps<{ mode?: string }>()
const description=ref(''); const indexPattern=ref(''); const loading=ref(false); const result=ref<any>(null)
const executing=ref(false); const esResult=ref<any>(null)
const hasEsConfig = computed(() => !!getEsConfig())
function fillSample(){description.value='查询最近1小时内来源IP为192.168.1.x网段的SSH登录失败事件，按时间倒序，返回前50条';indexPattern.value='logstash-ssh-*'}
async function submit(){
  if(!description.value.trim()){ElMessage.warning('请描述查询需求');return}
  loading.value=true;result.value=null;esResult.value=null
  try{const r=await Api.scriptGen.esQuery({search_scenario:description.value,index_pattern:indexPattern.value,time_range:'',filters:{}});if(r.success)result.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
async function executeQuery(){
  if(!result.value?.query){ElMessage.warning('请先生成查询语句');return}
  const cfg=getEsConfig();if(!cfg){ElMessage.warning('请先在系统设置中配置 ES 连接');return}
  executing.value=true;esResult.value=null
  try{
    const r=await Api.scriptGen.esSearch({query_dsl:result.value.query,index_pattern:indexPattern.value||undefined,es_config:cfg})
    if(r.success)esResult.value=r.data;else ElMessage.error(r.msg||'ES 查询失败')
  }catch{ElMessage.error('ES 请求失败')}
  finally{executing.value=false}
}
function formatSource(src: any): string {
  if (!src) return ''
  if (typeof src === 'string') return src
  try { return JSON.stringify(src) } catch { return String(src) }
}
</script>
