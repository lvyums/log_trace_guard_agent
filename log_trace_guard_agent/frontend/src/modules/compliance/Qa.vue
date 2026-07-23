<template>
  <div class="g-stack">
    <AlertGuide type="info" title="合规问答基于最新法规标准">
      知识库涵盖：等保2.0(GB/T 22239-2019)、网安法、数据安全法、行业规范。问题越具体，回答越精准。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><ChatDotRound /></el-icon> 合规问答</div>
          <div class="g-card-desc">关于等保2.0、网安法、数据安全法等合规问题的智能解答</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
      </div>
      <div style="display:flex;gap:8px">
        <el-input v-model="question" placeholder="输入合规相关问题..." :disabled="loading" @keyup.enter="submit" style="flex:1" />
        <el-button type="primary" @click="submit" :loading="loading">提问</el-button>
      </div>
      <div class="g-input-guide"><el-icon><InfoFilled /></el-icon><span>支持等保2.0、网安法、数据安全法、行业合规标准等问题</span></div>
    </div>
    <div v-if="history.length" style="display:flex;flex-direction:column;gap:12px">
      <div v-for="(item,i) in history" :key="i" class="g-card slide">
        <div style="margin-bottom:12px"><div style="font-size:12px;color:var(--text-tertiary);margin-bottom:4px">问题</div><div style="font-size:13px;color:var(--text-primary)">{{ item.q }}</div></div>
        <div class="g-divider" style="margin:8px 0"></div>
        <div>
          <div style="font-size:12px;color:var(--text-tertiary);margin-bottom:4px">回答</div>
          <div style="font-size:13px;color:var(--text-secondary);line-height:1.8;white-space:pre-wrap">{{ typeof item.a === 'string' ? item.a : JSON.stringify(item.a,null,2) }}</div>
        </div>

        <!-- 匹配标准引用 -->
        <div v-if="item._raw?.standards?.length" style="margin-top:12px">
          <div style="font-weight:600;margin-bottom:6px;font-size:12px;color:var(--text-secondary)">相关标准条目（{{ item._raw.matched_count || item._raw.standards.length }}条匹配）</div>
          <div v-for="(std, si) in item._raw.standards" :key="si" style="padding:6px 10px;margin-bottom:4px;border:1px solid var(--border-color);border-radius:4px;font-size:12px;background:var(--bg-secondary)">
            <div style="font-weight:500;margin-bottom:2px">{{ std.standard_name || '标准' }}</div>
            <div v-for="(it, ti) in (std.items||[])" :key="ti" style="color:var(--text-secondary);padding-left:8px;border-left:2px solid var(--el-color-primary);margin-top:4px">
              <strong>{{ it.item_id || '' }}</strong> {{ it.requirement || it.content || '' }}
            </div>
          </div>
        </div>

        <!-- 补充检索 -->
        <div v-if="item._raw?.rag_supplements?.length" style="margin-top:10px">
          <div style="font-weight:600;margin-bottom:6px;font-size:12px;color:var(--text-secondary)">知识库补充（{{ item._raw.rag_supplements.length }}条）</div>
          <div v-for="(rs, ri) in item._raw.rag_supplements" :key="ri" style="padding:6px 10px;margin-bottom:4px;border:1px solid var(--border-color);border-radius:4px;font-size:12px;background:var(--bg-secondary)">
            <div style="color:var(--text-secondary)">{{ rs.document?.slice(0,200) }}</div>
            <div v-if="rs.score" style="margin-top:2px;color:var(--text-tertiary)">匹配度: {{ (rs.score*100).toFixed(0) }}%</div>
          </div>
        </div>

        <!-- LLM深度解读 -->
        <div v-if="item._raw?.llm_answer" style="margin-top:10px">
          <div style="font-weight:600;margin-bottom:4px;font-size:12px;color:var(--el-color-primary)">AI深度解读</div>
          <div style="padding:8px 12px;background:var(--bg-secondary);border-radius:4px;font-size:13px;line-height:1.8;white-space:pre-wrap;color:var(--text-secondary)">{{ item._raw.llm_answer }}</div>
        </div>

        <!-- 备注 -->
        <div v-if="item._raw?.note" style="margin-top:8px;font-size:12px;color:var(--text-tertiary);font-style:italic">
          {{ item._raw.note }}
        </div>
      </div>
    </div>
    <div v-if="!history.length && !loading" class="g-card">
      <EmptyGuide title="暂无问答记录" desc="输入合规相关问题开始咨询" action-text="查看示例问题" @action="fillSample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
defineProps<{ mode?: string }>()
const question=ref(''); const loading=ref(false); const history=ref<any[]>([])
function fillSample(){question.value='等保2.0三级对日志留存有什么要求？'}
async function submit(){
  if(!question.value.trim()){ElMessage.warning('请输入问题');return}
  loading.value=true
  try{
    const r=await Api.compliance.qa({question:question.value})
    if(r.success){
      history.value.push({q:question.value,a:r.data.answer||r.data,_raw:r.data})
    }else ElMessage.error(r.msg)
  }catch{ElMessage.error('请求失败')}
  finally{loading.value=false;question.value=''}
}
</script>
