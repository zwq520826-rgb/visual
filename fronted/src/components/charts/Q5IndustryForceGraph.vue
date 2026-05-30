<template>
  <div class="q5-force-graph">
    <div v-if="loading" class="state">正在加载引力网络...</div>
    <div v-else-if="error" class="state error">{{ error }}</div>
    <div v-else-if="renderError" class="state error">{{ renderError }}</div>
    <div v-else-if="!hasGraphData" class="state">暂无网络数据</div>
    <div v-else ref="chartEl" class="chart"></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  networkData: {
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
  }
})

const chartEl = ref(null)
const renderError = ref('')
let chart = null

const hasGraphData = computed(() => {
  const nodes = props.networkData?.nodes
  const links = props.networkData?.links
  return Array.isArray(nodes) && nodes.length > 0 && Array.isArray(links)
})

function buildOption(data) {
  const nodes = Array.isArray(data?.nodes) ? data.nodes : []
  const links = Array.isArray(data?.links) ? data.links : []
  const jobTitle = data?.job_title || '岗位'

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
        if (params.dataType === 'node') {
          const d = params.data || {}
          if (d.type === 'job') {
            return `核心岗位<br/>${d.name}<br/>需求量: ${Number(d.value || 0).toLocaleString()}`
          }
          return `行业节点<br/>${d.name}<br/>招聘量: ${Number(d.value || 0).toLocaleString()}`
        }
        if (params.dataType === 'edge') {
          const d = params.data || {}
          return `岗位: ${jobTitle}<br/>行业: ${String(d.target || '').replace('ind:', '')}<br/>招聘量: ${Number(d.value || 0).toLocaleString()}<br/>薪资: ${Number(d.salary || 0).toFixed(2)}`
        }
        return ''
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        focusNodeAdjacency: true,
        draggable: true,
        data: nodes,
        links,
        categories: [
          { name: 'job' },
          { name: 'industry' }
        ],
        label: {
          show: true,
          color: '#dce8ff',
          fontSize: 11,
          formatter: '{b}'
        },
        labelLayout: {
          hideOverlap: true
        },
        lineStyle: {
          color: 'source',
          opacity: 0.8,
          curveness: 0.18
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 4 }
        },
        force: {
          repulsion: 280,
          edgeLength: [120, 260],
          gravity: 0.04,
          friction: 0.4,
          layoutAnimation: true
        }
      }
    ]
  }
}

async function initChart() {
  await nextTick()
  if (!chartEl.value || !hasGraphData.value) return
  renderError.value = ''
  if (chart) {
    chart.dispose()
    chart = null
  }
  try {
    chart = echarts.init(chartEl.value)
    chart.setOption(buildOption(props.networkData), true)
    chart.resize()
  } catch (e) {
    renderError.value = `引力图渲染失败: ${e?.message || '未知错误'}`
    if (chart) {
      chart.dispose()
      chart = null
    }
  }
}

function resizeChart() {
  if (chart) chart.resize()
}

watch(
  () => props.networkData,
  async () => {
    renderError.value = ''
    if (!hasGraphData.value) return
    if (!chart) {
      await initChart()
      return
    }
    try {
      chart.setOption(buildOption(props.networkData), true)
      chart.resize()
    } catch (e) {
      renderError.value = `引力图更新失败: ${e?.message || '未知错误'}`
    }
  },
  { deep: true, flush: 'post' }
)

watch(
  () => props.loading,
  async (v) => {
    if (!v && hasGraphData.value) {
      await nextTick()
      await initChart()
    }
  }
)

watch(
  () => hasGraphData.value,
  async (ok) => {
    if (!ok) return
    await nextTick()
    await initChart()
  },
  { flush: 'post' }
)

onMounted(async () => {
  if (hasGraphData.value) {
    await initChart()
  }
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.q5-force-graph {
  width: 100%;
  min-height: 560px;
  height: 100%;
  border-radius: 18px;
  background:
    radial-gradient(circle at 20% 20%, rgba(111, 173, 255, 0.12), transparent 44%),
    radial-gradient(circle at 80% 80%, rgba(255, 150, 92, 0.13), transparent 44%),
    linear-gradient(160deg, #08172c 0%, #0d1f39 45%, #112b44 100%);
  border: 1px solid rgba(137, 176, 232, 0.2);
  overflow: hidden;
  position: relative;
}

.chart {
  width: 100%;
  height: 100%;
  min-height: 560px;
}

.state {
  min-height: 560px;
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
