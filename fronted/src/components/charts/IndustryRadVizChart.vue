<template>
  <div class="industry-radviz-chart">
    <div v-if="!hasSelection" class="empty-state">
      <p>请先在左侧散点图中选择行业</p>
      <p class="hint">至少选择 1 个行业后显示 RadViz 维度贡献图</p>
    </div>
    <div v-else ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getNationalIndustryScatter } from '@/api/q1Api'

const props = defineProps({
  selectedIndustries: { type: Array, default: () => [] }
})

const hasSelection = computed(() => (props.selectedIndustries || []).length > 0)

const chartContainer = ref(null)
let chartInstance = null
const rawData = ref([])

const DIMS = [
  { key: 'avg_median_salary', label: '薪资' },
  { key: 'avg_experience_rank', label: '经验' },
  { key: 'avg_education_rank', label: '学历' },
  { key: 'avg_city_tier_score', label: '城市等级' },
  { key: 'job_count', label: '规模' }
]

const palette = ['#2d7bff', '#00d7ff', '#00c8a7', '#ffd166', '#7db8ff']

const toNum = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const shortName = (name) => {
  const s = String(name || '')
  return s.length <= 12 ? s : `${s.slice(0, 5)}...${s.slice(-3)}`
}

const buildOption = () => {
  if (!hasSelection.value) return null
  const rows = [...rawData.value].sort((a, b) => toNum(b.job_count) - toNum(a.job_count)).slice(0, 80)
  const selectedSet = new Set((props.selectedIndustries || []).map(i => i.company_type))
  const selectedRows = rows.filter(r => selectedSet.has(r.company_type))

  const minMax = {}
  DIMS.forEach(dim => {
    const vals = rows.map(r => toNum(r[dim.key]))
    minMax[dim.key] = { min: Math.min(...vals), max: Math.max(...vals) }
  })

  const anchors = DIMS.map((dim, idx) => {
    const angle = (Math.PI * 2 * idx) / DIMS.length - Math.PI / 2
    return { key: dim.key, label: dim.label, x: Math.cos(angle), y: Math.sin(angle), color: palette[idx % palette.length] }
  })

  const getNorm = (row, key) => {
    const mm = minMax[key]
    const value = toNum(row[key])
    if (mm.max <= mm.min) return 0.5
    return (value - mm.min) / (mm.max - mm.min)
  }

  const points = selectedRows.map(row => {
    const weights = anchors.map(a => Math.max(0.0001, getNorm(row, a.key)))
    const sum = weights.reduce((s, v) => s + v, 0)
    const x = weights.reduce((s, w, i) => s + w * anchors[i].x, 0) / sum
    const y = weights.reduce((s, w, i) => s + w * anchors[i].y, 0) / sum
    const dominantIdx = weights.indexOf(Math.max(...weights))
    const size = 8 + Math.min(20, Math.sqrt(toNum(row.job_count)) / 6)
    const selected = selectedSet.has(row.company_type)
    return {
      value: [x, y, size],
      name: row.company_type,
      itemStyle: {
        color: palette[dominantIdx],
        opacity: selected ? 1 : 0.72,
        borderColor: selected ? '#fff3bf' : '#102f54',
        borderWidth: selected ? 2 : 1
      },
      raw: row
    }
  })

  const anchorPoints = anchors.map(a => ({
    value: [a.x * 1.06, a.y * 1.06],
    name: a.label,
    itemStyle: { color: a.color }
  }))

  const circlePoints = Array.from({ length: 180 }, (_, i) => {
    const t = (Math.PI * 2 * i) / 179
    return [Math.cos(t), Math.sin(t)]
  })

  return {
    backgroundColor: 'rgba(8,24,46,0.82)',
    xAxis: { min: -1.2, max: 1.2, show: false },
    yAxis: { min: -1.2, max: 1.2, show: false },
    tooltip: {
      formatter: p => {
        if (!p.data?.raw) return p.name
        const r = p.data.raw
        return `${r.company_type}<br/>薪资: ${toNum(r.avg_median_salary).toFixed(2)}<br/>经验: ${toNum(r.avg_experience_rank).toFixed(2)}<br/>学历: ${toNum(r.avg_education_rank).toFixed(2)}<br/>城市等级: ${toNum(r.avg_city_tier_score).toFixed(2)}<br/>规模: ${toNum(r.job_count).toFixed(0)}`
      }
    },
    series: [
      {
        type: 'line',
        data: circlePoints,
        symbol: 'none',
        lineStyle: { color: 'rgba(115,170,230,0.45)', width: 1.5 },
        silent: true
      },
      {
        type: 'scatter',
        data: anchorPoints,
        symbolSize: 12,
        label: { show: true, formatter: '{b}', color: '#cde7ff', position: 'top' },
        z: 4,
        silent: true
      },
      {
        type: 'scatter',
        data: points,
        symbolSize: d => d[2],
        label: {
          show: false,
          formatter: p => shortName(p.name)
        },
        emphasis: {
          focus: 'self',
          label: { show: true, color: '#fff0c2' }
        },
        z: 3
      }
    ]
  }
}

const renderChart = () => {
  if (!chartInstance) return
  const option = buildOption()
  if (!option) {
    chartInstance.clear()
    return
  }
  chartInstance.setOption(option, true)
}

const ensureChart = () => {
  if (!chartContainer.value) return false
  if (!chartInstance) chartInstance = echarts.init(chartContainer.value)
  return true
}

const loadData = async () => {
  const res = await getNationalIndustryScatter()
  rawData.value = res?.data || []
  renderChart()
}

const handleResize = () => chartInstance && chartInstance.resize()

onMounted(async () => {
  await loadData()
  window.addEventListener('resize', handleResize)
})

watch(() => props.selectedIndustries, () => {
  if (!hasSelection.value && chartInstance) {
    chartInstance.clear()
    return
  }
  nextTick(() => {
    if (ensureChart()) {
      chartInstance.resize()
      renderChart()
    }
  })
}, { deep: true })

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) chartInstance.dispose()
  chartInstance = null
})
</script>

<style scoped>
.chart-container { width: 100%; min-height: 320px; height: 100%; }

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

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: #89add0;
}
</style>
