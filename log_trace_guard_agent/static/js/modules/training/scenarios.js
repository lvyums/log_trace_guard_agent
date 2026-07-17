/* ============================================
   模块五 · 实训场景 — 查看并选择攻防实训场景
   ============================================ */

const TrainingScenarios = {
  name: 'TrainingScenarios',
  props: { mode: String },
  data() {
    return {
      scenarios: [],
      loading: false,
      selected: null,
    };
  },
  computed: {
    isTraining() {
      return this.mode === 'training';
    },
  },
  methods: {
    async loadScenarios() {
      this.loading = true;
      try {
        const res = await Api.training.scenarios();
        if (res.success && res.data) {
          this.scenarios = Array.isArray(res.data) ? res.data : (res.data.scenarios || []);
        } else {
          this.loadSampleScenarios();
        }
      } catch (e) {
        this.loadSampleScenarios();
      } finally {
        this.loading = false;
      }
    },
    loadSampleScenarios() {
      this.scenarios = [
        { id: 1, title: 'SSH暴力破解检测', difficulty: '初级', category: '入侵检测', description: '分析SSH登录日志，识别暴力破解行为并溯源攻击IP', steps: 3 },
        { id: 2, title: 'Web攻击日志分析', difficulty: '中级', category: 'Web安全', description: '分析WAF日志，识别SQL注入、XSS等Web攻击', steps: 5 },
        { id: 3, title: '内网横向移动追踪', difficulty: '高级', category: '应急响应', description: '通过多源日志关联分析，追踪内网横向移动路径', steps: 7 },
        { id: 4, title: '日志采集架构设计', difficulty: '中级', category: '架构设计', description: '根据企业需求设计完整的日志采集与存储架构', steps: 4 },
        { id: 5, title: '合规基线检查', difficulty: '初级', category: '合规审计', description: '对服务器配置进行等保2.0三级合规自查', steps: 3 },
      ];
    },
    selectScenario(s) {
      this.selected = s;
    },
    startTraining() {
      if (this.selected) {
        window.location.hash = '#/training/submit';
      }
    },
  },
  mounted() {
    this.loadScenarios();
  },
  template: `
    <div class="g-stack">
      <alert-guide type="info" title="选择场景前先评估自己的水平">
        初级：适合刚接触日志分析的学员，主要考察基础字段提取能力。中级：需要理解攻击原理，能关联多条日志判断攻击阶段。高级：需要完整还原攻击链并给出溯源建议。
      </alert-guide>

      <!-- 实训模式提示 -->
      <alert-guide v-if="isTraining" type="info" title="实训模式已开启">
        选择一个实训场景开始练习。每个场景包含分步指引和标准答案，完成后可查看详细报告。
      </alert-guide>

      <div class="g-card">
        <div class="g-card-header">
          <div class="g-card-title"><el-icon><Reading /></el-icon> 实训场景</div>
        </div>

        <div v-if="loading" style="text-align:center;padding:40px">
          <el-icon class="is-loading" :size="32" color="var(--primary)"><Loading /></el-icon>
          <div style="margin-top:8px;font-size:13px;color:var(--text-tertiary)">加载中...</div>
        </div>

        <div v-else-if="!scenarios.length" class="g-empty">
          <empty-guide title="暂无实训场景" desc="请稍后再试或联系管理员" />
        </div>

        <div v-else style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px">
          <div v-for="s in scenarios" :key="s.id"
               class="training-task-item" :class="{ active: selected?.id === s.id }"
               @click="selectScenario(s)">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
              <div style="display:flex;align-items:center;gap:8px">
                <span class="training-task-num">{{ s.id }}</span>
                <span class="training-task-title">{{ s.title }}</span>
              </div>
              <risk-badge :level="s.difficulty === '高级' ? 'P0' : s.difficulty === '中级' ? 'P1' : 'P3'"
                         :label="s.difficulty" />
            </div>
            <div style="font-size:12px;color:var(--text-tertiary);margin-bottom:6px">{{ s.category }} · {{ s.steps }}个步骤</div>
            <div style="font-size:13px;color:var(--text-secondary)">{{ s.description }}</div>
          </div>
        </div>
      </div>

      <div v-if="selected && isTraining" class="g-actions" style="justify-content:center">
        <el-button type="primary" size="large" @click="startTraining">
          <el-icon style="margin-right:4px"><Promotion /></el-icon> 开始实训
        </el-button>
      </div>
    </div>
  `,
};
