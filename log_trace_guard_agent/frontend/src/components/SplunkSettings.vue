<template>
  <el-dialog title="系统设置" width="540px" :model-value="visible" @update:model-value="$emit('update:visible', $event)" destroy-on-close>
    <el-tabs v-model="activeTab">
      <!-- AI 设置 -->
      <el-tab-pane label="AI 模型" name="ai">
        <el-form label-position="top" size="default">
          <el-form-item label="API Key">
            <el-input v-model="aiForm.api_key" placeholder="AI 模型 API Key" show-password />
          </el-form-item>
          <el-form-item label="Base URL">
            <el-input v-model="aiForm.base_url" placeholder="如 https://raytoken.com.cn/v1" />
          </el-form-item>
          <el-form-item label="模型名称">
            <el-input v-model="aiForm.model_name" placeholder="如 deepseek-v4-flash" />
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- Splunk 设置 -->
      <el-tab-pane label="Splunk" name="splunk">
        <el-form label-position="top" size="default">
          <el-form-item label="Splunk URL">
            <el-input v-model="splunkForm.base_url" placeholder="如 https://splunk.example.com:8089" />
          </el-form-item>
          <el-form-item label="认证方式">
            <el-radio-group v-model="splunkForm.auth_mode">
              <el-radio value="token">Token</el-radio>
              <el-radio value="basic">用户名密码</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="splunkForm.auth_mode === 'token'" label="Auth Token">
            <el-input v-model="splunkForm.auth_token" placeholder="Splunk Bearer Token" show-password />
          </el-form-item>
          <template v-if="splunkForm.auth_mode === 'basic'">
            <el-form-item label="用户名">
              <el-input v-model="splunkForm.username" placeholder="用户名" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="splunkForm.password" placeholder="密码" show-password />
            </el-form-item>
          </template>
          <el-form-item label="最大返回条数">
            <el-input-number v-model="splunkForm.max_results" :min="1" :max="1000" />
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="splunkForm.verify_ssl">验证 SSL 证书</el-checkbox>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- ES 设置 -->
      <el-tab-pane label="Elasticsearch" name="es">
        <el-form label-position="top" size="default">
          <el-form-item label="ES URL">
            <el-input v-model="esForm.base_url" placeholder="如 http://localhost:9200" />
          </el-form-item>
          <el-form-item label="用户名（可选）">
            <el-input v-model="esForm.username" placeholder="如 elastic" />
          </el-form-item>
          <el-form-item label="密码（可选）">
            <el-input v-model="esForm.password" placeholder="密码" show-password />
          </el-form-item>
          <el-form-item label="最大返回条数">
            <el-input-number v-model="esForm.max_results" :min="1" :max="10000" />
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="esForm.verify_ssl">验证 SSL 证书</el-checkbox>
          </el-form-item>
          <el-divider />
          <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px">
            <template #title>
              保存到 .env 后重启后端服务即可永久生效。若不清除，每次请求自动携带当前配置。
            </template>
          </el-alert>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <template v-if="activeTab === 'splunk'">
        <el-button @click="testSplunkConnection" :loading="testingSplunk">测试连接</el-button>
        <el-button @click="saveSplunk">临时保存</el-button>
        <el-button type="primary" @click="saveSplunkToEnv" :loading="savingEnv">保存到 .env</el-button>
      </template>
      <template v-else-if="activeTab === 'es'">
        <el-button @click="testEsConnection" :loading="testingEs">测试连接</el-button>
        <el-button @click="saveEsToLocal">临时保存</el-button>
        <el-button type="primary" @click="saveEsToEnv">保存到 .env</el-button>
      </template>
      <template v-else>
        <el-button type="primary" @click="saveAi">保存</el-button>
      </template>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../api'
import {
  loadSplunkConfig, saveSplunkConfig,
  loadAiConfig, saveAiConfig,
  loadEsConfig, saveEsConfig, esConfigDefaults,
} from '../utils/splunk'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [v: boolean] }>()

const activeTab = ref('ai')
const testingSplunk = ref(false)
const testingEs = ref(false)
const savingEnv = ref(false)

const aiForm = ref(loadAiConfig())
const splunkForm = ref(loadSplunkDefaults())
const esForm = ref(loadEsConfig())

function loadSplunkDefaults() {
  return { ...splunkDefaults(), ...((loadSplunkConfig() as any) || {}) }
}

function splunkDefaults() {
  return {
    base_url: '',
    auth_mode: 'token' as 'token' | 'basic',
    auth_token: '',
    username: '',
    password: '',
    verify_ssl: true,
    max_results: 100,
  }
}

watch(() => props.visible, (v) => {
  if (v) {
    aiForm.value = loadAiConfig()
    splunkForm.value = loadSplunkDefaults()
    esForm.value = loadEsConfig()
  }
})

function saveAi() {
  if (!aiForm.value.api_key.trim()) { ElMessage.warning('请输入 API Key'); return }
  saveAiConfig(aiForm.value)
  ElMessage.success('AI 配置已保存')
  emit('update:visible', false)
}

function saveSplunk() {
  if (!splunkForm.value.base_url.trim()) { ElMessage.warning('请输入 Splunk URL'); return }
  saveSplunkConfig(splunkForm.value)
  ElMessage.success('Splunk 配置已保存到本地')
}

async function saveSplunkToEnv() {
  if (!splunkForm.value.base_url.trim()) { ElMessage.warning('请输入 Splunk URL'); return }
  savingEnv.value = true
  try {
    const r = await Api.scriptGen.splunkSaveConfig({
      splunk_base_url: splunkForm.value.base_url,
      splunk_auth_token: splunkForm.value.auth_mode === 'token' ? splunkForm.value.auth_token || '' : '',
      splunk_username: splunkForm.value.auth_mode === 'basic' ? splunkForm.value.username || '' : '',
      splunk_password: splunkForm.value.auth_mode === 'basic' ? splunkForm.value.password || '' : '',
      splunk_verify_ssl: splunkForm.value.verify_ssl,
      splunk_max_results: splunkForm.value.max_results,
    })
    if (r.success) {
      ElMessage.success((r.data as any)?.message || 'Splunk 配置已保存到 .env')
      // 同时写入 localStorage 作为临时配置
      saveSplunkConfig(splunkForm.value)
    } else {
      ElMessage.error(r.msg || '保存失败')
    }
  } catch { ElMessage.error('请求失败') }
  finally { savingEnv.value = false }
}

async function testSplunkConnection() {
  if (!splunkForm.value.base_url.trim()) { ElMessage.warning('请先填写 Splunk URL'); return }
  testingSplunk.value = true
  try {
    const r = await Api.scriptGen.splunkTest({
      spl_query: 'search index=_internal | head 1',
      splunk_config: {
        base_url: splunkForm.value.base_url,
        auth_token: splunkForm.value.auth_mode === 'token' ? splunkForm.value.auth_token : undefined,
        username: splunkForm.value.auth_mode === 'basic' ? splunkForm.value.username : undefined,
        password: splunkForm.value.auth_mode === 'basic' ? splunkForm.value.password : undefined,
        verify_ssl: splunkForm.value.verify_ssl,
      },
    })
    if (r.success) ElMessage.success('连接成功')
    else ElMessage.error(r.msg || '连接失败')
  } catch { ElMessage.error('请求失败') }
  finally { testingSplunk.value = false }
}

function saveEsToLocal() {
  if (!esForm.value.base_url.trim()) { ElMessage.warning('请输入 ES URL'); return }
  saveEsConfig(esForm.value)
  ElMessage.success('ES 配置已保存到本地，关闭对话框后仍然有效')
}

async function testEsConnection() {
  if (!esForm.value.base_url.trim()) { ElMessage.warning('请先填写 ES URL'); return }
  testingEs.value = true
  try {
    const r = await Api.scriptGen.esTest({
      query_dsl: '',
      es_config: {
        base_url: esForm.value.base_url,
        username: esForm.value.username || undefined,
        password: esForm.value.password || undefined,
        verify_ssl: esForm.value.verify_ssl,
      },
    })
    if (r.success) {
      const d = r.data as any
      ElMessage.success(`连接成功 — 集群: ${d.cluster_name || 'N/A'}, 版本: ${d.version || 'N/A'}`)
    } else {
      ElMessage.error(r.msg || '连接失败')
    }
  } catch { ElMessage.error('请求失败') }
  finally { testingEs.value = false }
}

async function saveEsToEnv() {
  if (!esForm.value.base_url.trim()) { ElMessage.warning('请输入 ES URL'); return }
  savingEnv.value = true
  try {
    const r = await Api.scriptGen.esSaveConfig({
      es_base_url: esForm.value.base_url,
      es_username: esForm.value.username || '',
      es_password: esForm.value.password || '',
      es_verify_ssl: esForm.value.verify_ssl,
      es_max_results: esForm.value.max_results,
    })
    if (r.success) {
      ElMessage.success((r.data as any)?.message || 'ES 配置已保存到 .env')
      // 同时写入 localStorage 作为临时配置
      saveEsConfig(esForm.value)
    } else {
      ElMessage.error(r.msg || '保存失败')
    }
  } catch { ElMessage.error('请求失败') }
  finally { savingEnv.value = false }
}
</script>
