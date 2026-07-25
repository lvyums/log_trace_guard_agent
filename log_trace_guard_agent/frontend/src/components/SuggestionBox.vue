<template>
  <div class="g-suggestion-box">
    <div v-if="title" class="g-suggestion-title">{{ title }}</div>
    <div class="g-suggestion-content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
}>()
</script>

<style scoped>
.g-suggestion-box {
  margin-top: 8px;
  padding: 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
}
.g-suggestion-title {
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
}
.g-suggestion-content {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
