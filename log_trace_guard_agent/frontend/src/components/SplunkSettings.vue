<template>
  <el-dialog title="系统设置" width="520px" :model-value="visible" @update:model-value="$emit('update:visible', $event)" destroy-on-close>
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
            <el-input v-model="splunkForm.base_url" placeholder="如 https://splunk.example.com" />
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
    </el-tabs>

    <template #footer>
      <el-button v-if="activeTab === 'splunk'" @click="testConnection" :loading="testing">测试连接</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../api'
import { loadSplunkConfig, saveSplunkConfig, loadAiConfig, saveAiConfig } from '../utils/splunk'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [v: boolean] }>()

const activeTab = ref('ai')
const testing = ref(false)
const aiForm = ref(loadAiConfig())
const splunkForm = ref(loadSplunkDefaults())

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
  }
})

function save() {
  if (activeTab.value === 'ai') {
    if (!aiForm.value.api_key.trim()) { ElMessage.warning('请输入 API Key'); return }
    saveAiConfig(aiForm.value)
    ElMessage.success('AI 配置已保存')
  } else {
    if (!splunkForm.value.base_url.trim()) { ElMessage.warning('请输入 Splunk URL'); return }
    saveSplunkConfig(splunkForm.value)
    ElMessage.success('Splunk 配置已保存')
  }
  emit('update:visible', false)
}

async function testConnection() {
  if (!splunkForm.value.base_url.trim()) { ElMessage.warning('请先填写 Splunk URL'); return }
  testing.value = true
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
  finally { testing.value = false }
}
</script>
