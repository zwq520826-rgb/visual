<template>
  <section class="q1-shell">
    <header class="q1-hero">
      <div class="hero-main">
        <p class="hero-kicker">Q1 · 职位差异度分析</p>
        <h2>职位分布散点气泡图</h2>
        <p class="chart-description">
          以职位为基本单元，展示经验要求、薪资水平、招聘规模与行业泛化性的结构关系。
        </p>
      </div>
      <div class="hero-metrics">
        <div class="metric-pill">
          <span class="label">已选职位</span>
          <strong>{{ selectedCount }}</strong>
        </div>
        <div class="metric-pill">
          <span class="label">雷达图需求</span>
          <strong>2-3 个</strong>
        </div>
        <div class="metric-pill">
          <span class="label">蝴蝶图需求</span>
          <strong>2 个</strong>
        </div>
      </div>
    </header>

    <div class="q1-tab">
      <article class="left-section panel-card">
        <div class="panel-head">
          <h3>主视图 A：职位散点矩阵</h3>
          <p class="chart-description-small">
            可点击气泡联动右侧两张分析图；支持维度切换、缩放与 Top 标注。
          </p>
        </div>
        <div class="scatter-chart">
          <ScatterBubbleChart ref="scatterChart" />
        </div>
      </article>

      <aside class="right-section">
        <div class="right-chart radar-chart panel-card">
          <div class="panel-head">
            <h3>视图 B：职位多维对比（雷达）</h3>
            <p class="chart-description-small">
              支持 2-3 个职位叠加对比，快速查看薪资、门槛与热度轮廓。
            </p>
          </div>
          <RadarComparisonChart :selectedJobs="selectedNodes" />
        </div>

        <div class="right-chart ring-chart panel-card">
          <div class="panel-head">
            <h3>视图 C：差异度分解（蝴蝶）</h3>
            <p class="chart-description-small">
              仅支持 2 个职位；按维度展示两职位真实值与差异贡献。
            </p>
          </div>
          <JobDifferenceButterflyChart :selectedJobs="selectedNodes" />
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import ScatterBubbleChart from '@/components/charts/ScatterBubbleChart.vue'
import RadarComparisonChart from '@/components/charts/RadarComparisonChart.vue'
import JobDifferenceButterflyChart from '@/components/charts/JobDifferenceButterflyChart.vue'

// Q1 职位差异度分析标签页
// 包含三个视图：左侧散点图，右侧极坐标柱图和蝴蝶图

const scatterChart = ref(null)
const selectedNodes = ref([])
const selectedCount = computed(() => selectedNodes.value.length)

// 使用间隔轮询方式监听选中节点
let pollTimer = null
onMounted(() => {
  pollTimer = setInterval(() => {
    if (scatterChart.value) {
      const nodes = scatterChart.value.selectedNodes || []
      const needUpdate = nodes.length !== selectedNodes.value.length || 
        JSON.stringify(nodes) !== JSON.stringify(selectedNodes.value)

      if (needUpdate) {
        selectedNodes.value = [...nodes]
      }
    }
  }, 300)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})
</script>

<style scoped>
.q1-shell {
  --q1-bg-1: #f8fcff;
  --q1-bg-2: #eaf4ff;
  --q1-card-bg: rgba(255, 255, 255, 0.92);
  --q1-card-border: rgba(45, 88, 142, 0.2);
  --q1-title: #133a63;
  --q1-text: #2c4d72;
  --q1-muted: #5d7c9f;
  --q1-accent: #2e7ac6;
  --q1-accent-2: #d66b3d;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px;
  border-radius: 18px;
  background:
    radial-gradient(circle at 88% 0%, rgba(214, 107, 61, 0.14), transparent 30%),
    radial-gradient(circle at 0% 100%, rgba(46, 122, 198, 0.12), transparent 40%),
    linear-gradient(180deg, var(--q1-bg-1), var(--q1-bg-2));
}

.q1-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 18px;
  border-radius: 14px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.95), rgba(243, 250, 255, 0.95));
  border: 1px solid rgba(46, 122, 198, 0.18);
  box-shadow: 0 12px 28px rgba(40, 85, 137, 0.1);
  animation: q1Rise 0.45s ease both;
}

.hero-main h2 {
  margin: 0;
  color: var(--q1-title);
  font-size: clamp(1.15rem, 1.5vw, 1.45rem);
  line-height: 1.28;
}

.hero-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--q1-accent);
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(104px, 1fr));
  gap: 10px;
  width: min(420px, 48%);
}

.metric-pill {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(46, 122, 198, 0.25);
  background: rgba(234, 244, 255, 0.88);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-pill .label {
  color: var(--q1-muted);
  font-size: 11px;
  font-weight: 700;
}

.metric-pill strong {
  color: var(--q1-title);
  font-size: 18px;
  line-height: 1.2;
}

.q1-tab {
  display: flex;
  gap: 16px;
  align-items: stretch;
  min-height: 640px;
  animation: q1Rise 0.55s ease both;
  animation-delay: 0.08s;
}

.chart-description {
  margin: 8px 0 0;
  max-width: 66ch;
  color: var(--q1-muted);
  line-height: 1.58;
  font-size: 14px;
}

.chart-description-small {
  margin: 4px 0 0;
  color: #547495;
  line-height: 1.52;
  font-size: 13px;
}

.left-section {
  flex: 2;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.scatter-chart {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 460px;
}

.right-section {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.panel-card {
  background: var(--q1-card-bg);
  border: 1px solid var(--q1-card-border);
  border-radius: 14px;
  box-shadow: 0 10px 24px rgba(42, 87, 139, 0.12);
  padding: 12px;
}

.panel-head {
  margin-bottom: 10px;
}

.panel-head h3 {
  margin: 0;
  color: var(--q1-title);
  font-size: 17px;
  line-height: 1.3;
}

.right-chart {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.radar-chart {
  position: relative;
  overflow: hidden;
}

.radar-chart::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(46, 122, 198, 0.22), transparent);
  pointer-events: none;
}

.ring-chart {
  position: relative;
}

.ring-chart::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 84px;
  height: 84px;
  background: radial-gradient(circle, rgba(214, 107, 61, 0.12), transparent 70%);
  pointer-events: none;
}

.right-chart {
  background: linear-gradient(165deg, rgba(255, 255, 255, 0.95), rgba(244, 251, 255, 0.92));
}

.radar-chart,
.ring-chart {
  box-sizing: border-box;
}

@keyframes q1Rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1320px) {
  .q1-hero {
    flex-direction: column;
  }

  .hero-metrics {
    width: 100%;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1200px) {
  .q1-tab {
    flex-direction: column;
  }
  
  .right-section {
    flex-direction: row;
    gap: 14px;
  }
  
  .radar-chart {
    min-height: 350px;
  }
  
  .ring-chart {
    min-height: 350px;
  }
}

@media (max-width: 900px) {
  .q1-shell {
    padding: 10px;
  }

  .hero-metrics {
    grid-template-columns: 1fr;
  }

  .right-section {
    flex-direction: column;
  }

  .panel-head h3 {
    font-size: 15px;
  }

  .scatter-chart {
    min-height: 420px;
  }
}
</style>
