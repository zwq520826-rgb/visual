<template>
  <div class="diverging-diff-chart">
    <div v-show="selectedJobs.length < 2" class="no-data-message">
      <p>请从散点图中选择 2 个职位进行差异分析</p>
      <p class="hint">发散型条形图显示 A-B 的维度差值方向与幅度</p>
    </div>
    <div v-show="selectedJobs.length > 2" class="warning-message">
      <p>发散型条形图仅支持 2 个职位</p>
      <p class="hint">当前已选择 {{ selectedJobs.length }} 个职位</p>
    </div>
    <div v-show="selectedJobs.length === 2" ref="chartContainer" class="chart-container"></div>
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
  { key: 'avg_salary', label: '平均薪资', unit: 'K' },
  { key: 'avg_experience', label: '经验要求', unit: '' },
  { key: 'avg_education', label: '学历要求', unit: '' },
  { key: 'job_in_city_cnt', label: '招聘人数', unit: '' },
  { key: 'salary_std', label: '薪资波动', unit: 'K' },
  { key: 'avg_shannon_entropy', label: '行业泛化性', unit: '' }
]

const toNum = (value) => {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

const shortName = (name) => {
  const text = String(name || '')
  return text.length <= 18 ? text : `${text.slice(0, 8)}...${text.slice(-6)}`
}

const updateChart = () => {
  if (!chartInstance || props.selectedJobs.length !== 2) return

  const [jobA, jobB] = props.selectedJobs
  const rows = dimensions.map((dim) => {
    const aValue = toNum(jobA[dim.key])
    const bValue = toNum(jobB[dim.key])
    const delta = aValue - bValue
    const base = Math.max(Math.abs(aValue), Math.abs(bValue), 1e-6)
    const normalizedDelta = (delta / base) * 100
    return {
      label: dim.label,
      key: dim.key,
      unit: dim.unit,
      aValue,
      bValue,
      delta,
      normalizedDelta
    }
  })

  const maxAbsDelta = Math.max(...rows.map((row) => Math.abs(row.normalizedDelta)), 1)

  chartInstance.setOption({
    backgroundColor: 'rgba(8,24,46,0.82)',
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const row = rows[params.dataIndex]
        const sign = row.delta >= 0 ? '+' : ''
        return [
          `<strong>${row.label}</strong>`,
          `${jobA.job_title}: ${row.aValue.toFixed(2)}${row.unit}`,
          `${jobB.job_title}: ${row.bValue.toFixed(2)}${row.unit}`,
          `原始差值(A-B): ${sign}${row.delta.toFixed(2)}${row.unit}`,
          `归一化差值: ${sign}${row.normalizedDelta.toFixed(1)}%`
        ].join('<br/>')
      }
    },
    legend: {
      left: 10,
      top: 8,
      itemWidth: 12,
      itemHeight: 12,
      formatter: (name) => shortName(name),
      textStyle: { color: '#cde7ff', width: 160, overflow: 'truncate' },
      data: [jobA.job_title || '职位A', jobB.job_title || '职位B']
    },
    grid: {
      left: 110,
      right: 30,
      top: 58,
      bottom: 20
    },
    xAxis: {
      type: 'value',
      min: -maxAbsDelta,
      max: maxAbsDelta,
      axisLine: { lineStyle: { color: '#9bc8ef' } },
      splitLine: { lineStyle: { color: 'rgba(114,181,255,0.2)' } },
      axisLabel: {
        color: '#bcdcff',
        formatter: (value) => `${value.toFixed(0)}%`
      }
    },
    yAxis: {
      type: 'category',
      data: rows.map((row) => row.label),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#d6ebff' }
    },
    series: [
      {
        name: '归一化差值(A-B)',
        type: 'bar',
        data: rows.map((row) => row.normalizedDelta),
        barWidth: 18,
        itemStyle: {
          color: (params) => (params.value >= 0 ? '#2d7bff' : '#00d7ff')
        },
        label: {
          show: true,
          position: (params) => (params.value >= 0 ? 'right' : 'left'),
          color: '#dff3ff',
          formatter: (params) => {
            const row = rows[params.dataIndex]
            const sign = params.value >= 0 ? '+' : ''
            return `${sign}${params.value.toFixed(1)}%`
          }
        },
        markLine: {
          symbol: 'none',
          lineStyle: {
            color: '#ffd166',
            width: 1.4,
            type: 'solid'
          },
          data: [{ xAxis: 0 }]
        }
      }
    ],
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

const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

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
  if (chartInstance) {
    chartInstance.dispose()
  }
  chartInstance = null
})
</script>

<style scoped>
.chart-container {
  min-height: 320px;
  height: 100%;
}

.no-data-message,
.warning-message {
  color: #9ac4ec;
  text-align: center;
  padding: 24px 12px;
}

.hint {
  font-size: 12px;
  opacity: 0.8;
}
</style>
