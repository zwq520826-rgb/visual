<template>
  <div class="region-cluster-wrap">
    <div class="chart-pane">
      <div class="pane-head">
        <h3>视图 A：地域招聘画像散点图</h3>
        <p>{{ chartDesc }}</p>
        <div class="axis-controls">
          <label>
            <span>X 轴</span>
            <select v-model="axisX">
              <option v-for="opt in axisOptions" :key="`x-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
            </select>
          </label>
          <label>
            <span>Y 轴</span>
            <select v-model="axisY">
              <option v-for="opt in axisOptions" :key="`y-${opt.value}`" :value="opt.value">{{ opt.label }}</option>
            </select>
          </label>
        </div>
      </div>

      <div v-if="error" class="state-box error">{{ error }}</div>
      <div v-else-if="loading" class="state-box">加载中...</div>
      <div v-else-if="!regions.length" class="state-box">暂无地域散点数据</div>
      <div v-else ref="chartRef" class="cluster-chart"></div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  regions: { type: Array, default: () => [] },
  clusterSummary: { type: Array, default: () => [] },
  metadata: { type: Object, default: null },
  selectedRegionId: { type: String, default: null },
  selectedClusterId: { type: Number, default: null },
  focusCityId: { type: String, default: null },
  heatmapSimilarRegions: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' }
})

const emit = defineEmits(['select-region', 'select-cluster'])

const chartRef = ref(null)
let chart = null

const axisOptions = [
  { value: 'finance_maturity', label: '薪资成熟度' },
  { value: 'skill_concentration', label: '技能/行业集中度' },
  { value: 'scale_intensity', label: '招聘规模强度' },
  { value: 'education_level', label: '学历门槛强度' },
  { value: 'experience_demand', label: '经验门槛强度' },
  { value: 'salary_median', label: '中位薪资' },
  { value: 'salary_mean', label: '平均薪资' },
  { value: 'job_count_log', label: '岗位规模(log)' }
]

const axisX = ref('finance_maturity')
const axisY = ref('skill_concentration')

const labelMap = computed(() => {
  const m = {}
  axisOptions.forEach((o) => { m[o.value] = o.label })
  return m
})

const chartDesc = computed(() => `横轴 ${labelMap.value[axisX.value]}，纵轴 ${labelMap.value[axisY.value]}；每个散点是一个城市地域，点大小表示岗位规模，颜色表示相似地域簇。`)

const hashUnit = (text, salt = 0) => {
  const s = `${text || ''}_${salt}`
  let h = 0
  for (let i = 0; i < s.length; i += 1) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0
  }
  return Math.abs(h % 100000) / 100000
}

const valueOf = (r, key) => {
  if (key === 'job_count_log') return Math.log1p(Math.max(0, Number(r.job_count || 0)))
  return Number(r?.[key] ?? 0)
}

const axisStats = computed(() => {
  const xs = props.regions.map((r) => valueOf(r, axisX.value)).filter((v) => Number.isFinite(v))
  const ys = props.regions.map((r) => valueOf(r, axisY.value)).filter((v) => Number.isFinite(v))
  const xMin = xs.length ? Math.min(...xs) : 0
  const xMax = xs.length ? Math.max(...xs) : 1
  const yMin = ys.length ? Math.min(...ys) : 0
  const yMax = ys.length ? Math.max(...ys) : 1
  const dx = Math.max(1e-9, xMax - xMin)
  const dy = Math.max(1e-9, yMax - yMin)
  return { xMin, xMax, yMin, yMax, dx, dy }
})

const coordMap = computed(() => {
  const map = new Map()
  const { dx, dy } = axisStats.value
  props.regions.forEach((r) => {
    const xRaw = valueOf(r, axisX.value)
    const yRaw = valueOf(r, axisY.value)
    const jitterX = (hashUnit(r.region_id, 11) - 0.5) * dx * 0.06
    const jitterY = (hashUnit(r.region_id, 17) - 0.5) * dy * 0.06
    map.set(r.region_id, {
      x: xRaw + jitterX,
      y: yRaw + jitterY,
      xRaw,
      yRaw
    })
  })
  return map
})

const extent = computed(() => {
  const vals = [...coordMap.value.values()]
  if (!vals.length) return { minX: 0, maxX: 1, minY: 0, maxY: 1 }
  const xs = vals.map((v) => v.x)
  const ys = vals.map((v) => v.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const dx = Math.max(1e-9, maxX - minX)
  const dy = Math.max(1e-9, maxY - minY)
  return {
    minX: minX - dx * 0.08,
    maxX: maxX + dx * 0.08,
    minY: minY - dy * 0.08,
    maxY: maxY + dy * 0.08
  }
})

const sizeStats = computed(() => {
  const counts = props.regions.map((r) => Number(r.job_count || 0)).filter((n) => Number.isFinite(n) && n >= 0)
  if (!counts.length) return { minLog: 0, maxLog: 1 }
  return {
    minLog: Math.log1p(Math.min(...counts)),
    maxLog: Math.log1p(Math.max(...counts))
  }
})

const symbolSize = (count) => {
  const c = Math.max(0, Number(count || 0))
  const { minLog, maxLog } = sizeStats.value
  if (maxLog <= minLog) return 16
  const t = (Math.log1p(c) - minLog) / (maxLog - minLog)
  return 8 + t * 30
}

const visibleRegions = computed(() => {
  if (props.selectedClusterId === null) return props.regions
  return props.regions.filter((r) => Number(r.cluster_id) === Number(props.selectedClusterId))
})

const clusterIds = computed(() => [...new Set(props.regions.map((r) => Number(r.cluster_id)).filter((v) => Number.isFinite(v)))].sort((a, b) => a - b))
const COLOR = ['#2f6ed8', '#33a06f', '#e19a32', '#8e77cf', '#db5f7b', '#2cb1bc', '#f08a24', '#4b6cb7']
const clusterColor = (cid) => {
  const idx = clusterIds.value.indexOf(Number(cid))
  return COLOR[idx >= 0 ? idx % COLOR.length : 0]
}

const summaryLabelMap = computed(() => {
  const m = {}
  ;(props.clusterSummary || []).forEach((c) => {
    m[Number(c.cluster_id)] = c.cluster_label || `簇${c.cluster_id}`
  })
  return m
})

const similarMap = computed(() => {
  const m = new Map()
  ;(props.heatmapSimilarRegions || []).forEach((it) => {
    if (it?.city) m.set(String(it.city), Number(it.similarity || 0))
  })
  return m
})

const selectedRegion = computed(() => props.regions.find((r) => r.region_id === props.selectedRegionId) || null)

const buildSeries = () => {
  const grouped = new Map()
  visibleRegions.value.forEach((r) => {
    const cid = Number(r.cluster_id)
    if (!grouped.has(cid)) grouped.set(cid, [])
    grouped.get(cid).push(r)
  })

  const series = []
  grouped.forEach((rows, cid) => {
    series.push({
      name: `C${cid} ${summaryLabelMap.value[cid] || ''}`,
      type: 'scatter',
      data: rows.map((r) => {
        const p = coordMap.value.get(r.region_id) || { x: 0, y: 0, xRaw: 0, yRaw: 0 }
        return {
          value: [p.x, p.y, Number(r.job_count || 0)],
          region_id: r.region_id,
          region_label: r.region_label,
          city_tier: r.city_tier,
          cluster_id: cid,
          salary_mean: r.salary_mean,
          salary_median: r.salary_median,
          xRaw: p.xRaw,
          yRaw: p.yRaw,
          industry_top: r.industry_top || []
        }
      }),
      symbolSize: (_v, params) => symbolSize(params?.data?.value?.[2]),
      itemStyle: {
        color: clusterColor(cid),
        opacity: 0.82
      },
      emphasis: {
        scale: 1.18,
        itemStyle: { opacity: 1 }
      },
      z: 3
    })
  })

  const focus = props.focusCityId || selectedRegion.value?.region_id || null
  const byId = new Map(props.regions.map((r) => [r.region_id, r]))
  const lineData = []
  if (focus && byId.has(focus) && coordMap.value.has(focus)) {
    const from = coordMap.value.get(focus)
    similarMap.value.forEach((sim, city) => {
      if (!byId.has(city) || !coordMap.value.has(city)) return
      const to = coordMap.value.get(city)
      lineData.push({
        coords: [[from.x, from.y], [to.x, to.y]],
        similarity: sim,
        to_city: city
      })
    })
  }

  if (lineData.length) {
    series.push({
      name: 'similar-links',
      type: 'lines',
      coordinateSystem: 'cartesian2d',
      data: lineData,
      z: 9,
      lineStyle: {
        width: 1.3,
        opacity: 0.58,
        color: '#5f79aa'
      },
      effect: {
        show: true,
        symbol: 'circle',
        symbolSize: 4,
        trailLength: 0.2
      },
      tooltip: {
        formatter: (p) => `相似度：${(Number(p?.data?.similarity || 0) * 100).toFixed(1)}%`
      }
    })
  }

  return series
}

const render = () => {
  if (!chartRef.value || !props.regions.length) return
  if (chart) chart.dispose()
  chart = echarts.init(chartRef.value)

  chart.setOption({
    grid: { left: 70, right: 16, top: 56, bottom: 56 },
    legend: {
      top: 6,
      textStyle: { color: '#4f6f9f', fontSize: 12 }
    },
    xAxis: {
      type: 'value',
      min: extent.value.minX,
      max: extent.value.maxX,
      name: labelMap.value[axisX.value],
      nameLocation: 'middle',
      nameGap: 32,
      axisLine: { lineStyle: { color: '#9cb4d8' } },
      splitLine: { lineStyle: { color: '#ecf1fb' } },
      axisLabel: { color: '#6a86af' }
    },
    yAxis: {
      type: 'value',
      min: extent.value.minY,
      max: extent.value.maxY,
      name: labelMap.value[axisY.value],
      nameLocation: 'middle',
      nameGap: 46,
      axisLine: { lineStyle: { color: '#9cb4d8' } },
      splitLine: { lineStyle: { color: '#eef3fb' } },
      axisLabel: { color: '#6a86af' }
    },
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (params?.seriesType === 'lines') {
          return params?.data?.similarity ? `相似度：${(params.data.similarity * 100).toFixed(1)}%` : ''
        }
        const d = params.data || {}
        const inds = Array.isArray(d.industry_top) ? d.industry_top.slice(0, 3).join(' / ') : '-'
        return [
          `<strong>${d.region_label || ''} ${d.region_id || ''}</strong>`,
          `簇：C${d.cluster_id ?? '-'} ${summaryLabelMap.value[Number(d.cluster_id)] || ''}`,
          `岗位数量：${Number(d.value?.[2] || 0).toLocaleString()}`,
          `${labelMap.value[axisX.value]}：${Number(d.xRaw || 0).toFixed(4)}`,
          `${labelMap.value[axisY.value]}：${Number(d.yRaw || 0).toFixed(4)}`,
          `平均薪资：${Number(d.salary_mean || 0).toFixed(2)}`,
          `主导行业：${inds}`
        ].join('<br/>')
      }
    },
    series: buildSeries()
  })

  chart.off('click')
  chart.on('click', (params) => {
    const rid = params?.data?.region_id
    if (rid) emit('select-region', rid)
  })
}

watch([axisX, axisY], () => {
  if (axisX.value === axisY.value) {
    const fallback = axisOptions.find((o) => o.value !== axisX.value)
    if (fallback) axisY.value = fallback.value
  }
})

watch(
  () => [props.regions, props.selectedRegionId, props.selectedClusterId, props.focusCityId, props.heatmapSimilarRegions, axisX.value, axisY.value],
  () => nextTick(() => render()),
  { deep: true }
)

onMounted(() => nextTick(() => render()))
onUnmounted(() => {
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.region-cluster-wrap {
  min-height: 520px;
}

.chart-pane {
  border: 1px solid #cddcf2;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
  min-height: 0;
}

.pane-head h3 {
  margin: 0;
  font-size: 18px;
  color: #2b4f86;
}

.pane-head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #6f88af;
}

.axis-controls {
  margin-top: 8px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.axis-controls label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #456792;
}

.axis-controls select {
  border: 1px solid #c8d9f0;
  border-radius: 8px;
  padding: 4px 8px;
  background: #f8fbff;
  color: #2d5587;
}

.cluster-chart {
  margin-top: 8px;
  height: 460px;
}

.state-box {
  margin-top: 10px;
  min-height: 200px;
  border: 1px dashed #c0d3ef;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6f88af;
  font-size: 13px;
}

.state-box.error {
  border-color: #ecc8c8;
  color: #b05050;
}
</style>
