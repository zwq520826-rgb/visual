<template>
  <div class="q5-force-atlas">
    <div v-if="loading" class="state">正在加载引力网络...</div>
    <div v-else-if="error" class="state error">{{ error }}</div>
    <div v-else-if="renderError" class="state error">{{ renderError }}</div>
    <div v-else-if="!hasData" class="state">暂无网络数据</div>
    <div v-else ref="chartEl" class="chart"></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  networks: {
    type: Array,
    default: () => []
  },
  activeJobTitle: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  }
})

const chartEl = ref(null)
const renderError = ref('')
let chart = null

const hasData = computed(() => Array.isArray(props.networks) && props.networks.length > 0)

function hash32(str) {
  let h = 2166136261
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

function unitFromSeed(seed, salt = 0) {
  const v = hash32(`${seed}|${salt}`)
  return (v % 100000) / 100000
}

function clamp01(v) {
  return Math.max(0, Math.min(1, v))
}

function salaryColorByT(t) {
  const x = clamp01(t)
  const c0 = [59, 130, 246] // low salary: cool blue
  const c1 = [239, 68, 68]  // high salary: warm red
  const r = Math.round(c0[0] + (c1[0] - c0[0]) * x)
  const g = Math.round(c0[1] + (c1[1] - c0[1]) * x)
  const b = Math.round(c0[2] + (c1[2] - c0[2]) * x)
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
}

function mixWithWhite(hex, ratio = 0.72) {
  const x = clamp01(ratio)
  const s = (hex || '').replace('#', '')
  if (s.length !== 6) return hex || '#6ca5ff'
  const r = parseInt(s.slice(0, 2), 16)
  const g = parseInt(s.slice(2, 4), 16)
  const b = parseInt(s.slice(4, 6), 16)
  const rr = Math.round(r + (255 - r) * x)
  const gg = Math.round(g + (255 - g) * x)
  const bb = Math.round(b + (255 - b) * x)
  return `#${rr.toString(16).padStart(2, '0')}${gg.toString(16).padStart(2, '0')}${bb.toString(16).padStart(2, '0')}`
}

function buildMergedGraph(width = 1600, height = 620) {
  // 恒星簇拉开，形成可拖拽浏览的长卷视图（不强行挤在一屏）
  const clusterGap = Math.max(1120, Math.floor(width * 0.78))
  const startX = 180
  const centerY = Math.floor(height * 0.52)
  const nodes = []
  const links = []
  const centers = {}

  props.networks.forEach((network, idx) => {
    const job = network?.job_title || `job_${idx + 1}`
    const clusterPrefix = `g${idx}`
    const centerNodeRaw = (network.nodes || []).find(n => n.type === 'job') || {}
    const centerSize = Number(centerNodeRaw.symbolSize || 54)
    const centerId = `${clusterPrefix}:job:${job}`
    const centerX = startX + idx * clusterGap
    centers[job] = centerX

    nodes.push({
      id: centerId,
      name: job,
      type: 'job',
      value: Number(centerNodeRaw.value || network?.summary?.job_total_count || 0),
      symbolSize: Number(centerNodeRaw.symbolSize || 54),
      itemStyle: centerNodeRaw.itemStyle || { color: '#ffd166' },
      x: centerX,
      y: centerY,
      label: { show: true, color: '#dfefff' }
    })

    const nodeByIndustry = new Map()
    ;(network.nodes || []).forEach((n) => {
      if (n.type === 'industry') nodeByIndustry.set(n.name, n)
    })

    const edgeList = Array.isArray(network.links) ? network.links : []
    const coreEdges = edgeList.filter(e => e.edge_class === 'core')
    const dustEdges = edgeList.filter(e => e.edge_class === 'dust')
    const orientationShift = (unitFromSeed(job, 77) - 0.5) * 0.36

    const pushIndustryEdge = (edge, angle, radius, nodeClass, j) => {
      const industryName = String(edge.target || '').replace(/^ind:/, '') || `industry_${j + 1}`
      const indRaw = nodeByIndustry.get(industryName) || {}
      const indId = `${clusterPrefix}:ind:${industryName}`
      const x = centerX + Math.cos(angle) * radius
      const y = centerY + Math.sin(angle) * radius

      nodes.push({
        id: indId,
        name: industryName,
        type: 'industry',
        node_class: nodeClass,
        value: Number(indRaw.value || edge.value || 0),
        salary: Number(edge.salary || indRaw.salary || 0),
        symbolSize: Number(indRaw.symbolSize || 22),
        itemStyle: indRaw.itemStyle || { color: '#4ea8de' },
        x,
        y,
        label: {
          show: indRaw?.label?.show !== false,
          color: '#d7e6ff',
          fontSize: nodeClass === 'dust' ? 0 : 11
        }
      })

      links.push({
        source: centerId,
        target: indId,
        edge_class: edge.edge_class || 'core',
        value: Number(edge.value || 0),
        salary: Number(edge.salary || 0),
        lineStyle: edge.lineStyle || { color: '#6ca5ff', width: 2.5, opacity: 0.82 }
      })
    }

    // 核心行业：规律环绕，形成“核心星环”
    coreEdges.forEach((edge, idx) => {
      const n = Math.max(1, coreEdges.length)
      const baseAngle = -Math.PI / 2 + (Math.PI * 2 * idx) / n
      const ringJitter = idx % 2 === 0 ? -22 : 22
      const baseCoreRadius = Math.max(360, centerSize * 1.85 + 230)
      const radius = baseCoreRadius + ringJitter
      pushIndustryEdge(edge, baseAngle + orientationShift, radius, 'core', idx)
    })

    // 星尘行业：非规则散落（可复现的伪随机）
    dustEdges.forEach((edge, idx) => {
      const n = Math.max(1, dustEdges.length)
      const industryName = String(edge.target || '').replace(/^ind:/, '') || `dust_${idx}`
      const seed = `${job}|${industryName}|${idx}`
      const u1 = unitFromSeed(seed, 1)
      const u2 = unitFromSeed(seed, 2)
      const u3 = unitFromSeed(seed, 3)

      // 保持整体均匀覆盖，但局部打散，不形成规则花瓣
      const baseAngle = (Math.PI * 2 * idx) / n
      const angle = baseAngle + (u1 - 0.5) * 0.95 + orientationShift * 0.6
      const radius = 440 + u2 * 240 + (u3 - 0.5) * 40
      pushIndustryEdge(edge, angle, radius, 'dust', idx)
    })
  })

  const activeCenter = centers[props.activeJobTitle] ?? Object.values(centers)[0] ?? startX
  const offsetX = Math.floor(width * 0.5 - activeCenter)
  const shiftedNodes = nodes.map(n => ({ ...n, x: Number(n.x) + offsetX }))
  return { nodes: shiftedNodes, links }
}

function buildOption() {
  const width = chart?.getWidth?.() || 1600
  const height = chart?.getHeight?.() || 620
  const merged = buildMergedGraph(width, height)
  const allSalaries = merged.links.map(l => Number(l.salary || 0)).filter(v => Number.isFinite(v))
  const salMin = allSalaries.length ? Math.min(...allSalaries) : 0
  const salMax = allSalaries.length ? Math.max(...allSalaries) : 1
  const salSpan = salMax - salMin
  const linksColored = merged.links.flatMap((l) => {
    const salary = Number(l.salary || 0)
    const t = salSpan > 0 ? (salary - salMin) / salSpan : 0.5
    const base = salaryColorByT(t)
    const isDust = l.edge_class === 'dust'
    const color = isDust ? mixWithWhite(base, 0.72) : base
    const mainLink = {
      ...l,
      // 单系列：仅让星尘“线”不可交互；星尘“节点”仍可交互
      silent: isDust,
      tooltip: { show: !isDust },
      emphasis: isDust ? { disabled: true } : undefined,
      lineStyle: {
        ...(l.lineStyle || {}),
        color
      }
    }
    if (isDust) return [mainLink]

    // 核心线增加“不可见命中层”，提升 hover 灵敏度（视觉不变）
    const hitWidth = Math.max(Number(mainLink.lineStyle?.width || 2) + 12, 14)
    const hitLink = {
      ...l,
      edge_class: 'core_hit',
      tooltip: { show: true },
      emphasis: { disabled: true },
      lineStyle: {
        width: hitWidth,
        opacity: 0.001,
        color: 'rgba(255,255,255,0.001)',
        curveness: (mainLink.lineStyle && mainLink.lineStyle.curveness) || 0.22
      }
    }
    return [mainLink, hitLink]
  })

  return {
    backgroundColor: 'transparent',
    animationDuration: 900,
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(10,16,30,0.92)',
      borderColor: 'rgba(130,164,212,0.35)',
      borderWidth: 1,
      textStyle: { color: '#d7e6ff' },
      formatter: (params) => {
        if (params.dataType === 'edge' && params.data?.edge_class === 'dust') return ''
        if (params.dataType === 'node') {
          const d = params.data || {}
          if (d.type === 'job') return `核心岗位<br/>${d.name}<br/>需求量: ${Number(d.value || 0).toLocaleString()}`
          return `行业<br/>${d.name}<br/>招聘量: ${Number(d.value || 0).toLocaleString()}<br/>平均薪资: ${Number(d.salary || 0).toFixed(2)}`
        }
        if (params.dataType === 'edge') {
          const d = params.data || {}
          return `招聘量: ${Number(d.value || 0).toLocaleString()}<br/>薪资: ${Number(d.salary || 0).toFixed(2)}`
        }
        return ''
      }
    },
    series: [
      {
        // 单系列：星尘线不可交互，星尘节点可交互
        type: 'graph',
        layout: 'none',
        roam: true,
        draggable: false,
        focusNodeAdjacency: true,
        data: merged.nodes,
        links: linksColored,
        label: { show: true, fontSize: 11 },
        labelLayout: { hideOverlap: true },
        lineStyle: {
          opacity: 0.82,
          curveness: 0.22
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 4 }
        }
      }
    ]
  }
}

async function renderChart() {
  await nextTick()
  if (!chartEl.value || !hasData.value) return
  renderError.value = ''
  try {
    if (!chart) chart = echarts.init(chartEl.value)
    chart.setOption(buildOption(), true)
    chart.resize()
  } catch (e) {
    renderError.value = `引力图渲染失败: ${e?.message || '未知错误'}`
  }
}

function onResize() {
  if (!chart) return
  chart.resize()
  chart.setOption(buildOption(), true)
}

watch(() => props.networks, renderChart, { deep: true, flush: 'post' })
watch(() => props.activeJobTitle, renderChart, { flush: 'post' })
watch(() => props.loading, async (v) => {
  if (!v && hasData.value) await renderChart()
})

onMounted(async () => {
  if (hasData.value) await renderChart()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.q5-force-atlas {
  width: 100%;
  min-height: 620px;
  border-radius: 20px;
  background:
    radial-gradient(circle at 20% 20%, rgba(111, 173, 255, 0.12), transparent 44%),
    radial-gradient(circle at 80% 80%, rgba(255, 150, 92, 0.13), transparent 44%),
    linear-gradient(160deg, #08172c 0%, #0d1f39 45%, #112b44 100%);
  border: 1px solid rgba(137, 176, 232, 0.2);
  overflow: hidden;
}

.chart {
  width: 100%;
  min-height: 620px;
}

.state {
  min-height: 620px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d4e6ff;
  font-size: 14px;
}

.state.error {
  color: #ffd3d3;
}
</style>
