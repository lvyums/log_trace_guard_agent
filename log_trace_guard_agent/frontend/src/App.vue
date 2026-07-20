<template>
  <div v-if="ready" class="app-shell">
    <GlobalTour v-if="showTour" @close="showTour = false" :mode="currentMode" />

    <header class="app-header" :class="{ 'is-collapsed': sidebarCollapsed }">
      <div class="header-left">
        <div class="header-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="logo-icon">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
          <span class="logo-text">日志溯源卫士</span>
        </div>
        <el-button class="sidebar-toggle" :icon="sidebarCollapsed ? 'Expand' : 'Fold'" @click="toggleSidebar" circle size="small" />
      </div>

      <nav class="header-nav">
        <div v-for="mod in filteredModules" :key="mod.key"
             class="nav-tab" :class="{ active: currentModule === mod.key }"
             @click="switchModule(mod.key)">
          <el-icon><component :is="mod.icon" /></el-icon>
          <span>{{ mod.label }}</span>
        </div>
      </nav>

      <div class="header-right">
        <el-tooltip :content="currentMode === 'ops' ? '切换至实训模式' : '切换至运维模式'" placement="bottom">
          <el-switch v-model="isTrainingMode" @change="toggleMode"
            active-text="实训" inactive-text="运维"
            active-color="#FF7D00" inactive-color="#165DFF" />
        </el-tooltip>
        <el-tooltip :content="isDark ? '切换浅色主题' : '切换深色主题'" placement="bottom">
          <el-button :icon="isDark ? 'Sunny' : 'Moon'" @click="toggleTheme" circle size="small" />
        </el-tooltip>
        <el-tooltip content="查看新手引导" placement="bottom">
          <el-button icon="QuestionFilled" @click="showTour = true" circle size="small" />
        </el-tooltip>
      </div>
    </header>

    <div class="app-body" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <aside class="app-sidebar" :class="{ collapsed: sidebarCollapsed }">
        <div v-for="mod in modules" :key="mod.key" class="sidebar-section" v-show="currentModule === mod.key">
          <div class="sidebar-title">{{ mod.label }}</div>
          <div v-for="item in mod.children" :key="item.path"
            class="sidebar-item" :class="{ active: currentPath === item.path }"
            @click="navigate(item.path)">
            <el-icon><component :is="item.icon" /></el-icon>
            <span class="sidebar-item-text">{{ item.label }}</span>
          </div>
        </div>
      </aside>

      <main class="app-main" id="main-content">
        <component :is="currentComponent" :mode="currentMode" />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, shallowRef, markRaw, onMounted } from 'vue'
import { APP_CONFIG } from './config'
import GlobalTour from './components/GlobalTour.vue'

// Import all page components
import LogParseIdentify from './modules/log-parse/Identify.vue'
import LogParseParse from './modules/log-parse/Parse.vue'
import LogParseAssess from './modules/log-parse/Assess.vue'
import LogParseBatch from './modules/log-parse/Batch.vue'
import LogCollectMatch from './modules/log-collect/Match.vue'
import LogCollectPlan from './modules/log-collect/Plan.vue'
import LogCollectFault from './modules/log-collect/Fault.vue'
import LogCollectArch from './modules/log-collect/Arch.vue'
import ScriptGenRegex from './modules/script-gen/Regex.vue'
import ScriptGenEsquery from './modules/script-gen/EsQuery.vue'
import ScriptGenPlatform from './modules/script-gen/Platform.vue'
import ScriptGenTrace from './modules/script-gen/Trace.vue'
import ScriptGenOptimize from './modules/script-gen/Optimize.vue'
import ComplianceQa from './modules/compliance/Qa.vue'
import ComplianceBaseline from './modules/compliance/Baseline.vue'
import ComplianceCheck from './modules/compliance/Check.vue'
import TrainingScenarios from './modules/training/Scenarios.vue'
import TrainingSubmit from './modules/training/Submit.vue'
import TrainingReport from './modules/training/Report.vue'
import LogCorrelateAnalyze from './modules/log-correlate/Analyze.vue'
import LogCorrelatePatterns from './modules/log-correlate/Patterns.vue'

const ROUTE_MAP: Record<string, any> = {
  '/log-parse/identify': markRaw(LogParseIdentify),
  '/log-parse/parse': markRaw(LogParseParse),
  '/log-parse/assess': markRaw(LogParseAssess),
  '/log-parse/batch': markRaw(LogParseBatch),
  '/log-collect/match': markRaw(LogCollectMatch),
  '/log-collect/plan': markRaw(LogCollectPlan),
  '/log-collect/fault': markRaw(LogCollectFault),
  '/log-collect/arch': markRaw(LogCollectArch),
  '/script-gen/regex': markRaw(ScriptGenRegex),
  '/script-gen/es-query': markRaw(ScriptGenEsquery),
  '/script-gen/platform': markRaw(ScriptGenPlatform),
  '/script-gen/trace': markRaw(ScriptGenTrace),
  '/script-gen/optimize': markRaw(ScriptGenOptimize),
  '/compliance/qa': markRaw(ComplianceQa),
  '/compliance/baseline': markRaw(ComplianceBaseline),
  '/compliance/check': markRaw(ComplianceCheck),
  '/training/scenarios': markRaw(TrainingScenarios),
  '/training/submit': markRaw(TrainingSubmit),
  '/training/report': markRaw(TrainingReport),
  '/log-correlate/analyze': markRaw(LogCorrelateAnalyze),
  '/log-correlate/patterns': markRaw(LogCorrelatePatterns),
}

const ready = ref(false)
const currentModule = ref('log-parse')
const currentPath = ref('/log-parse/identify')
const sidebarCollapsed = ref(false)
const isDark = ref(true)
const isTrainingMode = ref(false)
const showTour = ref(false)
const modules = APP_CONFIG.modules

const currentMode = computed(() => isTrainingMode.value ? 'training' : 'ops')
const currentComponent = computed(() => ROUTE_MAP[currentPath.value])

// 根据模式过滤模块：攻防实训仅在实训模式下显示
const filteredModules = computed(() => {
  return modules.filter(m => {
    if (m.key === 'training') {
      return isTrainingMode.value  // 仅实训模式显示
    }
    return true
  })
})

function switchModule(key: string) {
  currentModule.value = key
  const mod = modules.find(m => m.key === key)
  if (mod && mod.children.length) {
    currentPath.value = mod.children[0].path
  }
  updateUrl()
}

function navigate(path: string) {
  currentPath.value = path
  const mod = modules.find(m => m.children.some(c => c.path === path))
  if (mod) currentModule.value = mod.key
  updateUrl()
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function toggleTheme() {
  isDark.value = !isDark.value
  applyTheme()
  localStorage.setItem('lg-theme', isDark.value ? 'dark' : 'light')
}

function toggleMode(val: boolean) {
  isTrainingMode.value = val
  localStorage.setItem('lg-mode', val ? 'training' : 'ops')
  if (val && !localStorage.getItem('lg-tour-seen')) {
    showTour.value = true
  }
  // 切换到运维模式时，如果当前在攻防实训页面，跳转到日志解析首页
  if (!val && currentModule.value === 'training') {
    switchModule('log-parse')
  }
}

function applyTheme() {
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  if (isDark.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

function updateUrl() {
  const hash = '#' + currentPath.value
  if (window.location.hash !== hash) {
    window.location.hash = hash
  }
}

function parseHash() {
  const hash = window.location.hash.slice(1)
  if (hash && ROUTE_MAP[hash]) {
    currentPath.value = hash
    const mod = modules.find(m => m.children.some(c => c.path === hash))
    if (mod) currentModule.value = mod.key
  }
}

function initFromStorage() {
  const theme = localStorage.getItem('lg-theme')
  if (theme) {
    isDark.value = theme === 'dark'
    applyTheme()
  }
  const mode = localStorage.getItem('lg-mode')
  if (mode === 'training') {
    isTrainingMode.value = true
  }
  const tourSeen = localStorage.getItem('lg-tour-seen')
  if (!tourSeen) {
    showTour.value = true
  }
}

onMounted(() => {
  parseHash()
  initFromStorage()
  // 运维模式下攻防实训模块不可见，跳转首页
  if (!isTrainingMode.value && currentModule.value === 'training') {
    switchModule('log-parse')
  }
  ready.value = true
  window.addEventListener('hashchange', parseHash)
})
</script>