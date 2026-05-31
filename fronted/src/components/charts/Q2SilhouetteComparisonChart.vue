<template>
  <div class="silhouette-wrap">
    <div v-if="loading" class="state">正在加载轮廓数据...</div>
    <div v-else-if="error" class="state error">{{ error }}</div>
    <div v-else-if="jobs.length === 0" class="state">请选择职位后点击“同步分析”</div>

    <div v-else class="silhouette-content">
      <div class="job-cards">
        <div class="job-cards-spacer" aria-hidden="true"></div>
        <div
          v-for="(job, idx) in displayJobs"
          :key="job?.job_title || `job-empty-${idx}`"
          class="job-card"
          :class="{ empty: !job }"
          :style="{ '--job-color': palette[idx] }"
        >
          <template v-if="job">
          <div class="avatar">
            <svg v-if="idx === 0" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="8.2" r="3.2" stroke="currentColor" stroke-width="1.8"/>
              <path d="M5.8 18.4C6.5 15.8 8.8 14.2 12 14.2C15.2 14.2 17.5 15.8 18.2 18.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M7 6.1V4.6M9.4 6.1V3.8M11.8 6.1V5M14.2 6.1V3.8M16.6 6.1V4.6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
            </svg>
            <svg v-else-if="idx === 1" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="7.8" r="3.1" stroke="currentColor" stroke-width="1.8"/>
              <path d="M6.2 18.2C6.8 15.7 9 14.3 12 14.3C15 14.3 17.2 15.7 17.8 18.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M4.6 11.2H7.2M16.8 11.2H19.4M7.8 11.2L10.2 9.5M13.8 9.5L16.2 11.2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="8.1" r="3.15" stroke="currentColor" stroke-width="1.8"/>
              <path d="M5.7 18.3C6.4 15.8 8.7 14.2 12 14.2C15.3 14.2 17.6 15.8 18.3 18.3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M9.8 11.1L8.6 13.1M14.2 11.1L15.4 13.1M10.8 12.1H13.2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="job-tag">职位 {{ labels[idx] }}</div>
          <div class="job-name" :title="job.job_title">{{ shorten(job.job_title) }}</div>
          <div class="job-strength">
            <span :style="{ width: `${scorePercent(job)}%` }"></span>
          </div>
          </template>
        </div>
      </div>

      <div class="matrix">
        <div v-for="metric in metrics" :key="metric.key" class="metric-row">
          <div class="metric-label">
            <span :class="['metric-icon', `metric-${metric.key}`]"></span>
            <span>{{ metric.label }}</span>
          </div>
          <div class="metric-values">
            <div
              v-for="(job, idx) in displayJobs"
              :key="`${metric.key}-${job?.job_title || idx}`"
              class="energy-cell"
              :class="{ empty: !job }"
              :style="{ '--job-color': palette[idx] }"
              :title="job ? `${metric.label}: ${metricValue(job, metric.key).toFixed(1)}` : ''"
            >
              <template v-if="job">
              <span class="energy-layout">
                <span class="energy-bar">
                  <span
                    v-for="seg in SEGMENT_COUNT"
                    :key="seg"
                    :class="['energy-seg', { on: seg <= segmentCount(job, metric.key) }]"
                  ></span>
                </span>
                <span class="metric-number" :class="{ hidden: metric.key !== 'salary' }">
                  {{ metric.key === 'salary' ? salaryLabel(job) : '000.00K' }}
                </span>
              </span>
              </template>
            </div>
          </div>
        </div>
      </div>

      <div class="legend">
        <div v-for="(job, idx) in jobs" :key="'legend-' + job.job_title" class="legend-item">
          <i :style="{ background: palette[idx] }"></i>
          <span>职位 {{ labels[idx] }}：{{ shorten(job.job_title) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: {
    type: Object,
    default: null
  },
  cityBreadthScores: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  }
})

const metrics = [
  { key: 'salary', label: '薪资水平' },
  { key: 'skill', label: '技能要求' },
  { key: 'concentration', label: '行业集中度' },
  { key: 'heat', label: '职业热度' },
  { key: 'cityBreadth', label: '城市分布广度' }
]

const labels = ['A', 'B', 'C']
const palette = ['#2f6df6', '#ef5350', '#37b568']
const SEGMENT_COUNT = 10

const jobs = computed(() => {
  const list = props.data?.positions || []
  return list.slice(0, 3)
})

const displayJobs = computed(() => {
  const arr = jobs.value.slice(0, 3)
  while (arr.length < 3) arr.push(null)
  return arr
})

const metricRanges = computed(() => {
  const ranges = {}
  metrics.forEach((metric) => {
    const vals = jobs.value.map((job) => metricValue(job, metric.key))
    if (!vals.length) {
      ranges[metric.key] = { min: 0, max: 0 }
      return
    }
    ranges[metric.key] = {
      min: Math.min(...vals),
      max: Math.max(...vals)
    }
  })
  return ranges
})

const metricValue = (job, key) => {
  if (!job) return 0

  if (key === 'salary') return Number(job?.values?.[0] || 0)
  if (key === 'skill') return Number(job?.values?.[1] || 0)
  if (key === 'concentration') return Number(job?.values?.[2] || 0)
  if (key === 'heat') return Number(job?.values?.[3] || 0)
  if (key === 'cityBreadth') return Number(props.cityBreadthScores?.[job.job_title] || 0)

  return 0
}

const segmentCount = (job, key) => {
  const v = metricValue(job, key)
  const range = metricRanges.value[key] || { min: 0, max: 0 }

  // 三职位该维度完全相同时，显示中间能量，避免全部熄灭。
  if (range.max === range.min) {
    return Math.ceil(SEGMENT_COUNT * 0.6)
  }

  const normalized = (v - range.min) / (range.max - range.min)
  return Math.max(1, Math.min(SEGMENT_COUNT, Math.round(normalized * (SEGMENT_COUNT - 1)) + 1))
}

const scorePercent = (job) => {
  if (!job) return 0
  const keys = ['salary', 'skill', 'concentration', 'heat', 'cityBreadth']
  const avgSegs = keys.reduce((sum, key) => sum + segmentCount(job, key), 0) / keys.length
  return Number(((avgSegs / SEGMENT_COUNT) * 100).toFixed(1))
}

const salaryLabel = (job) => {
  const raw = job?.details?.salary
  if (raw && typeof raw === 'string') {
    return raw
  }
  return `${metricValue(job, 'salary').toFixed(1)}`
}

const shorten = (text) => {
  if (!text) return '未命名职位'
  if (text.length <= 18) return text
  return `${text.slice(0, 8)}...${text.slice(-6)}`
}
</script>

<style scoped>
.silhouette-wrap {
  height: 100%;
  min-height: 540px;
  padding: 12px;
}

.silhouette-content {
  --label-col-width: 150px;
  height: 100%;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 14px;
}

.state {
  height: 100%;
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #59709a;
  font-weight: 600;
}

.state.error {
  color: #bf3a46;
}

.job-cards {
  display: grid;
  grid-template-columns: var(--label-col-width) repeat(3, minmax(0, 1fr));
  gap: 0;
}

.job-cards-spacer {
  min-height: 1px;
}

.job-card {
  border: 1px solid rgba(47, 109, 246, 0.15);
  border-radius: 12px;
  padding: 10px 8px;
  text-align: center;
  background: linear-gradient(180deg, #fff 0%, #f7fbff 100%);
  box-shadow: 0 8px 18px rgba(33, 79, 130, 0.08);
  position: relative;
  overflow: hidden;
}

.job-card.empty {
  opacity: 0;
  pointer-events: none;
}

.avatar {
  width: 48px;
  height: 48px;
  margin: 0 auto 6px;
  border-radius: 999px;
  background: radial-gradient(circle at 30% 30%, #fff, color-mix(in srgb, var(--job-color) 72%, white));
  border: 2px solid color-mix(in srgb, var(--job-color) 55%, white);
  position: relative;
  display: grid;
  place-items: center;
  color: color-mix(in srgb, var(--job-color) 72%, #18417a);
}

.avatar svg {
  width: 30px;
  height: 30px;
}

.job-tag {
  color: var(--job-color);
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 3px;
}

.job-name {
  color: #1d3966;
  font-size: 12px;
  line-height: 1.3;
  font-weight: 600;
}

.job-strength {
  margin-top: 8px;
  height: 6px;
  border-radius: 999px;
  background: #e8f1fb;
  overflow: hidden;
}

.job-strength span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, color-mix(in srgb, var(--job-color) 70%, white), var(--job-color));
  box-shadow: 0 0 8px color-mix(in srgb, var(--job-color) 35%, white);
  transition: width 0.4s ease;
}

.matrix {
  border: 1px solid #d8e3f6;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

.metric-row {
  display: grid;
  grid-template-columns: var(--label-col-width) 1fr;
  border-bottom: 1px solid #edf2fb;
}

.metric-row:last-child {
  border-bottom: none;
}

.metric-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  color: #304f80;
  font-size: 13px;
  font-weight: 700;
  background: linear-gradient(180deg, #f9fcff, #f1f7ff);
}

.metric-icon {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: 0.02em;
}

.metric-salary {
  background: linear-gradient(135deg, #2f6df6, #4f8bff);
}

.metric-salary::before {
  content: '¥';
}

.metric-skill {
  background: linear-gradient(135deg, #20a4b6, #37c0d2);
}

.metric-skill::before {
  content: '</>';
  font-size: 9px;
}

.metric-concentration {
  background: linear-gradient(135deg, #8a63df, #aa7af5);
}

.metric-concentration::before {
  content: '◎';
}

.metric-heat {
  background: linear-gradient(135deg, #ea7c43, #f29a4d);
}

.metric-heat::before {
  content: '≈';
}

.metric-cityBreadth {
  background: linear-gradient(135deg, #3e9c6a, #45b87a);
}

.metric-cityBreadth::before {
  content: '⌖';
}

.metric-values {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.energy-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 6px;
  position: relative;
}

.energy-cell.empty::before {
  display: none;
}

.energy-cell::before {
  content: '';
  position: absolute;
  inset: 6px 10px;
  border-radius: 8px;
  background: linear-gradient(120deg, rgba(47, 109, 246, 0.06), rgba(47, 109, 246, 0));
  opacity: 0;
  transition: opacity 0.2s ease;
}

.energy-cell:hover::before {
  opacity: 1;
}

.energy-layout {
  display: grid;
  grid-template-columns: 124px 74px;
  align-items: center;
  column-gap: 8px;
}

.energy-bar {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  min-width: 124px;
  gap: 4px;
}

.energy-seg {
  width: 8px;
  height: 12px;
  border-radius: 4px;
  background: linear-gradient(180deg, rgba(50, 73, 108, 0.34), rgba(31, 47, 73, 0.28));
  border: 1px solid rgba(135, 162, 201, 0.22);
  transition: transform 0.2s ease, background 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.energy-seg.on {
  background: linear-gradient(180deg, color-mix(in srgb, var(--job-color) 78%, white), var(--job-color));
  border-color: color-mix(in srgb, var(--job-color) 72%, white);
  box-shadow: 0 0 7px color-mix(in srgb, var(--job-color) 48%, white), inset 0 1px 0 rgba(255, 255, 255, 0.36);
}

.energy-cell:hover .energy-seg.on {
  transform: translateY(-1px) scale(1.05);
}

.metric-number {
  font-size: 12px;
  font-weight: 700;
  color: #2d4776;
  white-space: nowrap;
  text-align: left;
}

.metric-number.hidden {
  visibility: hidden;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  color: #3b5888;
  font-size: 12px;
  font-weight: 600;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.legend-item i {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.75), 0 0 8px rgba(33, 79, 130, 0.22);
}

@media (max-width: 900px) {
  .silhouette-content {
    --label-col-width: 120px;
  }

  .metric-row {
    grid-template-columns: var(--label-col-width) 1fr;
  }

  .metric-label {
    font-size: 12px;
  }

  .energy-layout {
    grid-template-columns: 110px 68px;
    column-gap: 6px;
  }

  .energy-bar {
    min-width: 110px;
    gap: 3px;
  }

  .energy-seg {
    width: 7px;
    height: 11px;
  }
}
</style>
