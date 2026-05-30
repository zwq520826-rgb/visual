<template>
  <div class="industry-difference-heatmap">
    <div v-if="!hasSelection" class="empty-state">
      <p>请先在左侧散点图中选择行业</p>
      <p class="hint">至少选择 1 个行业后显示差异矩阵热力图</p>
    </div>
    <template v-else>
      <div class="chart-note">当前已选择 {{ selectedCount }} 个行业，按所选行业展示差异矩阵。</div>
      <div ref="chartContainer" class="chart-container"></div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getNationalIndustryScatter } from '@/api/q1Api'

const props = defineProps({
  selectedIndustries: { type: Array, default: () => [] }
})

const chartContainer = ref(null)
let chartInstance = null
const rawData = ref([])

const DIMENSIONS = [
  { key: 'avg_median_salary', label: '平均薪资' },
  { key: 'avg_experience_rank', label: '经验要求' },
  { key: 'avg_education_rank', label: '学历要求' },
  { key: 'avg_city_tier_score', label: '城市等级' },
  { key: 'job_count', label: '招聘总数' }
]

const toNum = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const shortName = (name) => {
  const s = String(name || '')
  return s.length <= 14 ? s : `${s.slice(0, 6)}...${s.slice(-4)}`
}

const selectedCount = computed(() => (props.selectedIndustries || []).length)
const hasSelection = computed(() => selectedCount.value > 0)

const buildOption = () => {
  const selectedSet = new Set((props.selectedIndustries || []).map(i => i.company_type))
  if (selectedSet.size === 0) {
    return null
  }
  const sorted = [...rawData.value].sort((a, b) => toNum(b.job_count) - toNum(a.job_count))
  const selectedRows = sorted.filter(r => selectedSet.has(r.company_type))
  const rows = selectedRows

  const means = {}
  const stds = {}
  DIMENSIONS.forEach(dim => {
    const vals = rawData.value.map(r => toNum(r[dim.key]))
    const mean = vals.reduce((s, v) => s + v, 0) / (vals.length || 1)
    const variance = vals.reduce((s, v) => s + (v - mean) * (v - mean), 0) / (vals.length || 1)
    means[dim.key] = mean
    stds[dim.key] = Math.sqrt(variance) || 1
  })

  const yLabels = rows.map(r => r.company_type)
  const heatData = []
  rows.forEach((row, y) => {
    DIMENSIONS.forEach((dim, x) => {
      const z = (toNum(row[dim.key]) - means[dim.key]) / stds[dim.key]
      const clipped = Math.max(-2.5, Math.min(2.5, z))
      heatData.push({
        value: [x, y, clipped],
        rowName: row.company_type,
        dimLabel: dim.label,
        rawVal: toNum(row[dim.key]),
        zScore: clipped
      })
    })
  })

  return {
    backgroundColor: 'rgba(8,24,46,0.82)',
    tooltip: {
      position: 'top',
      formatter: p => {
        const rowName = p.data?.rowName || '-'
        const dimLabel = p.data?.dimLabel || '-'
        const rawVal = Number(p.data?.rawVal || 0)
        const zScore = Number(p.data?.zScore || 0)
        return `${rowName}<br/>${dimLabel}: ${rawVal.toFixed(2)}<br/>偏离均值: ${zScore.toFixed(2)}σ`
      }
    },
    grid: { left: 90, right: 24, top: 40, bottom: 50 },
    xAxis: {
      type: 'category',
      data: DIMENSIONS.map(d => d.label),
      axisLabel: { color: '#cde7ff', interval: 0 }
    },
    yAxis: {
      type: 'category',
      data: yLabels,
      axisLabel: {
        color: '#b9d8f6',
        formatter: v => selectedSet.has(v) ? `* ${shortName(v)}` : shortName(v)
      }
    },
    visualMap: {
      min: -2.5,
      max: 2.5,
      orient: 'horizontal',
      left: 'center',
      bottom: 8,
      text: ['高于均值', '低于均值'],
      textStyle: { color: '#cde7ff' },
      inRange: { color: ['#2057b5', '#a8ddff', '#f9f9f9', '#ffd2b8', '#c93a3a'] }
    },
    series: [
      {
        type: 'heatmap',
        coordinateSystem: 'cartesian2d',
        encode: { x: 0, y: 1, value: 2 },
        data: heatData,
        label: { show: false },
        itemStyle: {
          borderColor: 'rgba(8,24,46,0.35)',
          borderWidth: 1
        },
        emphasis: {
          itemStyle: {
            borderColor: '#fff7cf',
            borderWidth: 1.5
          }
        }
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
  if (!chartInstance) {
    chartInstance = echarts.init(chartContainer.value)
  }
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
.chart-note {
  color: #9fc3e5;
  font-size: 12px;
  margin: 0 0 8px 2px;
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

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: #89add0;
}
</style>
