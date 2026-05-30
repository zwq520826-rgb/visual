<template>
  <div class="scatter-bubble-chart">
    <!-- 控制面板 -->
    <div class="controls">
      <div class="control-item" v-if="viewMode === 'city'">
        <label for="city-select">选择城市：</label>
        <select 
          id="city-select" 
          v-model="selectedCity" 
          @change="loadScatterData" 
          class="city-select"
        >
          <option v-for="city in cities" :key="city" :value="city">{{ city }}</option>
        </select>
      </div>
      <div class="control-item">
        <label>视图：</label>
        <span class="mode-hint">城市 · 职位层级</span>
      </div>

      <div class="control-item metric-group">
        <label>X轴：</label>
        <select v-model="xMetric" @change="updateChart" class="metric-select">
          <option v-for="item in metricOptions" :key="`x-${item.value}`" :value="item.value">{{ item.label }}</option>
        </select>
      </div>

      <div class="control-item metric-group">
        <label>Y轴：</label>
        <select v-model="yMetric" @change="updateChart" class="metric-select">
          <option v-for="item in metricOptions" :key="`y-${item.value}`" :value="item.value">{{ item.label }}</option>
        </select>
      </div>

      <div class="control-item metric-group">
        <label>气泡：</label>
        <select v-model="sizeMetric" @change="updateChart" class="metric-select">
          <option v-for="item in sizeOptions" :key="`s-${item.value}`" :value="item.value">{{ item.label }}</option>
        </select>
      </div>

      <div class="control-item">
        <label class="switch-item"><input type="checkbox" v-model="showTopLabels" @change="updateChart"/> Top标注</label>
      </div>
    </div>

    <!-- 图例 / 提示 -->
    <div class="legend">
      <div class="legend-title">职位层级</div>
      <div class="legend-items">
        <div 
          v-for="item in legendItems" 
          :key="item.name"
          class="legend-item"
          @click="toggleCategory(item.name)"
          :class="{ inactive: hiddenCategories.has(item.name) }"
        >
          <span class="legend-color" :style="{ backgroundColor: item.color }"></span>
          <span class="legend-label">{{ item.name }}</span>
        </div>
      </div>
    </div>

    <!-- ECharts容器 -->
    <div ref="chartContainer" class="chart-container"></div>

    <!-- 选中节点信息 -->
    <div v-if="selectedNodes.length > 0" class="selected-info">
      <div class="selected-header">
        <span>
          {{ '已选择 ' + selectedNodes.length + ' 个职位' }}
        </span>
        <button @click="clearSelection" class="clear-btn">清除选择</button>
      </div>
      <div class="selected-list">
        <div
          v-for="(node, index) in selectedNodes"
          :key="`${node.job_title}-${node.avg_salary}-${node.avg_experience}-${index}`"
          class="selected-node"
        >
          <span class="node-title">{{ node.job_title }}</span>
          <span class="node-info">
            平均薪资：{{ node.avg_salary?.toFixed(2) }}K |
            平均经验：{{ node.avg_experience?.toFixed(2) }} |
            平均学历：{{ node.avg_education?.toFixed(2) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { 
  getRepresentativeCities, 
  getScatterData, 
  getNationalIndustryScatter
} from '@/api/q1Api'

// 响应式数据
const cities = ref([])
const selectedCity = ref('')
const scatterData = ref(null)
const industryScatterData = ref(null)
const colorMode = ref('job_level') // 'job_level' 或 'industry'
const viewMode = computed(() => colorMode.value === 'job_level' ? 'city' : 'industry')
const xMetric = ref('avg_experience')
const yMetric = ref('avg_salary')
const sizeMetric = ref('job_in_city_cnt')
const showTopLabels = ref(false)
const showTrendLine = ref(false)
const hiddenCategories = ref(new Set())
const selectedNodes = ref([])
const chartContainer = ref(null)
let chartInstance = null

// 定义配色方案
const jobLevelColors = {
  '平薪新人': '#3b82f6',
  '基薪普及': '#14b8a6',
  '优薪技能': '#f59e0b',
  '高新管理': '#ef4444'
}

// 生成行业配色（使用渐变色）
const generateIndustryColors = (industries) => {
  const colors = [
    '#3b82f6', '#14b8a6', '#f59e0b', '#ef4444', '#8b5cf6',
    '#10b981', '#f97316', '#06b6d4', '#e11d48', '#6366f1',
    '#84cc16', '#d946ef', '#0ea5e9', '#f43f5e', '#22c55e'
  ]
  const colorMap = {}
  industries.forEach((industry, index) => {
    colorMap[industry] = colors[index % colors.length]
  })
  return colorMap
}

const industryColors = ref({})

const cityMetricOptions = [
  { value: 'avg_experience', label: '平均经验' },
  { value: 'avg_salary', label: '平均薪资' },
  { value: 'avg_education', label: '平均学历' },
  { value: 'avg_shannon_entropy', label: '香农熵' },
  { value: 'salary_std', label: '薪资波动' }
]

const industryMetricOptions = [
  { value: 'avg_experience_rank', label: '平均经验' },
  { value: 'avg_median_salary', label: '平均薪资' },
  { value: 'avg_education_rank', label: '平均学历' },
  { value: 'avg_city_tier_score', label: '城市等级' },
  { value: 'job_count', label: '招聘总数' }
]

const metricOptions = computed(() => viewMode.value === 'city' ? cityMetricOptions : industryMetricOptions)
const sizeOptions = computed(() => viewMode.value === 'city'
  ? [
      { value: 'job_in_city_cnt', label: '招聘人数' },
      { value: 'salary_std', label: '薪资波动' },
      { value: 'avg_shannon_entropy', label: '香农熵' }
    ]
  : [
      { value: 'job_count', label: '招聘总数' },
      { value: 'avg_median_salary', label: '平均薪资' },
      { value: 'avg_city_tier_score', label: '城市等级' }
    ])

const getMetricValue = (raw, key) => {
  const value = raw?.[key]
  return Number.isFinite(Number(value)) ? Number(value) : 0
}

const scaleSize = (value, min, max) => {
  const v = Number(value) || 0
  if (max <= min) return 22
  const normalized = (v - min) / (max - min)
  return 10 + Math.max(0, Math.min(1, normalized)) * 38
}

// 计算图例项
const legendItems = computed(() => {
  if (viewMode.value !== 'city') return []
  return Object.entries(jobLevelColors).map(([name, color]) => ({
    name,
    color
  }))
})

// 切换类别显示/隐藏
const toggleCategory = (category) => {
  if (viewMode.value !== 'city') return
  if (hiddenCategories.value.has(category)) {
    hiddenCategories.value.delete(category)
  } else {
    hiddenCategories.value.add(category)
  }
  updateChart()
}

// 清除选择
const clearSelection = () => {
  selectedNodes.value = []
  if (chartInstance) {
    chartInstance.dispatchAction({
      type: 'unselect'
    })
  }
}

// 加载初始数据
const loadInitialData = async () => {
  try {
    // 加载城市列表
    const citiesResponse = await getRepresentativeCities()
    cities.value = citiesResponse.cities
    
    // 选择第一个城市
    if (cities.value.length > 0) {
      selectedCity.value = cities.value[0]
      await loadScatterData()
    }
  } catch (error) {
    console.error('加载初始数据失败:', error)
  }
}

// 加载散点图数据
const loadScatterData = async () => {
  if (!selectedCity.value || viewMode.value !== 'city') return
  
  try {
    // 加载散点图数据
    const response = await getScatterData(selectedCity.value)
    scatterData.value = response
    
    // 更新图表
    await nextTick()
    updateChart()
  } catch (error) {
    console.error('加载散点图数据失败:', error)
  }
}

// 加载全国行业散点数据
const loadIndustryScatterData = async () => {
  try {
    const response = await getNationalIndustryScatter()
    industryScatterData.value = response
    const typeList = response?.data?.map(item => item.company_type) || []
    industryColors.value = generateIndustryColors(typeList)
    await nextTick()
    updateChart()
  } catch (error) {
    console.error('加载行业散点数据失败:', error)
  }
}

// 准备图表数据
const prepareChartData = () => {
  if (viewMode.value === 'city') {
    if (!scatterData.value || !scatterData.value.data) return []
    const data = scatterData.value.data
    const groupedData = {}
    const validData = data.filter(point => !hiddenCategories.value.has(point.job_level))
    const sizeRawValues = validData.map(point => getMetricValue(point, sizeMetric.value))
    const minSizeRaw = Math.min(...sizeRawValues, 0)
    const maxSizeRaw = Math.max(...sizeRawValues, 1)
    data.forEach(point => {
      const categoryValue = point.job_level
      if (hiddenCategories.value.has(categoryValue)) return
      if (!groupedData[categoryValue]) {
        groupedData[categoryValue] = []
      }
        groupedData[categoryValue].push({
          value: [
            getMetricValue(point, xMetric.value),
            getMetricValue(point, yMetric.value),
            scaleSize(getMetricValue(point, sizeMetric.value), minSizeRaw, maxSizeRaw)
          ],
        itemStyle: {
          color: jobLevelColors[categoryValue] || '#ccc'
        },
        rawData: point
      })
    })
    return Object.entries(groupedData).map(([categoryName, points]) => ({
      name: categoryName,
      type: 'scatter',
      symbolSize: dataPoint => dataPoint[2],
      data: points,
      emphasis: {
        focus: 'self',
        itemStyle: {
          borderColor: '#333',
          borderWidth: 2
        }
      }
    }))
  }

  // 行业模式：单个系列，按行业着色
  if (!industryScatterData.value || !industryScatterData.value.data) return []
  const sizeRawValues = industryScatterData.value.data.map(item => getMetricValue(item, sizeMetric.value))
  const minSizeRaw = Math.min(...sizeRawValues, 0)
  const maxSizeRaw = Math.max(...sizeRawValues, 1)
  const industryPoints = industryScatterData.value.data.map(item => ({
    value: [
      getMetricValue(item, xMetric.value),
      getMetricValue(item, yMetric.value),
      scaleSize(getMetricValue(item, sizeMetric.value), minSizeRaw, maxSizeRaw)
    ],
    name: item.company_type,
    itemStyle: {
      color: industryColors.value[item.company_type] || '#6e5b3e'
    },
    rawData: item
  }))

  return [
    {
      name: '行业类别',
      type: 'scatter',
      symbolSize: dataPoint => dataPoint[2],
      data: industryPoints,
      emphasis: {
        focus: 'self',
        itemStyle: {
          borderColor: '#333',
          borderWidth: 2
        }
      }
    }
  ]
}

// 更新图表
const updateChart = () => {
  if (!chartInstance) return
  
  // 根据当前模式检查数据
  if (viewMode.value === 'city' && !scatterData.value) return
  if (viewMode.value === 'industry' && !industryScatterData.value) return
  
  const baseSeries = prepareChartData()
  const points = baseSeries.flatMap(s => s.data || [])

  const xName = metricOptions.value.find(item => item.value === xMetric.value)?.label || 'X轴'
  const yName = metricOptions.value.find(item => item.value === yMetric.value)?.label || 'Y轴'

  const series = [...baseSeries]

  if (showTopLabels.value && points.length > 0) {
    const topPoints = [...points].sort((a, b) => (b.value?.[1] || 0) - (a.value?.[1] || 0)).slice(0, 8)
    series.push({
      name: 'Top标注',
      type: 'scatter',
      data: topPoints,
      symbolSize: dataPoint => Math.max(14, (dataPoint?.[2] || 10) * 0.65),
      itemStyle: {
        color: '#ef4444',
        borderColor: '#ffffff',
        borderWidth: 1
      },
      label: {
        show: true,
        position: 'top',
        color: '#1f2937',
        fontSize: 11,
        formatter: params => {
          const raw = params.data?.rawData
          return viewMode.value === 'city' ? raw?.job_title : raw?.company_type
        }
      },
      silent: true
    })
  }

  // 趋势线已移除，避免遮挡散点图
  
  const option = {
    title: {
      text: viewMode.value === 'city' 
        ? `${selectedCity.value} - 职位分布散点图`
        : '全国行业类别散点（160）',
      left: 'center',
      top: 10,
      textStyle: {
        color: '#1f2937',
        fontWeight: 600
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const data = params.data.rawData

        if (viewMode.value === 'industry') {
          return `
            <div style="padding: 8px; max-width: 320px;">
              <strong>${data.company_type}</strong><br/>
              <span style="color: #666;">招聘总数：</span>${data.job_count}<br/>
              <span style="color: #666;">平均中位薪资：</span>${data.avg_median_salary.toFixed(2)}K<br/>
              <span style="color: #666;">平均经验层级：</span>${data.avg_experience_rank.toFixed(2)}<br/>
              <span style="color: #666;">平均学历层级：</span>${data.avg_education_rank.toFixed(2)}<br/>
              <span style="color: #666;">平均城市等级：</span>${data.avg_city_tier_label || '暂无'}${data.avg_city_tier_score ? `（${data.avg_city_tier_score.toFixed(2)}）` : ''}<br/>
            </div>
          `
        }

        const samples = data.samples || []
        const samplesHtml = samples.length
          ? samples.map((s, idx) => `
              <div style="margin-top:4px;font-size:12px;">
                <span style="color:#999;">样本${idx + 1}：</span>
                薪资：${s.salary}，学历：${s.education}，经验：${s.experience}
              </div>
            `).join('')
          : '<div style="margin-top:4px;font-size:12px;color:#aaa;">无示例数据</div>'

        return `
          <div style="padding: 8px; max-width: 320px;">
            <strong>${data.job_title}</strong><br/>
            <span style="color: #666;">平均薪资：</span>${data.avg_salary.toFixed(2)}K<br/>
            <span style="color: #666;">薪资标准差：</span>${data.salary_std.toFixed(2)}K<br/>
            <span style="color: #666;">平均经验：</span>${data.avg_experience.toFixed(2)}（层级）<br/>
            <span style="color: #666;">平均学历：</span>${data.avg_education.toFixed(2)}（层级）<br/>
            <span style="color: #666;">香农熵：</span>${data.avg_shannon_entropy.toFixed(3)}<br/>
            <span style="color: #666;">招聘人数：</span>${data.job_in_city_cnt}<br/>
            <span style="color: #666;">薪资范围：</span>${data.min_annual_salary.toFixed(2)}K - ${data.max_annual_salary.toFixed(2)}K<br/>
            <span style="color: #666;">职位层级：</span>${data.job_level}<br/>
            <span style="color: #666;">行业示例：</span>${data.company_type}<br/>
            <div style="margin-top:6px;padding-top:4px;border-top:1px solid #eee;font-size:12px;color:#666;">
              <div style="margin-bottom:2px;color:#999;">该城市该职位的示例记录：</div>
              ${samplesHtml}
            </div>
          </div>
        `
      }
    },
    grid: {
      left: '10%',
      right: '12%', // 增加右侧空间以容纳垂直滑块
      bottom: '18%', // 增加底部空间以容纳水平滑块
      top: '15%',
      containLabel: true
    },
    xAxis: {
      name: xName,
      nameLocation: 'middle',
      nameGap: 30,
      type: 'value',
      // 城市模式保留原来的 0-10，行业模式聚焦在 4-6 区间，减少空白和拥挤
      min: 'dataMin',
      max: 'dataMax',
      splitNumber: 8,
      splitLine: {
        show: true,
        lineStyle: {
          type: 'solid',
          color: 'rgba(95, 131, 174, 0.2)'
        }
      },
      axisLine: { lineStyle: { color: '#64748b' } },
      axisLabel: { color: '#334155' },
      nameTextStyle: { color: '#1f2937' }
    },
    yAxis: {
      name: yName,
      nameLocation: 'middle',
      nameGap: 50,
      type: 'value',
      splitLine: {
        show: true,
        lineStyle: {
          type: 'solid',
          color: 'rgba(95, 131, 174, 0.2)'
        }
      },
      axisLine: { lineStyle: { color: '#64748b' } },
      axisLabel: { color: '#334155' },
      nameTextStyle: { color: '#1f2937' }
    },
    // 添加内置缩放功能（鼠标滚轮缩放和拖拽平移）
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: 0,
        start: 0,
        end: 100,
        zoomOnMouseWheel: true, // 鼠标滚轮缩放
        moveOnMouseMove: true, // 鼠标移动平移
        moveOnMouseWheel: false, // 禁用鼠标滚轮平移（优先缩放）
        preventDefaultMouseMove: true // 防止默认鼠标移动行为
      },
      {
        type: 'inside',
        yAxisIndex: 0,
        start: 0,
        end: 100,
        zoomOnMouseWheel: true, // 鼠标滚轮缩放
        moveOnMouseMove: true, // 鼠标移动平移
        moveOnMouseWheel: false, // 禁用鼠标滚轮平移（优先缩放）
        preventDefaultMouseMove: true // 防止默认鼠标移动行为
      },
      // 添加滑块缩放（方便精确控制）
      {
        type: 'slider',
        xAxisIndex: 0,
        start: 0,
        end: 100,
        show: true,
        showDataShadow: false,
        showDetail: true,
        realtime: true,
        height: 20,
        bottom: 10,
        handleIcon: 'path://M30.9,53.2C16.8,53.2,5.3,41.7,5.3,27.6S16.8,2,30.9,2C45,2,56.4,13.5,56.4,27.6S45,53.2,30.9,53.2z M30.9,3.5C17.6,3.5,6.8,14.4,6.8,27.6c0,13.3,10.8,24.1,24.1,24.1C44.2,51.7,55,40.9,55,27.6C54.9,14.4,44.1,3.5,30.9,3.5z M36.9,35.8c0,0.6-0.4,1-1,1H26.8c-0.6,0-1-0.4-1-1s0.4-1,1-1h9.2C36.5,34.8,36.9,35.2,36.9,35.8z',
        handleSize: '80%',
        handleStyle: {
          color: '#2e7ac6',
          shadowBlur: 3,
          shadowColor: 'rgba(47, 58, 74, 0.2)',
          shadowOffsetX: 2,
          shadowOffsetY: 2
        },
        textStyle: {
          color: '#333',
          fontSize: 11
        },
        borderColor: '#2e7ac6',
        fillerColor: 'rgba(46, 122, 198, 0.24)',
        dataBackground: {
          lineStyle: {
            color: '#2e7ac6',
            width: 1
          },
          areaStyle: {
            color: 'rgba(46, 122, 198, 0.12)'
          }
        },
        selectedDataBackground: {
          lineStyle: {
            color: '#2e7ac6',
            width: 2
          },
          areaStyle: {
            color: 'rgba(46, 122, 198, 0.32)'
          }
        }
      },
      {
        type: 'slider',
        yAxisIndex: 0,
        start: 0,
        end: 100,
        show: true,
        showDataShadow: false,
        showDetail: true,
        realtime: true,
        width: 20,
        right: 10,
        handleIcon: 'path://M30.9,53.2C16.8,53.2,5.3,41.7,5.3,27.6S16.8,2,30.9,2C45,2,56.4,13.5,56.4,27.6S45,53.2,30.9,53.2z M30.9,3.5C17.6,3.5,6.8,14.4,6.8,27.6c0,13.3,10.8,24.1,24.1,24.1C44.2,51.7,55,40.9,55,27.6C54.9,14.4,44.1,3.5,30.9,3.5z M36.9,35.8c0,0.6-0.4,1-1,1H26.8c-0.6,0-1-0.4-1-1s0.4-1,1-1h9.2C36.5,34.8,36.9,35.2,36.9,35.8z',
        handleSize: '80%',
        handleStyle: {
          color: '#2e7ac6',
          shadowBlur: 3,
          shadowColor: 'rgba(47, 58, 74, 0.2)',
          shadowOffsetX: 2,
          shadowOffsetY: 2
        },
        textStyle: {
          color: '#333',
          fontSize: 11
        },
        borderColor: '#2e7ac6',
        fillerColor: 'rgba(46, 122, 198, 0.24)',
        dataBackground: {
          lineStyle: {
            color: '#2e7ac6',
            width: 1
          },
          areaStyle: {
            color: 'rgba(46, 122, 198, 0.12)'
          }
        },
        selectedDataBackground: {
          lineStyle: {
            color: '#2e7ac6',
            width: 2
          },
          areaStyle: {
            color: 'rgba(46, 122, 198, 0.32)'
          }
        }
      }
    ],
    // 添加工具箱，包含重置缩放按钮
    toolbox: {
      show: true,
      feature: {
        dataZoom: {
          yAxisIndex: 'none',
          title: {
            zoom: '区域缩放',
            back: '还原缩放'
          }
        },
        restore: {
          title: '还原'
        }
      },
      right: 20,
      top: 10,
      iconStyle: { borderColor: '#2e7ac6' },
      emphasis: {
        iconStyle: { borderColor: '#133a63' }
      }
    },
    backgroundColor: '#ffffff',
    textStyle: {
      color: '#2f3a4a'
    },
    series: series
  }
  
  chartInstance.setOption(option, true)
}

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) return
  
  chartInstance = echarts.init(chartContainer.value)
  
  // 监听点击事件实现多选
  chartInstance.on('click', (params) => {
    const data = params.data.rawData
    const isSameEntity = (a, b) => {
      if (viewMode.value === 'city') {
        return a.job_title === b.job_title &&
               a.avg_salary === b.avg_salary &&
               a.avg_experience === b.avg_experience &&
               a.company_type === b.company_type
      }
      return a.company_type === b.company_type
    }

    const index = selectedNodes.value.findIndex(n => isSameEntity(n, data))

    if (index >= 0) {
      selectedNodes.value.splice(index, 1)
    } else {
      // 行业模式限制最大2个，便于右侧差异对比
      if (viewMode.value === 'industry' && selectedNodes.value.length >= 2) {
        selectedNodes.value.shift()
      }
      selectedNodes.value.push(data)
    }
  })
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)

  updateChart()
}

// 处理窗口大小变化
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

const setViewMode = (mode) => {
  if (colorMode.value === mode) return
  colorMode.value = mode
}

// 重置缩放
const resetZoom = () => {
  if (!chartInstance) return
  chartInstance.dispatchAction({
    type: 'restore'
  })
}

// 监听模式变化
watch(colorMode, async (mode) => {
  hiddenCategories.value = new Set()
  selectedNodes.value = []
  if (mode === 'job_level') {
    xMetric.value = 'avg_experience'
    yMetric.value = 'avg_salary'
    sizeMetric.value = 'job_in_city_cnt'
  } else {
    xMetric.value = 'avg_experience_rank'
    yMetric.value = 'avg_median_salary'
    sizeMetric.value = 'job_count'
  }
  
  // 重置缩放状态
  resetZoom()

  if (mode === 'job_level') {
    if (selectedCity.value) {
      await loadScatterData()
    }
  } else {
    if (!industryScatterData.value) {
      await loadIndustryScatterData()
    } else {
      await nextTick()
      updateChart()
    }
  }
})

// 组件挂载时初始化
onMounted(async () => {
  await loadInitialData()
  await loadIndustryScatterData()
  initChart()
})

// 组件卸载时清理
onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  window.removeEventListener('resize', handleResize)
})

// 暴露选中的节点数据（供父组件使用）
defineExpose({
  selectedNodes,
  viewMode
})
</script>

<style scoped>
.scatter-bubble-chart {
  --q1-surface: rgba(255, 255, 255, 0.94);
  --q1-surface-soft: rgba(238, 247, 255, 0.82);
  --q1-border: rgba(46, 122, 198, 0.24);
  --q1-title: #133a63;
  --q1-text: #2b4f76;
  --q1-muted: #607f9f;
  --q1-accent: #2e7ac6;
  --q1-accent-2: #d66b3d;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  gap: 10px;
}

.controls {
  display: flex;
  gap: 14px 18px;
  padding: 12px 14px;
  background: linear-gradient(160deg, var(--q1-surface), var(--q1-surface-soft));
  border: 1px solid var(--q1-border);
  border-radius: 12px;
  box-shadow: 0 8px 18px rgba(43, 82, 126, 0.1);
  flex-wrap: wrap;
}

.control-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.metric-group {
  gap: 8px;
}

.metric-select {
  padding: 7px 10px;
  border: 1px solid rgba(46, 122, 198, 0.34);
  border-radius: 8px;
  background: #fdfefe;
  color: var(--q1-text);
  min-width: 120px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.metric-select:focus,
.city-select:focus {
  outline: none;
  border-color: var(--q1-accent);
  box-shadow: 0 0 0 3px rgba(46, 122, 198, 0.18);
}

.switch-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--q1-text);
  font-size: 13px;
}

.mode-hint {
  font-size: 13px;
  color: var(--q1-muted);
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px dashed rgba(46, 122, 198, 0.26);
  background: rgba(250, 253, 255, 0.88);
}

.control-item label {
  font-weight: 700;
  color: var(--q1-title);
  font-size: 12px;
  white-space: nowrap;
}

.city-select {
  padding: 7px 12px;
  border: 1px solid rgba(46, 122, 198, 0.34);
  border-radius: 8px;
  background: #ffffff;
  color: var(--q1-text);
  font-size: 13px;
  cursor: pointer;
  min-width: 150px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.city-select:hover {
  border-color: var(--q1-accent);
}

.color-mode-buttons {
  display: flex;
  gap: 8px;
}

.mode-btn {
  padding: 6px 16px;
  border: 1px solid rgba(46, 122, 198, 0.24);
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.3s;
  color: var(--q1-text);
}

.mode-btn:hover {
  border-color: var(--q1-accent);
  color: var(--q1-accent);
}

.mode-btn.active {
  background: linear-gradient(135deg, #1e5e9d, #2e7ac6);
  color: #f4fbff;
  border-color: #2e7ac6;
  font-weight: 700;
}

.legend {
  padding: 10px 12px;
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.93), rgba(241, 249, 255, 0.9));
  border: 1px solid var(--q1-border);
  border-radius: 12px;
}

.legend-title {
  font-weight: 700;
  color: var(--q1-title);
  margin-bottom: 8px;
  font-size: 13px;
}

.industry-legend-hint {
  font-size: 12px;
  color: var(--q1-muted);
  margin: 0;
}

.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.24s ease;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(46, 122, 198, 0.2);
}

.legend-item:hover {
  background: rgba(231, 243, 255, 0.8);
  transform: translateY(-1px);
}

.legend-item.inactive {
  opacity: 0.45;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: inline-block;
}

.legend-label {
  font-size: 12px;
  color: var(--q1-text);
}

.chart-container {
  flex: 1;
  min-height: 420px;
  border: 1px solid var(--q1-border);
  border-radius: 14px;
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.8);
}

.selected-info {
  position: absolute;
  top: 104px;
  right: 14px;
  width: 300px;
  max-height: 400px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(46, 122, 198, 0.3);
  border-radius: 12px;
  box-shadow: 0 16px 30px rgba(30, 77, 126, 0.18);
  overflow: hidden;
  z-index: 10;
  backdrop-filter: blur(8px);
  animation: slideInPanel 0.28s ease;
}

.selected-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: linear-gradient(140deg, #1f5f9d, #2d7cc8);
  color: #f5fbff;
  font-weight: 700;
  font-size: 13px;
}

.clear-btn {
  padding: 5px 10px;
  background: rgba(255, 255, 255, 0.94);
  color: #194f84;
  border: 1px solid rgba(29, 90, 146, 0.22);
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  transition: background 0.2s ease, transform 0.2s ease;
}

.clear-btn:hover {
  background: #ffffff;
  transform: translateY(-1px);
}

.selected-list {
  max-height: 338px;
  overflow-y: auto;
  padding: 10px 10px 6px;
}

.selected-node {
  padding: 9px 10px;
  margin-bottom: 8px;
  background: linear-gradient(155deg, #f9fcff, #eff7ff);
  border-radius: 8px;
  border-left: 3px solid var(--q1-accent-2);
  border-right: 1px solid rgba(46, 122, 198, 0.18);
}

.node-title {
  display: block;
  font-weight: 700;
  color: #1c4268;
  margin-bottom: 2px;
  line-height: 1.4;
}

.node-info {
  display: block;
  font-size: 12px;
  color: #557492;
  line-height: 1.5;
}

@keyframes slideInPanel {
  from {
    opacity: 0;
    transform: translateX(12px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@media (max-width: 1320px) {
  .selected-info {
    position: static;
    width: 100%;
    max-height: none;
  }
}

@media (max-width: 1024px) {
  .controls {
    padding: 10px;
  }

  .chart-container {
    min-height: 390px;
  }
}

@media (max-width: 760px) {
  .scatter-bubble-chart {
    gap: 8px;
  }

  .controls {
    gap: 10px;
    border-radius: 10px;
  }

  .control-item {
    width: 100%;
    justify-content: space-between;
  }

  .metric-select,
  .city-select {
    flex: 1;
    min-width: 0;
  }

  .legend-items {
    gap: 8px;
  }

  .chart-container {
    min-height: 360px;
    border-radius: 10px;
  }

  .selected-header {
    padding: 10px;
  }
}
</style>
