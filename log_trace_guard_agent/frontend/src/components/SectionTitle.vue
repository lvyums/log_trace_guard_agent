<template>
  <div class="g-section-title" :style="{ marginBottom: mb }">
    <el-icon v-if="icon" :style="{ marginRight: '6px' }"><component :is="icon" /></el-icon>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon?: any
  mb?: string
}>()
</script>

<style scoped>
.g-section-title {
  font-weight: 600;
  font-size: 13px;
  display: flex;
  align-items: center;
}
</style>
