<template>
  <div v-if="content" class="g-result-guide">
    <div class="g-result-guide-header" @click="open = !open">
      <el-icon><InfoFilled /></el-icon>
      <span style="font-weight:500;font-size:13px">结果解读</span>
      <el-icon
        style="margin-left:auto;transition:transform 0.2s"
        :style="{ transform: open ? 'rotate(90deg)' : '' }"
      ><ArrowRight /></el-icon>
    </div>
    <div v-show="open" class="g-result-guide-body">
      <div style="font-size:13px;color:var(--text-secondary);line-height:1.8">{{ content }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ content?: string }>()
const open = ref(true)
</script>