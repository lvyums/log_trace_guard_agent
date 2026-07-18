<template>
  <div class="g-empty">
    <el-icon class="g-empty-icon"><component :is="icon" /></el-icon>
    <div class="g-empty-title">{{ title }}</div>
    <div class="g-empty-desc">{{ desc }}</div>
    <el-button v-if="actionText" type="primary" @click="$emit('action')">
      {{ actionText }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  desc?: string
  actionText?: string
  icon?: string
}>(), { title: '暂无数据', desc: '请进行相关操作', icon: 'Inbox' })

defineEmits<{ action: [] }>()
</script>