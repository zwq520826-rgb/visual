<template>
  <div class="sankey-chart">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>正在加载数据...</p>
    </div>
    
    <div v-if="error" class="error-message">
      <p>错误: {{ error }}</p>
    </div>
    
    <div v-if="!loading && !error && !hasData" class="empty-state">
      <p>{{ emptyMessage }}</p>
    </div>
    
    <div v-if="hasData" class="chart-wrapper">
      <div ref="chartContainer" class="chart-container"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  },
  emptyMessage: {
    type: String,
    default: '暂无数据'
  }
})

const chartContainer = ref(null)
const hasData = ref(false)
let chartInstance = null
let renderTimer = 0

const hexToRgba = (hex, alpha = 1) => {
  if (!hex || typeof hex !== 'string') return `rgba(79,125,232,${alpha})`
  const normalized = hex.replace('#', '')
  const full = normalized.length === 3
    ? normalized.split('').map((c) => c + c).join('')
    : normalized
  if (full.length !== 6) return `rgba(79,125,232,${alpha})`
  const r = Number.parseInt(full.slice(0, 2), 16)
  const g = Number.parseInt(full.slice(2, 4), 16)
  const b = Number.parseInt(full.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

const hasValidData = (d) => !!(d && Array.isArray(d.nodes) && Array.isArray(d.links) && d.nodes.length > 0)

const scheduleRender = () => {
  if (renderTimer) {
    clearTimeout(renderTimer)
  }
  renderTimer = window.setTimeout(() => {
    renderTimer = 0
    renderChart()
  }, 16)
}

watch(
  () => [props.data, props.loading, props.error],
  ([data, loadingState, errorState]) => {
    if (errorState) {
      hasData.value = false
      return
    }
    hasData.value = hasValidData(data)
    if (!loadingState && hasData.value) {
      scheduleRender()
    }
  },
  { immediate: true, deep: false }
)

// 渲染图表
const renderChart = () => {
  if (!chartContainer.value || !props.data) {
    return
  }
  if (!hasValidData(props.data)) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartContainer.value)
  }

  const categoryColors = {
    '技能要求': '#4f7de8',
    '行业分布': '#77be5f',
    '市场需求': '#f0bf4f',
    '特征组合': '#ea6a66',
    '薪资结果': '#66b2d3'
  }

  const jobLegend = Array.isArray(props.data?.jobLegend) ? props.data.jobLegend : []
  const slotColorMap = Object.fromEntries(
    jobLegend.map((item) => [item.slot, item.color || '#4f7de8'])
  )

  // 为节点添加颜色（优先使用上游已编码的职位色）
  const nodesWithColor = props.data.nodes.map(node => ({
    ...node,
    itemStyle: {
      color: node.itemStyle?.color || slotColorMap[node.jobSlot] || categoryColors[node.category] || '#7c8da8',
      borderColor: '#ffffff',
      borderWidth: 1,
      borderRadius: 4,
      shadowBlur: 12,
      shadowColor: hexToRgba(node.itemStyle?.color || slotColorMap[node.jobSlot] || '#4f7de8', 0.26)
    }
  }))

  const nodeColorMap = new Map(nodesWithColor.map((node, idx) => [String(node.name ?? idx), node.itemStyle?.color || '#7b92b6']))
  const resolveNodeColor = (ref, fallback = '#7b92b6') => {
    if (typeof ref === 'number') {
      return nodesWithColor[ref]?.itemStyle?.color || fallback
    }
    return nodeColorMap.get(String(ref)) || fallback
  }

  const linksWithStyle = (props.data.links || []).map((link) => {
    const sourceColor = resolveNodeColor(link.source, slotColorMap[link.jobSlot] || '#7b92b6')
    const targetColor = resolveNodeColor(link.target, '#9db2d7')
    return {
      ...link,
      lineStyle: {
        curveness: Number(link.lineStyle?.curveness ?? 0.52),
        opacity: Number(link.lineStyle?.opacity ?? 0.5),
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 1,
          y2: 0,
          colorStops: [
            { offset: 0, color: hexToRgba(sourceColor, 0.82) },
            { offset: 1, color: hexToRgba(targetColor, 0.82) }
          ]
        },
        shadowBlur: 8,
        shadowColor: hexToRgba(sourceColor, 0.26)
      }
    }
  })

  const option = {
    animationDuration: 480,
    animationDurationUpdate: 360,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
    title: {
      text: '职位特征与薪资流动桑基图',
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#2c3e50'
      }
    },
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      formatter: function(params) {
        if (params.dataType === 'edge') {
          const edge = params.data || {}
          const from = edge.sourceLabel || edge.source || ''
          const to = edge.targetLabel || edge.target || ''
          const owner = edge.jobSlot ? `${edge.jobSlot}${edge.jobTitle ? `（${edge.jobTitle.slice(0, 6)}...${edge.jobTitle.slice(-4)}）` : ''}` : '汇总'
          return `${owner}<br/>${from} → ${to}<br/>流量: ${edge.value} 个职位`
        } else {
          const node = params.data || {}
          const owner = node.jobSlot ? `${node.jobSlot}${node.jobTitle ? `（${node.jobTitle.slice(0, 6)}...${node.jobTitle.slice(-4)}）` : ''}` : '共享节点'
          return `${owner}<br/>${node.displayName || node.name}<br/>分类: ${node.category}`
        }
      }
    },
    series: [
      {
        type: 'sankey',
        data: nodesWithColor,
        links: linksWithStyle,
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            opacity: 0.92,
            width: 2.4
          }
        },
        lineStyle: {
          color: 'source',
          curveness: 0.52,
          opacity: 0.48
        },
        label: {
          position: 'right',
          fontSize: 11.5,
          color: '#1f436f',
          formatter: (params) => {
            const node = params.data || {}
            const name = node.displayName || node.name || ''
            const slot = node.jobSlot || ''
            return slot ? `${slot} · ${name}` : name
          }
        },
        draggable: true,
        left: '5%',
        right: '20%',
        top: '15%',
        bottom: '10%',
        nodeWidth: 20,
        nodeGap: 12,
        layoutIterations: 32
      }
    ],
    legend: {
      data: jobLegend.map((item) => item.slot),
      orient: 'vertical',
      right: 10,
      top: 80,
      textStyle: {
        fontSize: 12
      },
      formatter: function(name) {
        const item = jobLegend.find((it) => it.slot === name)
        if (!item) return name
        return `${item.slot}：${item.jobTitle?.slice(0, 6)}...${item.jobTitle?.slice(-4)}`
      },
      itemWidth: 20,
      itemHeight: 14,
      selectedMode: false
    }
  }

  chartInstance.setOption(option, { notMerge: true, lazyUpdate: true })
}

// 窗口大小变化时重新渲染
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (renderTimer) {
    clearTimeout(renderTimer)
    renderTimer = 0
  }
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
  }
})
</script>

<style scoped>
.sankey-chart {
  width: 100%;
  height: 100%;
  min-height: 600px;
  position: relative;
}

.chart-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 600px;
  border: 1px solid rgba(46, 122, 198, 0.24);
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(165deg, rgba(255, 255, 255, 0.96), rgba(242, 249, 255, 0.96));
}

.chart-wrapper::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 0%, rgba(46, 122, 198, 0.08) 42%, transparent 74%);
  transform: translateX(-120%);
  animation: flowBg 4.8s linear infinite;
  pointer-events: none;
}

.chart-wrapper::after {
  content: '';
  position: absolute;
  inset: auto 0 0 0;
  height: 80px;
  background: radial-gradient(circle at 20% 20%, rgba(46, 122, 198, 0.08), transparent 65%);
  pointer-events: none;
}

.chart-container {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 600px;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #55779b;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e8f0fa;
  border-top: 4px solid #2f6df6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  padding: 20px;
  background: #feeff1;
  border: 1px solid #f5c2c9;
  border-radius: 8px;
  color: #a73943;
  text-align: center;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #5b7da0;
  font-size: 15px;
  font-weight: 600;
  background: linear-gradient(170deg, rgba(255, 255, 255, 0.9), rgba(242, 249, 255, 0.9));
}

@keyframes flowBg {
  0% { transform: translateX(-120%); }
  100% { transform: translateX(140%); }
}
</style>
