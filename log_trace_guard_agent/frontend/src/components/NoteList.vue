<template>
  <div v-for="(note, i) in items" :key="i" class="g-note-item">
    {{ note }}
  </div>
</template>

<script setup lang="ts">
defineProps<{ items: string[] }>()
</script>

<style scoped>
.g-note-item {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  padding-left: 12px;
  border-left: 2px solid var(--el-color-warning);
}
</style>
