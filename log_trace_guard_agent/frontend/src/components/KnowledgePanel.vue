<template>
  <div class="g-knowledge-panel">
    <div class="g-knowledge-header" :class="{ 'is-open': open }" @click="open = !open">
      <el-icon><DArrowRight /></el-icon>
      <span>{{ title }}</span>
    </div>
    <div v-show="open" class="g-knowledge-body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

withDefaults(defineProps<{ title?: string }>(), { title: '知识点详解' })
const open = ref(false)
</script>