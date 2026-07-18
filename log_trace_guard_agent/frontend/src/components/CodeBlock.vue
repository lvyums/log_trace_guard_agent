<template>
  <div class="g-code-block" :style="customStyle">
    <div v-if="label" class="g-code-header">
      <span>{{ label }}</span>
      <el-button size="small" text @click="copy">复制</el-button>
    </div>
    <div class="g-code-body" :style="{ maxHeight: maxHeight }">
      <pre><code :class="lang ? 'language-' + lang : ''">{{ code }}</code></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Utils } from '../utils'

const props = withDefaults(defineProps<{
  code?: string
  lang?: string
  label?: string
  maxHeight?: string
}>(), { maxHeight: '400px' })

const customStyle = computed(() => ({} as Record<string, string>))

function copy() {
  if (props.code) {
    Utils.copyText(props.code)
    ElMessage.success('已复制')
  }
}
</script>