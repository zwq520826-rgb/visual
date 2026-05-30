<template>
  <div class="job-diff-butterfly">
    <div v-if="selectedJobs.length < 2" class="placeholder">
      <p>请选择 2 个职位查看真实值对比</p>
      <p class="hint">在左侧散点图中点击两个气泡加载蝴蝶图</p>
    </div>
    <div v-else-if="selectedJobs.length > 2" class="placeholder">
      <p>蝴蝶图仅支持 2 个职位</p>
      <p class="hint">请取消多余选择后再查看</p>
    </div>
    <div v-else ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  selectedJobs: {
    type: Array,
    default: () => []
  }
})

const chartContainer = ref(null)
let chartInstance = null

const dimensions = [
  { key: 'job_in_city_cnt', name: '招聘人数', unit: '个', formatter: (v) => formatLargeNumber(v) },
  { key: 'avg_salary', name: '平均薪资', unit: 'K', formatter: (v) => `${(v || 0).toFixed(2)}` },
  { key: 'avg_experience', name: '平均经验', unit: '级', formatter: (v) => `${(v || 0).toFixed(2)}` },
  { key: 'avg_education', name: '平均学历', unit: '级', formatter: (v) => `${(v || 0).toFixed(2)}` },
  { key: 'salary_std', name: '薪资波动', unit: 'K', formatter: (v) => `${(v || 0).toFixed(2)}` },
  { key: 'avg_shannon_entropy', name: '行业泛化性', unit: '', formatter: (v) => `${(v || 0).toFixed(3)}` }
]

const toNum = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const formatLargeNumber = (value) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return '--'
  if (Math.abs(value) >= 10000) return `${(value / 10000).toFixed(1)}万`
  if (Math.abs(value) >= 1000) return `${(value / 1000).toFixed(1)}千`
  return value.toFixed(0)
}

const buildOption = (jobs) => {
  const a = jobs[0]
  const b = jobs[1]
  const contributionScores = dimensions.map((dim) => {
    const rawA = toNum(a?.[dim.key])
    const rawB = toNum(b?.[dim.key])
    return Math.abs(rawA - rawB) / Math.max(Math.abs(rawA), Math.abs(rawB), 1e-6)
  })
  const totalContribution = contributionScores.reduce((sum, score) => sum + score, 0) || 1
  const contributions = contributionScores.map((score) => (score / totalContribution) * 100)
  const categories = dimensions.map((dim, index) => `${dim.name}  ${contributions[index].toFixed(1)}%`)

  const leftData = []
  const rightData = []

  dimensions.forEach((dim, index) => {
    const rawA = toNum(a?.[dim.key])
    const rawB = toNum(b?.[dim.key])
    const maxAbs = Math.max(Math.abs(rawA), Math.abs(rawB), 1e-6)
    const normA = (rawA / maxAbs) * 1.5
    const normB = (rawB / maxAbs) * 1.5

    leftData.push({ value: -normA, dimIndex: index, raw: rawA, contribution: contributions[index] })
    rightData.push({ value: normB, dimIndex: index, raw: rawB, contribution: contributions[index] })
  })

  return {
    title: {
      text: '职位真实值对比',
      left: 'center',
      top: 5,
      textStyle: { fontSize: 14, fontWeight: 'bold' }
    },
    graphic: [
      {
        type: 'text',
        left: '14%',
        top: 58,
        style: {
          text: '差异度贡献占比',
          fill: '#6e5b3e',
          fontSize: 12,
          fontWeight: 500
        }
      }
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const lines = params.map((p) => {
          const dim = dimensions[p.data.dimIndex]
          const raw = toNum(p.data.raw)
          const text = dim.formatter ? dim.formatter(raw) : `${raw}${dim.unit}`
          return `${p.marker} ${p.seriesName}: ${text}${dim.unit && !text.includes(dim.unit) ? dim.unit : ''}`
        })
        const contribution = params?.[0]?.data?.contribution ?? 0
        return `${params[0].axisValue}<br/>差异贡献：${contribution.toFixed(1)}%<br/>${lines.join('<br/>')}`
      }
    },
    grid: {
      top: 60,
      bottom: 20,
      left: 30,
      right: 78,
      containLabel: true
    },
    xAxis: {
      type: 'value',
      min: -1.5,
      max: 1.5,
      axisLine: { lineStyle: { color: '#8d9aa8' } },
      splitLine: { lineStyle: { type: 'dashed', color: '#d6cebe' } },
      axisLabel: { show: false }
    },
    yAxis: {
      type: 'category',
      data: categories,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: '#2f3a4a', fontSize: 12, margin: 56 }
    },
    series: [
      {
        name: a.job_title,
        type: 'bar',
        data: leftData,
        itemStyle: { color: '#2f6df6' },
        barWidth: 18,
        label: {
          show: true,
          position: 'left',
          distance: 12,
          formatter: (p) => {
            const dim = dimensions[p.data.dimIndex]
            const raw = toNum(p.data.raw)
            return dim.formatter ? dim.formatter(raw) : `${raw}${dim.unit}`
          }
        }
      },
      {
        name: b.job_title,
        type: 'bar',
        data: rightData,
        itemStyle: { color: '#e24a4a' },
        barWidth: 18,
        label: {
          show: true,
          position: 'right',
          formatter: (p) => {
            const dim = dimensions[p.data.dimIndex]
            const raw = toNum(p.data.raw)
            return dim.formatter ? dim.formatter(raw) : `${raw}${dim.unit}`
          }
        }
      }
    ],
    barGap: '-100%',
    barCategoryGap: '40%'
  }
}

const updateChart = () => {
  if (!chartInstance || props.selectedJobs.length !== 2) return
  chartInstance.setOption(buildOption(props.selectedJobs), true)
}

const disposeChart = () => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  window.removeEventListener('resize', handleResize)
}

const handleResize = () => {
  if (chartInstance) chartInstance.resize()
}

const initChart = async () => {
  await nextTick()
  if (!chartContainer.value) return
  disposeChart()
  chartInstance = echarts.init(chartContainer.value)
  window.addEventListener('resize', handleResize)
  updateChart()
}

watch(() => props.selectedJobs, async (jobs) => {
  await nextTick()
  if (jobs.length !== 2) {
    disposeChart()
    return
  }
  if (!chartInstance) {
    initChart()
  } else {
    updateChart()
  }
}, { deep: true })

onMounted(() => {
  if (props.selectedJobs.length === 2) initChart()
})

onUnmounted(() => {
  disposeChart()
})
</script>

<style scoped>
.job-diff-butterfly {
  --q1-title: #133a63;
  --q1-muted: #5d7c9f;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  overflow: hidden;
}

.chart-container {
  flex: 1;
  width: 100%;
  height: calc(100% - 10px);
  min-height: 312px;
}

.placeholder {
  text-align: center;
  color: var(--q1-muted);
  padding: 48px 20px;
  width: 100%;
  border: 1px dashed rgba(46, 122, 198, 0.3);
  border-radius: 12px;
  background: linear-gradient(155deg, rgba(247, 252, 255, 0.96), rgba(237, 247, 255, 0.96));
}

.placeholder p {
  margin: 0;
  color: var(--q1-title);
  font-size: 15px;
  font-weight: 700;
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: #2e7ac6;
  font-weight: 500;
}

@media (max-width: 900px) {
  .chart-container {
    min-height: 292px;
  }
}
</style>
