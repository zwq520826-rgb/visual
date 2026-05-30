<template>
  <div class="polar-comparison-chart">
    <div v-show="selectedJobs.length < 2" class="no-data-message">
      <p>请从散点图中选择2-3个职位进行多维对比</p>
      <p class="hint">极坐标柱图会按维度展示每个职位的相对强弱</p>
    </div>
    <div v-show="selectedJobs.length > 0" ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  selectedJobs: { type: Array, default: () => [] }
})

const chartContainer = ref(null)
let chartInstance = null

const dimensions = [
  { key: 'avg_salary', label: '平均薪资', unit: 'K' },
  { key: 'avg_experience', label: '经验要求', unit: '' },
  { key: 'avg_education', label: '学历要求', unit: '' },
  { key: 'job_in_city_cnt', label: '招聘人数', unit: '' },
  { key: 'salary_std', label: '薪资波动', unit: 'K' },
  { key: 'avg_shannon_entropy', label: '香农熵', unit: '' }
]

const colors = ['#2d7bff', '#00d7ff', '#ffd166']

const shortName = (name) => {
  const str = String(name || '')
  if (str.length <= 18) return str
  return `${str.slice(0, 8)}...${str.slice(-6)}`
}

const toNum = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const updateChart = () => {
  if (!chartInstance || props.selectedJobs.length === 0) return
  const jobs = props.selectedJobs.slice(0, 3)
  const nameMap = {}
  jobs.forEach((job, idx) => {
    const full = job.job_title || `职位${idx + 1}`
    nameMap[full] = shortName(full)
  })

  // 维度内占比归一化：同一维度下多个职位占比和为100，便于直接比较
  const normalizedMatrix = dimensions.map(dim => {
    const values = jobs.map(job => toNum(job[dim.key]))
    const total = values.reduce((sum, cur) => sum + cur, 0)
    if (total <= 0) {
      return values.map(() => 0)
    }
    return values.map(v => (v / total) * 100)
  })

  const maxPerDimension = normalizedMatrix.map(row => {
    const maxVal = Math.max(...row)
    return row.map(v => Math.abs(v - maxVal) < 1e-9)
  })

  const series = jobs.map((job, idx) => ({
    name: job.job_title || `职位${idx + 1}`,
    type: 'bar',
    coordinateSystem: 'polar',
    data: dimensions.map((_, dimIdx) => {
      const value = normalizedMatrix[dimIdx][idx] || 0
      const isMax = maxPerDimension[dimIdx]?.[idx]
      return {
        value,
        itemStyle: isMax
          ? {
              color: colors[idx % colors.length],
              opacity: 0.98,
              borderColor: '#fff7cf',
              borderWidth: 2,
              shadowBlur: 14,
              shadowColor: 'rgba(255, 219, 88, 0.75)'
            }
          : {
              color: colors[idx % colors.length],
              opacity: idx === 0 ? 0.85 : 0.62,
              borderColor: colors[idx % colors.length],
              borderWidth: 1
            }
      }
    }),
    stack: `g${idx}`,
    barWidth: idx === 0 ? 16 : 11,
    itemStyle: {
      color: colors[idx % colors.length]
    },
    emphasis: { focus: 'series' }
  }))

  chartInstance.setOption({
    backgroundColor: 'rgba(8,24,46,0.82)',
    tooltip: {
      trigger: 'item',
      formatter: p => {
        const dim = dimensions[p.dataIndex]
        const seriesIdx = Number.isInteger(p.seriesIndex) ? p.seriesIndex : -1
        const currentJob = seriesIdx >= 0 ? jobs[seriesIdx] : null
        const raw = currentJob ? toNum(currentJob[dim.key]) : 0
        return `${p.seriesName}<br/>${dim.label}: ${p.value.toFixed(1)}%<br/>原始值: ${raw.toFixed(2)}${dim.unit}`
      }
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      left: 10,
      top: 24,
      bottom: 24,
      itemWidth: 14,
      itemHeight: 14,
      formatter: (name) => nameMap[name] || name,
      tooltip: { show: true },
      textStyle: { color: '#cde7ff', width: 140, overflow: 'truncate' }
    },
    angleAxis: {
      type: 'category',
      data: dimensions.map(d => d.label),
      axisLabel: { color: '#cde7ff', fontSize: 11 }
    },
    radiusAxis: {
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: 'rgba(114,181,255,0.25)' } },
      axisLabel: { show: false }
    },
    polar: { center: ['63%', '56%'], radius: ['20%', '72%'] },
    series,
    animationDuration: 700
  }, true)
}

const ensureChart = () => {
  if (!chartContainer.value) return false
  if (!chartInstance) {
    chartInstance = echarts.init(chartContainer.value)
  }
  return true
}

const initChart = () => {
  if (!ensureChart()) return
  setTimeout(() => {
    if (chartInstance) {
      chartInstance.resize()
      updateChart()
    }
  }, 0)
}

const handleResize = () => chartInstance && chartInstance.resize()

watch(() => props.selectedJobs, async () => {
  await nextTick()
  if (!ensureChart()) return
  chartInstance.resize()
  updateChart()
}, { deep: true, immediate: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) chartInstance.dispose()
  chartInstance = null
})
</script>

<style scoped>
.chart-container { min-height: 320px; height: 100%; }
.no-data-message { color: #9ac4ec; text-align: center; padding: 24px 12px; }
.hint { font-size: 12px; opacity: 0.8; }
</style>
