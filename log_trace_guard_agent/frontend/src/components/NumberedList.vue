<template>
  <div v-for="(item, i) in items" :key="i" class="g-numbered-item">
    <div class="g-numbered-circle">{{ i + 1 }}</div>
    <div class="g-numbered-text">{{ item }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ items: string[] }>()
</script>

<style scoped>
.g-numbered-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}
.g-numbered-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}
.g-numbered-text {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
