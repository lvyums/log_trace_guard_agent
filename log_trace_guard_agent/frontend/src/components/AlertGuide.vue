<template>
  <div v-if="visible" class="g-alert" :class="'g-alert--' + type">
    <el-icon><component :is="icon" /></el-icon>
    <div style="flex:1">
      <div v-if="title" style="font-weight:600;margin-bottom:2px">{{ title }}</div>
      <slot />
    </div>
    <el-icon
      v-if="closable" style="cursor:pointer;flex-shrink:0"
      @click="visible = false; $emit('close')"
    ><Close /></el-icon>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = withDefaults(defineProps<{
  type?: string
  title?: string
  closable?: boolean
}>(), { type: 'info', closable: true })

const emit = defineEmits<{ close: [] }>()
const visible = ref(true)

const icon = computed(() => {
  const map: Record<string, string> = {
    info: 'InfoFilled', warning: 'WarningFilled',
    danger: 'CircleCloseFilled', success: 'CircleCheckFilled',
  }
  return map[props.type] || 'InfoFilled'
})
</script>