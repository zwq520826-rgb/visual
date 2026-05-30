<template>
  <div class="industry-contribution-pie-chart">
    <div v-if="selectedIndustries.length < 2" class="empty-state">
      <p>请先在左侧散点图中选择 2 个行业</p>
      <p class="hint">将基于两个行业的维度差异占比绘制单个饼图</p>
    </div>
    <div ref="chartContainer" v-show="selectedIndustries.length >= 2" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  selectedIndustries: { type: Array, default: () => [] }
})

const chartContainer = ref(null)
let chartInstance = null

const DIMENSIONS = [
  { key: 'avg_median_salary', label: '薪资水平', color: '#2d7bff' },
  { key: 'avg_experience_rank', label: '经验要求', color: '#00d7ff' },
  { key: 'avg_education_rank', label: '学历要求', color: '#00c8a7' },
  { key: 'avg_city_tier_score', label: '城市等级', color: '#ffd166' },
  { key: 'job_count', label: '招聘规模', color: '#7b9cff' }
]

const toNum = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const shortName = (name) => {
  const s = String(name || '')
  return s.length <= 14 ? s : `${s.slice(0, 5)}...${s.slice(-4)}`
}

const normalizeDiffContribution = (a, b) => {
  const rawDiff = DIMENSIONS.map(d => Math.abs(toNum(a[d.key]) - toNum(b[d.key])))
  const sum = rawDiff.reduce((x, y) => x + y, 0) || 1
  return DIMENSIONS.map((d, idx) => ({
    name: d.label,
    value: (rawDiff[idx] / sum) * 100,
    itemStyle: { color: d.color },
    rawValue: rawDiff[idx]
  }))
}

const renderChart = () => {
  if (!chartInstance || props.selectedIndustries.length < 2) return

  const [a, b] = props.selectedIndustries
  const pieData = normalizeDiffContribution(a, b)

  chartInstance.setOption({
    backgroundColor: 'rgba(8,24,46,0.82)',
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${p.name}: ${p.percent.toFixed(1)}%<br/>绝对差值: ${toNum(p.data.rawValue).toFixed(2)}`
    },
    legend: {
      top: 8,
      textStyle: { color: '#cde7ff' },
      data: DIMENSIONS.map(d => d.label)
    },
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '17%',
        style: {
          text: `${shortName(a.company_type)} vs ${shortName(b.company_type)}`,
          fill: '#bfe1ff',
          font: '14px sans-serif'
        }
      }
    ],
    series: [
      {
        name: '维度差异占比',
        type: 'pie',
        radius: ['36%', '68%'],
        center: ['50%', '58%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderColor: 'rgba(8,24,46,0.82)',
          borderWidth: 1
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          color: '#d8ecff',
          fontSize: 11
        },
        labelLine: {
          lineStyle: { color: 'rgba(200,230,255,0.8)' }
        },
        data: pieData
      }
    ]
  }, true)
}

const ensureChart = () => {
  if (!chartContainer.value) return false
  if (!chartInstance) {
    chartInstance = echarts.init(chartContainer.value)
  }
  return true
}

watch(() => props.selectedIndustries, async () => {
  await nextTick()
  if (props.selectedIndustries.length < 2) {
    if (chartInstance) chartInstance.clear()
    return
  }
  if (!ensureChart()) return
  chartInstance.resize()
  renderChart()
}, { deep: true, immediate: true })

const handleResize = () => chartInstance && chartInstance.resize()

onMounted(() => {
  if (chartContainer.value && !chartInstance) {
    chartInstance = echarts.init(chartContainer.value)
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) chartInstance.dispose()
  chartInstance = null
})
</script>

<style scoped>
.chart-container {
  width: 100%;
  min-height: 320px;
  height: 100%;
  border-radius: 10px;
  background: rgba(8, 24, 46, 0.82);
}
.empty-state {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #a9cae9;
  border: 1px dashed rgba(114, 181, 255, 0.35);
  border-radius: 10px;
  background: rgba(8, 24, 46, 0.35);
}
.hint { margin-top: 8px; font-size: 12px; color: #89add0; }
</style>
