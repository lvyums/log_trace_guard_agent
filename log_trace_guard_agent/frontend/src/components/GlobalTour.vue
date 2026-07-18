<template>
  <div class="g-tour-overlay" @click.self="$emit('close')">
    <div class="g-tour-dialog" style="max-width:560px">
      <div class="g-tour-header">
        <div class="g-tour-title">安全日志分析工作流</div>
        <el-button :icon="'Close'" text @click="$emit('close')" />
      </div>
      <div class="g-tour-body">
        <div class="g-tour-step">
          <div class="g-tour-step-num">{{ currentStep + 1 }}</div>
          <div class="g-tour-step-content">
            <div class="g-tour-step-title">{{ step.title }}</div>
            <div class="g-tour-step-desc" style="line-height:1.7">{{ step.desc }}</div>
          </div>
        </div>
      </div>
      <div class="g-tour-footer">
        <div class="g-tour-progress">
          <div v-for="(s, i) in steps" :key="i" class="g-tour-dot" :class="{ active: i === currentStep }" />
        </div>
        <div class="g-tour-actions">
          <el-button size="small" @click="$emit('close')">跳过</el-button>
          <el-button size="small" :disabled="currentStep === 0" @click="prev">上一步</el-button>
          <el-button size="small" type="primary" @click="next">
            {{ isLast ? '完成' : '下一步' }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { APP_CONFIG } from '../config'

const emit = defineEmits<{ close: [] }>()
const props = defineProps<{ mode?: string }>()

const currentStep = ref(0)
const steps = APP_CONFIG.guidance.global.steps

const step = computed(() => steps[currentStep.value])
const isLast = computed(() => currentStep.value === steps.length - 1)

function next() {
  if (isLast.value) {
    emit('close')
  } else {
    currentStep.value++
  }
}
function prev() {
  if (currentStep.value > 0) currentStep.value--
}
</script>