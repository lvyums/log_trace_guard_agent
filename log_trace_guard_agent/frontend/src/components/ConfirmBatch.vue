<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    width="420px" :show-close="true" center
  >
    <div class="g-confirm-batch">
      <div class="confirm-icon">⚠️</div>
      <div class="confirm-count">{{ count }} 条数据</div>
      <div class="confirm-desc">{{ desc }}<br>此操作不可撤销，请确认后执行。</div>
    </div>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="$emit('confirm'); $emit('update:visible', false)">确认执行</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  visible?: boolean
  count?: number
  desc?: string
}>(), { count: 0, desc: '批量操作将处理以下数据' })

defineEmits<{
  'update:visible': [value: boolean]
  confirm: []
}>()
</script>