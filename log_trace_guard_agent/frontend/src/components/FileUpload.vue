<template>
  <div class="file-upload-component">
    <input
      ref="fileInputRef"
      type="file"
      :accept="accept"
      style="display:none"
      :multiple="multiple"
      @change="onFileSelected"
    />
    <el-button size="small" :disabled="disabled" @click="triggerFilePicker">
      <el-icon style="margin-right:4px"><Upload /></el-icon> {{ buttonText }}
    </el-button>

    <div v-if="loadedFiles.length" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px">
      <el-tag v-for="(file, i) in loadedFiles" :key="i" size="small" closable @close="removeFile(i)">
        {{ file.name }}
        <span v-if="file.size" style="margin-left:4px;color:var(--text-tertiary);font-size:11px">
          ({{ formatSize(file.size) }})
        </span>
      </el-tag>
    </div>

    <div v-if="uploading" style="margin-top:8px;font-size:12px;color:var(--text-secondary)">
      <el-icon class="is-loading" style="margin-right:4px"><Loading /></el-icon>
      上传中...
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../api'

interface UploadedFile {
  name: string
  path: string
  size?: number
}

interface Props {
  accept?: string
  multiple?: boolean
  disabled?: boolean
  buttonText?: string
  uploadApi?: (formData: FormData) => Promise<any>
  cleanupApi?: (data: any) => Promise<any>
}

const props = withDefaults(defineProps<Props>(), {
  accept: '.log,.txt,.csv,.json',
  multiple: true,
  disabled: false,
  buttonText: '上传日志文件（可多选）',
  uploadApi: (formData: FormData) => Api.logParse.upload(formData),
  cleanupApi: (data: any) => Api.logParse.cleanup(data),
})

const emit = defineEmits<{
  (e: 'update:files', files: UploadedFile[]): void
  (e: 'upload-success', files: UploadedFile[]): void
  (e: 'upload-error', msg: string): void
  (e: 'remove', file: UploadedFile): void
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const loadedFiles = ref<UploadedFile[]>([])
const uploading = ref(false)

const hasFiles = computed(() => loadedFiles.value.length > 0)

function triggerFilePicker() {
  fileInputRef.value?.click()
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / (1024 * 1024)).toFixed(1) + 'MB'
}

async function onFileSelected(event: Event) {
  const el = event.target as HTMLInputElement
  const files = el.files
  if (!files || files.length === 0) return

  uploading.value = true
  try {
    const formData = new FormData()
    for (const file of Array.from(files)) {
      formData.append('files', file)
    }

    const uploadRes = await props.uploadApi(formData)
    if (!uploadRes.success || !uploadRes.data?.file_paths?.length) {
      const msg = uploadRes.msg || '文件上传失败'
      ElMessage.error(msg)
      emit('upload-error', msg)
      return
    }

    const newFiles: UploadedFile[] = Array.from(files).map((f, i) => ({
      name: f.name,
      path: uploadRes.data.file_paths[i],
      size: f.size,
    }))

    loadedFiles.value = [...loadedFiles.value, ...newFiles]
    emit('update:files', [...loadedFiles.value])
    emit('upload-success', newFiles)
    ElMessage.success(`已上传 ${newFiles.length} 个文件`)
  } catch (err: any) {
    const msg = '文件上传失败: ' + (err.message || '未知错误')
    ElMessage.error(msg)
    emit('upload-error', msg)
  } finally {
    uploading.value = false
    el.value = ''
  }
}

async function removeFile(index: number) {
  const file = loadedFiles.value[index]
  if (!file) return
  // 先从列表移除，再异步清理服务端文件
  loadedFiles.value.splice(index, 1)
  emit('update:files', [...loadedFiles.value])
  emit('remove', file)
  // 异步清理，不阻塞 UI
  try {
    await props.cleanupApi({ file_paths: [file.path] })
  } catch {
    // 清理失败忽略，文件会自动过期
  }
}

async function clearAll() {
  const paths = loadedFiles.value.map(f => f.path)
  loadedFiles.value = []
  emit('update:files', [])
  // 异步清理服务端文件
  if (paths.length) {
    try {
      await props.cleanupApi({ file_paths: paths })
    } catch {
      // 清理失败忽略
    }
  }
}

function getFilePaths(): string[] {
  return loadedFiles.value.map(f => f.path)
}

defineExpose({
  clearAll,
  getFilePaths,
  hasFiles,
  loadedFiles,
})
</script>
