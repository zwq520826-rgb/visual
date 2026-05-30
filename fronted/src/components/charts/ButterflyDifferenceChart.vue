<template>
  <div class="butterfly-diff-chart">
    <div v-show="selectedJobs.length < 2" class="no-data-message">
      <p>请从散点图中选择2个职位进行1v1对比</p>
      <p class="hint">蝴蝶图可沿中轴快速识别双方强弱项</p>
    </div>
    <div v-show="selectedJobs.length > 2" class="warning-message">
      <p>蝴蝶图仅支持2个职位</p>
      <p class="hint">当前已选择 {{ selectedJobs.length }} 个职位</p>
    </div>
    <div v-show="selectedJobs.length === 2" ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({ selectedJobs: { type: Array, default: () => [] } })

const chartContainer = ref(null)
let chartInstance = null

const dims = [
  { key: 'avg_salary', label: '平均薪资', unit: 'K' },
  { key: 'avg_experience', label: '经验要求', unit: '' },
  { key: 'avg_education', label: '学历要求', unit: '' },
  { key: 'job_in_city_cnt', label: '招聘人数', unit: '' },
  { key: 'salary_std', label: '薪资波动', unit: 'K' },
  { key: 'avg_shannon_entropy', label: '香农熵', unit: '' }
]

const toNum = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const shortName = (name) => {
  const s = String(name || '')
  return s.length <= 18 ? s : `${s.slice(0, 8)}...${s.slice(-6)}`
}

const updateChart = () => {
  if (!chartInstance || props.selectedJobs.length !== 2) return
  const [a, b] = props.selectedJobs

  const pairRows = dims.map(d => {
    const av = toNum(a[d.key])
    const bv = toNum(b[d.key])
    const total = av + bv
    if (total <= 0) {
      return {
        label: d.label,
        leftPct: 0,
        rightPct: 0,
        aRaw: av,
        bRaw: bv,
        unit: d.unit
      }
    }
    return {
      label: d.label,
      leftPct: (av / total) * 100,
      rightPct: (bv / total) * 100,
      aRaw: av,
      bRaw: bv,
      unit: d.unit
    }
  })

  const left = pairRows.map(r => -r.leftPct)
  const right = pairRows.map(r => r.rightPct)
  const aName = a.job_title || '职位A'
  const bName = b.job_title || '职位B'

  chartInstance.setOption({
    backgroundColor: 'rgba(8,24,46,0.82)',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: params => {
        const i = params[0].dataIndex
        const row = pairRows[i]
        return `${row.label}<br/>${a.job_title}: ${row.leftPct.toFixed(1)}%（${row.aRaw.toFixed(2)}${row.unit}）<br/>${b.job_title}: ${row.rightPct.toFixed(1)}%（${row.bRaw.toFixed(2)}${row.unit}）`
      }
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      left: 8,
      top: 14,
      itemWidth: 12,
      itemHeight: 12,
      formatter: name => shortName(name),
      textStyle: { color: '#cde7ff', width: 190, overflow: 'truncate' },
      data: [aName, bName]
    },
    grid: { left: 120, right: 70, top: 72, bottom: 20 },
    xAxis: {
      type: 'value',
      min: -100,
      max: 100,
      axisLabel: { color: '#bcdcff', formatter: v => `${Math.abs(v)}` },
      splitLine: { lineStyle: { color: 'rgba(114,181,255,0.2)' } }
    },
    yAxis: {
      type: 'category',
      axisLabel: { color: '#d6ebff' },
      data: pairRows.map(r => r.label)
    },
    series: [
      {
        name: aName,
        type: 'bar',
        data: left,
        itemStyle: { color: '#2d7bff' },
        label: {
          show: true,
          position: 'left',
          color: '#8bc3ff',
          formatter: p => `${Math.abs(p.value).toFixed(1)}%`
        }
      },
      {
        name: bName,
        type: 'bar',
        data: right,
        itemStyle: { color: '#00d7ff' },
        label: {
          show: true,
          position: 'right',
          color: '#8ff2ff',
          formatter: p => `${p.value.toFixed(1)}%`
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
.no-data-message, .warning-message { color: #9ac4ec; text-align: center; padding: 24px 12px; }
.hint { font-size: 12px; opacity: 0.8; }
</style>
