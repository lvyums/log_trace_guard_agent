<template>
  <div class="g-stack">
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Grid /></el-icon> 批量解析</div>
          <div class="g-card-desc">批量上传日志文件进行解析分析</div>
        </div>
      </div>
      <p style="color:var(--text-secondary);font-size:14px">批量解析功能即将上线</p>
    </div>
  </div>
</template>
<script setup lang="ts">
defineProps<{ mode?: string }>()
</script>