<template>
  <div class="geo-wrap" :style="{ height: `${chartHeight}px` }">
    <div ref="chartRef" class="geo-chart"></div>
    <div v-if="loading" class="geo-state">正在计算城市偏好分布...</div>
    <div v-else-if="!markers.length" class="geo-state">选择职位后点击【同步分析】生成偏好城市图</div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, watch, ref } from 'vue'
import * as echarts from 'echarts'
import chinaJson from '@/assets/map/china.json'

const props = defineProps({
  markers: {
    type: Array,
    default: () => []
  },
  activeJobSlots: {
    type: Array,
    default: () => ['A', 'B', 'C']
  },
  loading: {
    type: Boolean,
    default: false
  },
  selectedCode: {
    type: String,
    default: ''
  },
  chartHeight: {
    type: Number,
    default: 560
  },
  mapLayoutSize: {
    type: Number,
    default: 118
  },
  mapCenterX: {
    type: Number,
    default: 50
  },
  mapCenterY: {
    type: Number,
    default: 70
  },
  mapZoom: {
    type: Number,
    default: 1.18
  },
  mapAspectScale: {
    type: Number,
    default: 0.75
  }
})

const emit = defineEmits(['select-city', 'hover-city', 'view-change'])

const chartRef = ref(null)
let chartInstance = null

const JOB_COLORS = ['#2f6df6', '#f06449', '#36b87c']
const SLOT_INDEX_MAP = { A: 0, B: 1, C: 2 }
let mapRegistered = false
const currentView = ref({
  zoom: 1,
  centerX: 50,
  centerY: 50
})
const FILTERED_CHINA_GEOJSON = {
  ...chinaJson,
  features: (chinaJson.features || []).filter((f) => {
    const name = f?.properties?.name || ''
    // 去掉南海诸岛插图，避免主图在宽屏中显得过小
    return !name.includes('南海诸岛')
  })
}

const toNumber = (v, fallback = 0) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

const hexToRgba = (hex, alpha = 1) => {
  if (!hex || typeof hex !== 'string') return `rgba(94,216,255,${alpha})`
  const normalized = hex.replace('#', '')
  const full = normalized.length === 3
    ? normalized.split('').map((c) => c + c).join('')
    : normalized
  if (full.length !== 6) return `rgba(94,216,255,${alpha})`
  const r = Number.parseInt(full.slice(0, 2), 16)
  const g = Number.parseInt(full.slice(2, 4), 16)
  const b = Number.parseInt(full.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

const activeIndexes = () => {
  const fromProps = (props.activeJobSlots || [])
    .map((slot) => SLOT_INDEX_MAP[String(slot || '').trim().toUpperCase()])
    .filter((idx) => Number.isInteger(idx) && idx >= 0 && idx <= 2)
  return fromProps.length ? Array.from(new Set(fromProps)) : [0, 1, 2]
}

const buildSeriesData = () => {
  if (!props.markers.length) return []
  const indexes = activeIndexes()

  const totals = props.markers
    .map((m) => {
      const counts = [toNumber(m.counts?.[0], 0), toNumber(m.counts?.[1], 0), toNumber(m.counts?.[2], 0)]
      return indexes.reduce((sum, idx) => sum + Math.max(0, counts[idx] || 0), 0)
    })
    .filter((v) => v > 0)
  if (!totals.length) return []

  const minV = Math.min(...totals)
  const maxV = Math.max(...totals)
  const span = Math.max(maxV - minV, 1)

  return props.markers.map((m) => {
    const originalTotal = Math.max(toNumber(m.total, 0), 1)
    const counts = [toNumber(m.counts?.[0], 0), toNumber(m.counts?.[1], 0), toNumber(m.counts?.[2], 0)]
    const activeTotal = indexes.reduce((sum, idx) => sum + Math.max(0, counts[idx] || 0), 0)
    if (activeTotal <= 0) return null
    const norm = (activeTotal - minV) / span
    const radius = 8 + norm * 14
    const selected = m.code === props.selectedCode
    const singleIndex = indexes.length === 1 ? indexes[0] : -1
    const dotColor = singleIndex >= 0 ? JOB_COLORS[singleIndex] : '#58d3ff'
    const activeRatios = counts.map((v, idx) => {
      if (!indexes.includes(idx) || activeTotal <= 0) return 0
      return Number(((v / activeTotal) * 100).toFixed(2))
    })

    return {
      name: m.code,
      code: m.code,
      mappedCity: m.mappedCity,
      mappedLon: toNumber(m.mappedLon),
      mappedLat: toNumber(m.mappedLat),
      counts,
      ratios: m.ratios || [0, 0, 0],
      activeRatios,
      total: activeTotal,
      originalTotal: toNumber(m.total, 0),
      rank: m.rank,
      selected,
      activeSlots: indexes.map((idx) => ['A', 'B', 'C'][idx]),
      itemStyle: {
        color: dotColor,
        borderColor: '#d8f8ff',
        borderWidth: selected ? 2 : 1.3,
        shadowBlur: 22,
        shadowColor: singleIndex >= 0 ? hexToRgba(dotColor, 0.45) : 'rgba(94,216,255,0.45)'
      },
      value: [toNumber(m.mappedLon), toNumber(m.mappedLat), activeTotal, counts[0], counts[1], counts[2], radius, originalTotal]
    }
  }).filter(Boolean)
}

const buildOption = () => {
  const data = buildSeriesData()

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      confine: true,
      borderColor: 'rgba(94,216,255,0.55)',
      backgroundColor: 'rgba(7, 20, 41, 0.94)',
      textStyle: { color: '#d8f4ff', fontSize: 12 },
      formatter: (params) => {
        const d = params.data
        if (!d) return ''
        const activeSlotsText = Array.isArray(d.activeSlots) && d.activeSlots.length ? d.activeSlots.join(' + ') : 'A + B + C'
        return [
          `<div style="font-weight:700; margin-bottom:4px; color:#5ed8ff;">${d.code}</div>`,
          `经纬度：${toNumber(d.mappedLon).toFixed(3)}, ${toNumber(d.mappedLat).toFixed(3)}`,
          `当前筛选（${activeSlotsText}）需求：${d.total}`,
          `全部职位总需求：${d.originalTotal}`,
          `职位A：${d.counts[0]}（${toNumber(d.activeRatios?.[0]).toFixed(2)}%）`,
          `职位B：${d.counts[1]}（${toNumber(d.activeRatios?.[1]).toFixed(2)}%）`,
          `职位C：${d.counts[2]}（${toNumber(d.activeRatios?.[2]).toFixed(2)}%）`
        ].join('<br/>')
      }
    },
    geo: {
      map: 'china-q2',
      roam: true,
      scaleLimit: {
        min: 0.7,
        max: 3.2
      },
      selectedMode: false,
      zoom: currentView.value.zoom,
      layoutCenter: [`${currentView.value.centerX}%`, `${currentView.value.centerY}%`],
      layoutSize: `${props.mapLayoutSize}%`,
      aspectScale: props.mapAspectScale,
      itemStyle: {
        areaColor: '#edf3fc',
        borderColor: '#8eb3e4',
        borderWidth: 0.9,
        shadowBlur: 10,
        shadowColor: 'rgba(68, 111, 171, 0.16)'
      },
      emphasis: {
        itemStyle: {
          areaColor: '#dfeaf9'
        },
        disabled: true
      }
    },
    series: [
      {
        type: 'scatter',
        coordinateSystem: 'geo',
        z: 4,
        silent: true,
        symbol: 'circle',
        data,
        symbolSize: (val) => Math.max(10, Number(val?.[6] || 10) + 8),
        itemStyle: {
          color: 'rgba(94,216,255,0.14)',
          borderColor: 'rgba(138,232,255,0.36)',
          borderWidth: 1,
          shadowBlur: 18,
          shadowColor: 'rgba(44, 166, 255, 0.35)'
        }
      },
      {
        type: 'effectScatter',
        coordinateSystem: 'geo',
        z: 8,
        data,
        showEffectOn: 'render',
        rippleEffect: {
          period: 4.2,
          scale: 2.9,
          brushType: 'stroke'
        },
        symbol: 'circle',
        symbolSize: (val, params) => {
          const base = Math.max(8, Number(val?.[6] || 8))
          return params?.data?.selected ? base + 4 : base
        },
        itemStyle: {
          color: '#58d3ff',
          borderColor: '#d8f8ff',
          borderWidth: 1.3,
          shadowBlur: 22,
          shadowColor: 'rgba(94,216,255,0.45)'
        },
        emphasis: {
          scale: 1.14,
          itemStyle: {
            borderWidth: 2
          },
          label: {
            show: true,
            formatter: ({ data }) => data?.code || '',
            color: '#9ee9ff',
            fontSize: 12,
            fontWeight: 700,
            position: 'right',
            distance: 7,
            backgroundColor: 'rgba(8,24,46,0.86)',
            borderColor: 'rgba(94,216,255,0.42)',
            borderWidth: 1,
            borderRadius: 6,
            padding: [3, 6]
          }
        }
      }
    ]
  }
}

const renderChart = async () => {
  if (!chartRef.value) return
  await nextTick()

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)

    chartInstance.on('click', (params) => {
      const code = params?.data?.code
      if (code) emit('select-city', code)
    })

    chartInstance.on('mouseover', (params) => {
      const code = params?.data?.code
      emit('hover-city', code || '')
    })

    chartInstance.on('mouseout', () => {
      emit('hover-city', '')
    })

    // 记录当前视图状态，便于后续手动平移/缩放不被重置
    chartInstance.on('georoam', (eventParams) => {
      const geoOpt = chartInstance.getOption()?.geo?.[0] || {}
      currentView.value.zoom = Number(geoOpt.zoom || currentView.value.zoom)
      if (Array.isArray(geoOpt.layoutCenter)) {
        const cx = Number.parseFloat(String(geoOpt.layoutCenter[0]))
        const cy = Number.parseFloat(String(geoOpt.layoutCenter[1]))
        if (Number.isFinite(cx)) currentView.value.centerX = cx
        if (Number.isFinite(cy)) currentView.value.centerY = cy
      }
      emit('view-change', { ...currentView.value, event: eventParams || null })
    })
  }

  if (!mapRegistered) {
    echarts.registerMap('china-q2', FILTERED_CHINA_GEOJSON)
    mapRegistered = true
  }

  chartInstance.setOption(buildOption(), true)
}

const resizeChart = () => {
  chartInstance?.resize()
}

const clamp = (v, min, max) => Math.max(min, Math.min(max, v))

const emitViewChange = (event = null) => {
  emit('view-change', {
    zoom: Number(currentView.value.zoom),
    centerX: Number(currentView.value.centerX),
    centerY: Number(currentView.value.centerY),
    event
  })
}

const syncViewFromProps = () => {
  currentView.value.zoom = clamp(Number(props.mapZoom || 1), 0.7, 3.2)
  currentView.value.centerX = clamp(Number(props.mapCenterX || 50), 5, 95)
  currentView.value.centerY = clamp(Number(props.mapCenterY || 50), 5, 95)
}

const zoomBy = (factor) => {
  if (!chartInstance) return
  const nextZoom = clamp(currentView.value.zoom * factor, 0.7, 3.2)
  currentView.value.zoom = nextZoom
  chartInstance.setOption(
    {
      geo: {
        zoom: nextZoom,
        layoutCenter: [`${currentView.value.centerX}%`, `${currentView.value.centerY}%`]
      }
    },
    false
  )
  emitViewChange({ source: 'button-zoom' })
}

const panByPercent = (dxPercent, dyPercent) => {
  if (!chartInstance) return
  currentView.value.centerX = clamp(currentView.value.centerX + dxPercent, 5, 95)
  currentView.value.centerY = clamp(currentView.value.centerY + dyPercent, 5, 95)
  chartInstance.setOption(
    {
      geo: {
        zoom: currentView.value.zoom,
        layoutCenter: [`${currentView.value.centerX}%`, `${currentView.value.centerY}%`]
      }
    },
    false
  )
  emitViewChange({ source: 'button-pan' })
}

const resetView = () => {
  if (!chartInstance) return
  currentView.value = {
    zoom: Number(props.mapZoom || 1),
    centerX: Number(props.mapCenterX || 50),
    centerY: Number(props.mapCenterY || 50)
  }
  chartInstance.setOption(
    {
      geo: {
        zoom: currentView.value.zoom,
        layoutCenter: [`${currentView.value.centerX}%`, `${currentView.value.centerY}%`]
      }
    },
    false
  )
  emitViewChange({ source: 'button-reset' })
}

watch(
  () => [
    props.markers,
    props.activeJobSlots,
    props.loading,
    props.selectedCode,
    props.chartHeight,
    props.mapLayoutSize,
    props.mapCenterX,
    props.mapCenterY,
    props.mapZoom,
    props.mapAspectScale
  ],
  () => {
    renderChart().then(() => resizeChart())
  },
  { deep: true }
)

watch(
  () => [props.mapCenterX, props.mapCenterY, props.mapZoom],
  () => {
    syncViewFromProps()
    if (!chartInstance) return
    chartInstance.setOption(
      {
        geo: {
          zoom: currentView.value.zoom,
          layoutCenter: [`${currentView.value.centerX}%`, `${currentView.value.centerY}%`]
        }
      },
      false
    )
  }
)

onMounted(() => {
  syncViewFromProps()
  renderChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

defineExpose({
  zoomIn: () => zoomBy(1.12),
  zoomOut: () => zoomBy(1 / 1.12),
  panLeft: () => panByPercent(-2, 0),
  panRight: () => panByPercent(2, 0),
  panUp: () => panByPercent(0, -2),
  panDown: () => panByPercent(0, 2),
  resetView
})
</script>

<style scoped>
.geo-wrap {
  position: relative;
  width: 100%;
  min-height: 360px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(80, 111, 174, 0.14);
  background: radial-gradient(circle at 12% 12%, #f3f7ff 0%, #eef3fb 35%, #e9eef8 100%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.86), 0 10px 24px rgba(64, 89, 138, 0.12);
}

.geo-wrap::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 8% 4%, rgba(66, 124, 211, 0.12), transparent 36%),
    radial-gradient(circle at 95% 82%, rgba(130, 164, 220, 0.12), transparent 42%);
  pointer-events: none;
  z-index: 0;
}

.geo-chart {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  min-height: 360px;
}

.geo-state {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4a6896;
  font-weight: 700;
  background: rgba(236, 243, 252, 0.78);
  z-index: 2;
  pointer-events: none;
}
</style>
