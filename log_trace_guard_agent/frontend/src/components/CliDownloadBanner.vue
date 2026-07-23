<template>
  <div v-if="visible" class="cli-banner">
    <el-icon><Monitor /></el-icon>
    <span class="cli-banner-text">
      <strong>命令行版本已发布</strong> — 支持本地日志批量分析、脚本生成、合规审计等更多功能
    </span>
    <a
      href="https://github.com/lvyums/log_trace_guard_agent/releases/latest"
      target="_blank"
      rel="noopener"
      class="cli-banner-btn"
    >
      <el-icon><Download /></el-icon>
      下载 CLI
    </a>
    <el-icon class="cli-banner-close" @click="close"><Close /></el-icon>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Monitor, Download, Close } from '@element-plus/icons-vue'

const STORAGE_KEY = 'cli-banner-closed'
const visible = ref(false)

onMounted(() => {
  visible.value = !localStorage.getItem(STORAGE_KEY)
})

function close() {
  visible.value = false
  localStorage.setItem(STORAGE_KEY, '1')
}
</script>

<style scoped>
.cli-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  background: linear-gradient(135deg, #e8f4fd 0%, #d6e8fa 100%);
  border-bottom: 1px solid #b3d8f0;
  font-size: 13px;
  color: #1a1a1a;
  flex-shrink: 0;
}

:root.dark .cli-banner {
  background: linear-gradient(135deg, #1a2a3a 0%, #1e3348 100%);
  border-bottom-color: #2a4a6a;
  color: #d0d8e0;
}

.cli-banner-text {
  flex: 1;
}

.cli-banner-text strong {
  color: #165dff;
}

:root.dark .cli-banner-text strong {
  color: #4e9aff;
}

.cli-banner-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 12px;
  border-radius: 4px;
  background: #165dff;
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.2s;
  white-space: nowrap;
}

.cli-banner-btn:hover {
  background: #0e42d2;
}

.cli-banner-close {
  cursor: pointer;
  opacity: 0.5;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.cli-banner-close:hover {
  opacity: 1;
}
</style>
