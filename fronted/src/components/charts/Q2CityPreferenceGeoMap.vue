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
let renderRafId = 0
let resizeRafId = 0

const JOB_COLORS = ['#4d7dff', '#ff7a63', '#41be88']
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

  // 半径映射：需求越大环形越大（采用 log 非线性，避免极端值把其余点压扁）
  const minV = Math.min(...totals)
  const maxV = Math.max(...totals)
  const minL = Math.log1p(minV)
  const maxL = Math.log1p(maxV)
  const spanL = Math.max(maxL - minL, 1e-6)
  const minRadius = 4.8
  const maxRadius = 12.8

  return props.markers.map((m) => {
    const originalTotal = Math.max(toNumber(m.total, 0), 1)
    const counts = [toNumber(m.counts?.[0], 0), toNumber(m.counts?.[1], 0), toNumber(m.counts?.[2], 0)]
    const activeTotal = indexes.reduce((sum, idx) => sum + Math.max(0, counts[idx] || 0), 0)
    if (activeTotal <= 0) return null
    const norm = (Math.log1p(activeTotal) - minL) / spanL
    const eased = Math.pow(Math.max(0, Math.min(1, norm)), 0.72)
    const radius = Math.round((minRadius + eased * (maxRadius - minRadius)) * 10) / 10
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
      value: [
        toNumber(m.mappedLon),
        toNumber(m.mappedLat),
        activeTotal,
        counts[0],
        counts[1],
        counts[2],
        radius,
        originalTotal,
        selected ? 1 : 0,
        toNumber(m.x, 50),
        toNumber(m.y, 50)
      ]
    }
  }).filter(Boolean)
}

const computeNonOverlapLayout = (data) => {
  if (!Array.isArray(data) || !data.length) {
    return { map: new Map(), hidden: new Set() }
  }

  const width = chartRef.value?.clientWidth || 1200
  const height = chartRef.value?.clientHeight || props.chartHeight || 560
  const margin = 8
  const gap = 3.2

  const points = data.map((d, idx) => {
    const lon = Number(d?.value?.[0] || 0)
    const lat = Number(d?.value?.[1] || 0)
    const fallbackXPct = Number(d?.value?.[9] || 50)
    const fallbackYPct = Number(d?.value?.[10] || 50)
    const fallbackPx = [
      (Math.max(0, Math.min(100, fallbackXPct)) / 100) * width,
      (Math.max(0, Math.min(100, fallbackYPct)) / 100) * height
    ]
    let px = fallbackPx
    if (chartInstance) {
      try {
        const geoPx = chartInstance.convertToPixel({ geoIndex: 0 }, [lon, lat])
        if (Array.isArray(geoPx) && Number.isFinite(geoPx[0]) && Number.isFinite(geoPx[1])) {
          px = geoPx
        }
      } catch (_) {
        px = fallbackPx
      }
    }

    const baseR = Math.max(4.2, Number(d?.value?.[6] || 4.2))
    // 把外圈描边/阴影也算进碰撞半径，避免“视觉上看似重叠”
    const outerR = baseR + 2.2 + 2.2

    return {
      key: String(idx),
      idx,
      x: px[0],
      y: px[1],
      r: outerR
    }
  })

  // 第一步：重叠裁剪（同区域重叠只保留更大的）
  const hidden = new Set()
  const kept = []
  const byRadius = [...points].sort((a, b) => b.r - a.r)
  for (const p of byRadius) {
    const overlapped = kept.some((k) => {
      const dx = p.x - k.x
      const dy = p.y - k.y
      const dist = Math.hypot(dx, dy)
      const minDist = p.r + k.r + gap
      return dist < minDist
    })
    if (overlapped) {
      hidden.add(p.key)
      continue
    }
    kept.push({ ...p })
  }

  // 第二步：对保留点做轻量全局松弛，避免边界碰撞
  const solved = kept.map((p) => ({ ...p }))

  // 全局松弛：双向推开，优先满足“不重叠”
  for (let iter = 0; iter < 140; iter += 1) {
    let moved = false
    for (let i = 0; i < solved.length; i += 1) {
      for (let j = i + 1; j < solved.length; j += 1) {
        const a = solved[i]
        const b = solved[j]
        let dx = b.x - a.x
        let dy = b.y - a.y
        let dist = Math.hypot(dx, dy)
        const minDist = a.r + b.r + gap
        if (dist >= minDist) continue
        moved = true
        if (dist < 0.001) {
          const ang = (((i + 7) * 71 + (j + 13) * 37 + iter * 19) % 360) * Math.PI / 180
          dx = Math.cos(ang)
          dy = Math.sin(ang)
          dist = 1
        }
        const overlap = minDist - dist
        const ux = dx / dist
        const uy = dy / dist
        // 双向分摊位移，质量近似按半径反比
        const wa = 1 / Math.max(1, a.r)
        const wb = 1 / Math.max(1, b.r)
        const wsum = wa + wb
        const moveA = overlap * (wa / wsum)
        const moveB = overlap * (wb / wsum)
        a.x -= ux * moveA
        a.y -= uy * moveA
        b.x += ux * moveB
        b.y += uy * moveB
      }
    }

    for (const p of solved) {
      p.x = Math.max(margin + p.r, Math.min(width - margin - p.r, p.x))
      p.y = Math.max(margin + p.r, Math.min(height - margin - p.r, p.y))
    }

    if (!moved) break
  }

  const byKey = new Map()
  for (const p of solved) {
    byKey.set(p.key, p)
  }

  return { map: byKey, hidden }
}

const buildOption = () => {
  const data = buildSeriesData()
  const idxList = activeIndexes()
  const idxSet = new Set(idxList)
  const slotPalette = JOB_COLORS
  const layoutResult = computeNonOverlapLayout(data)
  const layoutByCode = layoutResult.map
  const hiddenKeys = layoutResult.hidden

  return {
    backgroundColor: 'transparent',
    animation: false,
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
        type: 'custom',
        coordinateSystem: 'geo',
        z: 6,
        data,
        renderItem: (params, api) => {
          const lon = Number(api.value(0))
          const lat = Number(api.value(1))
          const coord = api.coord([lon, lat])
          if (!coord || !Number.isFinite(coord[0]) || !Number.isFinite(coord[1])) return null

          const counts = [
            Math.max(0, Number(api.value(3) || 0)),
            Math.max(0, Number(api.value(4) || 0)),
            Math.max(0, Number(api.value(5) || 0))
          ]
          const totalActive = idxList.reduce((sum, idx) => sum + (idxSet.has(idx) ? counts[idx] : 0), 0)
          if (totalActive <= 0) return null

          const baseR = Math.max(4.2, Number(api.value(6) || 4.2))
          const outerR = baseR + 2.2
          const layoutKey = String(params?.dataIndex)
          if (hiddenKeys.has(layoutKey)) return null
          const layout = layoutByCode.get(layoutKey)
          const cx = layout?.x ?? coord[0]
          const cy = layout?.y ?? coord[1]
          const isSelected = Number(api.value(8) || 0) === 1

          let start = -Math.PI / 2
          const children = []
          const sliceGap = 0.022

          idxList.forEach((idx) => {
            if (!idxSet.has(idx)) return
            const val = counts[idx]
            if (val <= 0) return
            const delta = (val / totalActive) * Math.PI * 2
            if (delta <= 0) return
            const gap = Math.min(sliceGap, delta * 0.3)
            const segStart = start + gap / 2
            const segEnd = start + delta - gap / 2
            if (segEnd <= segStart) {
              start += delta
              return
            }
            children.push({
              type: 'sector',
              shape: {
                cx,
                cy,
                r0: 0,
                r: outerR,
                startAngle: segStart,
                endAngle: segEnd,
                clockwise: true
              },
              style: {
                fill: slotPalette[idx],
                opacity: 0.95,
                stroke: 'rgba(255,255,255,0.88)',
                lineWidth: 1.05
              }
            })
            start += delta
          })

          // 外边框：强调选中态但不过分刺眼
          children.push({
            type: 'circle',
            shape: { cx, cy, r: outerR + (isSelected ? 1.45 : 0.8) },
            style: {
              fill: 'transparent',
              stroke: isSelected ? '#dff7ff' : 'rgba(220, 236, 255, 0.92)',
              lineWidth: isSelected ? 2.0 : 1.05,
              shadowBlur: isSelected ? 8 : 3,
              shadowColor: isSelected ? 'rgba(94,216,255,0.55)' : 'rgba(100,130,180,0.28)'
            }
          })
          return { type: 'group', children }
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

  chartInstance.setOption(buildOption(), { notMerge: true, lazyUpdate: true })
}

const resizeChart = () => {
  if (!chartInstance) return
  if (resizeRafId) {
    cancelAnimationFrame(resizeRafId)
  }
  resizeRafId = requestAnimationFrame(() => {
    chartInstance?.resize()
    resizeRafId = 0
  })
}

const scheduleRender = () => {
  if (renderRafId) {
    cancelAnimationFrame(renderRafId)
  }
  renderRafId = requestAnimationFrame(() => {
    renderChart()
    renderRafId = 0
  })
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
    props.mapLayoutSize,
    props.mapAspectScale
  ],
  () => {
    scheduleRender()
  },
  { deep: false }
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

watch(
  () => props.chartHeight,
  () => {
    nextTick(() => resizeChart())
  }
)

onMounted(() => {
  syncViewFromProps()
  scheduleRender()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  if (renderRafId) {
    cancelAnimationFrame(renderRafId)
    renderRafId = 0
  }
  if (resizeRafId) {
    cancelAnimationFrame(resizeRafId)
    resizeRafId = 0
  }
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
