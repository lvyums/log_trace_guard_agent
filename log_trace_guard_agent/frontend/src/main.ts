import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// Import all CSS - now copied to src/css
import './css/variables.css'
import './css/layout.css'
import './css/components.css'
import './css/guidance.css'
import './css/modules.css'
import './css/responsive.css'

import App from './App.vue'

const app = createApp(App)

app.use(ElementPlus, { locale: zhCn })

// Register all Element Plus icons globally
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')

console.log('[App] Mounted successfully with Vite build')
