<template>
  <section class="q2-layout">
    <header class="hero-card">
      <div>
        <h2>
          <span class="title-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M4 19.2V4.8M10.4 19.2V10.4M16.8 19.2V7.2M3 19.2H21" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          Q2 职位画像分析 · 三主视图排版方案
        </h2>
        <p>支持最多三组职位对比，整合轮廓对比、路径解析与城市偏好分布。</p>
      </div>
      <div class="hero-actions">
        <label class="period-picker">
          <span class="picker-label">
            <span class="inline-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <rect x="3.5" y="5.5" width="17" height="15" rx="2.5" stroke="currentColor" stroke-width="1.8"/>
                <path d="M8 3.5V7M16 3.5V7M3.5 10H20.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              </svg>
            </span>
            分析周期
          </span>
          <select v-model="analysisPeriod">
            <option value="2024Q1">2024 Q1</option>
            <option value="2024Q2">2024 Q2</option>
            <option value="2024Q3">2024 Q3</option>
          </select>
        </label>
        <button class="ghost-btn" type="button">
          <span class="btn-inline">
            <span class="inline-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M12 4V14.5M12 14.5L8.2 10.7M12 14.5L15.8 10.7M4 18.5H20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            导出报告
          </span>
        </button>
      </div>
    </header>

    <section class="selector-card">
      <div class="selector-title">
        <span class="inline-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M8 5.2H20M8 12H20M8 18.8H20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            <circle cx="5" cy="5.2" r="1.8" fill="currentColor"/>
            <circle cx="5" cy="12" r="1.8" fill="currentColor"/>
            <circle cx="5" cy="18.8" r="1.8" fill="currentColor"/>
          </svg>
        </span>
        职位选择（最多3个）
      </div>
      <div class="selector-grid">
        <CustomSelect
          v-model="unifiedJobs[0]"
          :options="jobTitlesList"
          placeholder="职位 A"
          :max-visible="100"
        />
        <CustomSelect
          v-model="unifiedJobs[1]"
          :options="jobTitlesList"
          placeholder="职位 B"
          :max-visible="100"
        />
        <CustomSelect
          v-model="unifiedJobs[2]"
          :options="jobTitlesList"
          placeholder="职位 C"
          :max-visible="100"
        />
      </div>
      <div class="selector-actions">
        <button class="primary-btn" type="button" :disabled="!hasUnifiedJobs" @click="runSyncAnalysis">
          <span class="btn-inline">
            <span class="inline-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M20 12.2a8 8 0 0 1-13.7 5.7M4 11.8a8 8 0 0 1 13.7-5.7M5 16.8V18.9H7.1M18.9 5.1H16.8V3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            同步分析
          </span>
        </button>
        <button class="ghost-btn" type="button" @click="resetAll">
          <span class="btn-inline">
            <span class="inline-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M6.4 8.6A7.2 7.2 0 1 1 5 12M6.4 8.6V4.8M6.4 8.6H10.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            重置
          </span>
        </button>
      </div>
    </section>

    <section class="three-panel-grid">
      <article class="panel-card left-panel">
        <header class="panel-header">
          <h3 class="panel-title">
            <span class="title-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M12 4L19 8V16L12 20L5 16V8L12 4Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
                <path d="M12 4V20M5 8L19 16M19 8L5 16" stroke="currentColor" stroke-width="1.2" opacity="0.55"/>
              </svg>
            </span>
            轮廓对比图
          </h3>
        </header>
        <p class="panel-subtitle">薪资水平 / 技能要求 / 行业集中度 / 职业热度 / 城市分布广度</p>
        <div class="panel-body chart-shell">
          <Q2SilhouetteComparisonChart
            :data="chartData?.data"
            :city-breadth-scores="cityBreadthScores"
            :loading="loading"
            :error="error"
          />
        </div>
      </article>

      <article class="panel-card center-panel">
        <header class="panel-header">
          <h3 class="panel-title">
            <span class="title-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M4 6.5H10.5L13.5 9.5H20M4 17.5H10.5L13.5 14.5H20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="4" cy="6.5" r="1.6" fill="currentColor"/>
                <circle cx="20" cy="9.5" r="1.6" fill="currentColor"/>
                <circle cx="4" cy="17.5" r="1.6" fill="currentColor"/>
                <circle cx="20" cy="14.5" r="1.6" fill="currentColor"/>
              </svg>
            </span>
            路径流向图
          </h3>
          <span class="tiny-badge">
            <span class="inline-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M6 18L18 6M8.2 6H18V15.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            占比（%）
          </span>
        </header>
        <p class="panel-subtitle">技能水平 → 行业分布 → 市场需求 → 薪资水平</p>
        <div class="panel-body chart-shell">
          <SankeyChart
            :data="sankeyData?.data"
            :loading="sankeyLoading"
            :error="sankeyError"
            empty-message="选择职位后点击【同步分析】"
          />
        </div>
      </article>

      <article class="panel-card right-panel">
        <header class="panel-header">
          <h3 class="panel-title">
            <span class="title-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M15.5 7V16.5M8.5 8.5V17M3.5 6.7L8.1 4.2L15 7.1L20.3 4.3V17.2L15.9 19.7L9 16.8L3.5 19.7V6.7Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
              </svg>
            </span>
            偏好城市地图
          </h3>
          <span class="tiny-badge">
            <span class="inline-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <rect x="4.5" y="3.5" width="15" height="17" rx="2.8" stroke="currentColor" stroke-width="1.8"/>
                <path d="M9.5 12L11.2 13.7L14.7 10.3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            城市以匿名编码显示
          </span>
        </header>
        <div class="panel-body map-shell">
          <div class="map-controls">
            <label class="ctl">
              <span class="ctl-label"><i class="ctl-ico width"></i>窗口宽 {{ mapViewConfig.containerWidth }}%</span>
              <input v-model.number="mapViewConfig.containerWidth" type="range" min="55" max="100" step="1" />
            </label>
            <label class="ctl">
              <span class="ctl-label"><i class="ctl-ico height"></i>窗口高 {{ mapViewConfig.containerHeight }}px</span>
              <input v-model.number="mapViewConfig.containerHeight" type="range" min="360" max="780" step="10" />
            </label>
            <label class="ctl">
              <span class="ctl-label"><i class="ctl-ico layout"></i>地图大小 {{ mapViewConfig.layoutSize }}%</span>
              <input v-model.number="mapViewConfig.layoutSize" type="range" min="90" max="150" step="1" />
            </label>
            <label class="ctl">
              <span class="ctl-label"><i class="ctl-ico zoom"></i>地图缩放 {{ mapViewConfig.zoom.toFixed(2) }}</span>
              <input v-model.number="mapViewConfig.zoom" type="range" min="0.70" max="2.50" step="0.01" />
            </label>
            <label class="ctl">
              <span class="ctl-label"><i class="ctl-ico aspect"></i>地图宽高比 {{ mapViewConfig.aspectScale.toFixed(2) }}</span>
              <input v-model.number="mapViewConfig.aspectScale" type="range" min="0.58" max="1.05" step="0.01" />
            </label>
            <label class="ctl">
              <span class="ctl-label"><i class="ctl-ico centerx"></i>中心X {{ mapViewConfig.centerX }}%</span>
              <input v-model.number="mapViewConfig.centerX" type="range" min="5" max="95" step="0.5" />
            </label>
            <label class="ctl">
              <span class="ctl-label"><i class="ctl-ico centery"></i>中心Y {{ mapViewConfig.centerY }}%</span>
              <input v-model.number="mapViewConfig.centerY" type="range" min="5" max="95" step="0.5" />
            </label>
            <div class="map-nav-buttons">
              <button class="ghost-btn mini-btn with-icon" type="button" @click="zoomMapIn"><i class="nav-ico zoom-in"></i><span>放大</span></button>
              <button class="ghost-btn mini-btn with-icon" type="button" @click="zoomMapOut"><i class="nav-ico zoom-out"></i><span>缩小</span></button>
              <button class="ghost-btn mini-btn with-icon" type="button" @click="panMapLeft"><i class="nav-ico left"></i><span>左移</span></button>
              <button class="ghost-btn mini-btn with-icon" type="button" @click="panMapRight"><i class="nav-ico right"></i><span>右移</span></button>
              <button class="ghost-btn mini-btn with-icon" type="button" @click="panMapUp"><i class="nav-ico up"></i><span>上移</span></button>
              <button class="ghost-btn mini-btn with-icon" type="button" @click="panMapDown"><i class="nav-ico down"></i><span>下移</span></button>
              <button class="ghost-btn mini-btn with-icon" type="button" @click="resetMapViewport"><i class="nav-ico reset"></i><span>复位视图</span></button>
              <button class="ghost-btn mini-btn with-icon" type="button" @click="resetMapViewConfig"><i class="nav-ico fit"></i><span>重置地图尺寸</span></button>
            </div>
            <div class="map-hint"><i class="hint-ico"></i>支持鼠标滚轮缩放与按住拖拽平移，滑杆仅用于微调。</div>
          </div>
          <div
            class="map-resize-shell"
            :style="{
              width: `${mapViewConfig.containerWidth}%`,
              height: `${mapViewConfig.containerHeight}px`
            }"
          >
          <Q2CityPreferenceGeoMap
            ref="cityGeoRef"
            :markers="cityPreferenceMarkers"
            :active-job-slots="activeMapSlots"
            :loading="cityMapLoading"
            :selected-code="selectedCityCode"
            :chart-height="mapViewConfig.containerHeight"
            :map-layout-size="mapViewConfig.layoutSize"
            :map-center-x="mapViewConfig.centerX"
            :map-center-y="mapViewConfig.centerY"
            :map-zoom="mapViewConfig.zoom"
            :map-aspect-scale="mapViewConfig.aspectScale"
            @select-city="toggleCitySelection"
            @view-change="onMapViewChange"
          />
          </div>
          <div v-if="selectedCitySummary" class="city-summary-box">
            <div class="summary-title"><i class="summary-ico"></i>{{ selectedCitySummary.code }}（锁定）</div>
            <div class="summary-line">经纬度：{{ Number(selectedCitySummary.mappedLon || 0).toFixed(3) }}, {{ Number(selectedCitySummary.mappedLat || 0).toFixed(3) }}</div>
            <div class="summary-line">总需求：{{ selectedCitySummary.total }}</div>
            <div class="summary-line">职位A：{{ selectedCitySummary.counts[0] }}</div>
            <div class="summary-line">职位B：{{ selectedCitySummary.counts[1] }}</div>
            <div class="summary-line">职位C：{{ selectedCitySummary.counts[2] }}</div>
            <div class="summary-line">城市排名：Top {{ selectedCitySummary.rank }}</div>
          </div>
          <div class="map-legend">
            <button
              type="button"
              :class="['legend-item', { active: isMapSlotActive('A') }]"
              @click="toggleMapSlot('A')"
            >
              <i class="dot a"></i>职位 A：{{ legendJobs[0] }}
            </button>
            <button
              type="button"
              :class="['legend-item', { active: isMapSlotActive('B') }]"
              @click="toggleMapSlot('B')"
            >
              <i class="dot b"></i>职位 B：{{ legendJobs[1] }}
            </button>
            <button
              type="button"
              :class="['legend-item', { active: isMapSlotActive('C') }]"
              @click="toggleMapSlot('C')"
            >
              <i class="dot c"></i>职位 C：{{ legendJobs[2] }}
            </button>
            <div class="legend-status">{{ isAllMapSlotsSelected ? '当前：全部职位分布' : `当前：${activeMapSlots.join(' + ')} 分布` }}</div>
          </div>
          <div class="city-drilldown" v-if="selectedCitySummary">
            <div class="drilldown-title"><i class="drill-ico"></i>城市下钻 · {{ selectedCitySummary.code }}</div>
            <div class="drilldown-meta">总需求 {{ selectedCitySummary.total }}，主导职位 {{ selectedCityDominantLabel }}</div>
            <div class="drilldown-grid">
              <div
                v-for="item in selectedCityJobProfiles"
                :key="item.jobKey"
                :class="['drill-cell', item.slot]"
              >
                <div class="cell-head">{{ item.label }}</div>
                <div class="cell-main">{{ item.cityCount }}（{{ item.cityRatio }}%）</div>
                <div class="cell-sub">薪资 {{ item.salary || '--' }} / 经验 {{ item.experience || '--' }} / 学历 {{ item.education || '--' }}</div>
              </div>
            </div>
          </div>
        </div>
      </article>
    </section>

    <footer class="stats-bar">
      <div class="stat-item">
        <div class="stat-label"><i class="stat-ico sample"></i>分析样本</div>
        <div class="stat-value">{{ sampleCountText }} 条记录</div>
      </div>
      <div class="stat-item">
        <div class="stat-label"><i class="stat-ico industry"></i>覆盖行业</div>
        <div class="stat-value">{{ industryCoverage }} 个</div>
      </div>
      <div class="stat-item">
        <div class="stat-label"><i class="stat-ico city"></i>覆盖城市</div>
        <div class="stat-value">{{ cityCoverage }} 个</div>
      </div>
      <div class="stat-item">
        <div class="stat-label"><i class="stat-ico dimension"></i>分析维度</div>
        <div class="stat-value">5 大维度</div>
      </div>
    </footer>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useFetchData } from '@/utils/fetchData.js'
import { getJobTitlesList, getNestedBarData, getParallelCoordinatesData, getSankeyData } from '@/api/positionApi.js'
import { CHINA_CITY_ANCHORS, HOT_CITY_PRIORITY } from '@/config/chinaCityAnchors.js'
import Q2SilhouetteComparisonChart from '@/components/charts/Q2SilhouetteComparisonChart.vue'
import SankeyChart from '@/components/charts/SankeyChart.vue'
import Q2CityPreferenceGeoMap from '@/components/charts/Q2CityPreferenceGeoMap.vue'
import CustomSelect from '@/components/common/CustomSelect.vue'

const analysisPeriod = ref('2024Q2')
const jobTitlesList = ref([])
const unifiedJobs = ref(['', '', ''])

const selectedJobs = ref(['', '', ''])
const sankeyJobs = ref(['', '', ''])
const nestedJobs = ref(['', '', ''])

const sankeyMode = ref('compare')
const selectedDimensions = ref(['skill_level', 'industry_spread', 'market_demand'])
const sankeyData = ref(null)
const sankeyLoading = ref(false)
const sankeyError = ref(null)
const SANKEY_JOB_COLORS = ['#2f6df6', '#ef5350', '#37b568']

const nestedData = ref(null)
const cityBreadthScores = ref({})
const cityPreferenceMarkers = ref([])
const cityMapLoading = ref(false)
const selectedCityCode = ref('')
const cityGeoRef = ref(null)
const MAP_SLOTS = ['A', 'B', 'C']
const activeMapSlots = ref([...MAP_SLOTS])
const DEFAULT_MAP_VIEW_CONFIG = {
  containerWidth: 100,
  containerHeight: 560,
  layoutSize: 118,
  centerX: 50,
  centerY: 70,
  zoom: 1.18,
  aspectScale: 0.75
}
const mapViewConfig = ref({ ...DEFAULT_MAP_VIEW_CONFIG })

const hasUnifiedJobs = computed(() => unifiedJobs.value.some((job) => job && job.trim()))

const { data: chartData, loading, error, execute } = useFetchData(() => {
  const validJobs = selectedJobs.value.filter((job) => job && job.trim())
  if (!validJobs.length) {
    throw new Error('请至少选择一个职位')
  }
  return getParallelCoordinatesData(validJobs)
})

const sampleCountText = computed(() => {
  const count = chartData.value?.data?.positions?.reduce((sum, item) => {
    return sum + Number(item?.details?.job_frequency || 0)
  }, 0)
  return Number(count || 0).toLocaleString('zh-CN')
})

const industryCoverage = computed(() => {
  const nodes = sankeyData.value?.data?.nodes || []
  return nodes.filter((node) => node.category === '行业分布').length
})

const cityCoverage = computed(() => {
  return cityPreferenceMarkers.value.length
})

const legendJobs = computed(() => {
  const valid = selectedJobs.value.filter((job) => job && job.trim())
  const labels = valid.slice(0, 3).map((job) => `${job.slice(0, 6)}...${job.slice(-4)}`)
  while (labels.length < 3) labels.push('未选择')
  return labels
})

const selectedCitySummary = computed(() => {
  if (!selectedCityCode.value) return null
  return cityPreferenceMarkers.value.find((marker) => marker.code === selectedCityCode.value) || null
})

const isAllMapSlotsSelected = computed(() => activeMapSlots.value.length === MAP_SLOTS.length)

const selectedCityDominantLabel = computed(() => {
  const summary = selectedCitySummary.value
  if (!summary) return '--'
  const maxValue = Math.max(...summary.counts)
  const maxIndex = summary.counts.findIndex((v) => v === maxValue)
  if (maxValue <= 0 || maxIndex < 0) return '--'
  return ['职位A', '职位B', '职位C'][maxIndex]
})

const selectedCityJobProfiles = computed(() => {
  const summary = selectedCitySummary.value
  if (!summary) return []

  const positions = chartData.value?.data?.positions || []
  const detailByTitle = new Map(positions.map((item) => [item.job_title, item.details || {}]))
  const validTitles = selectedJobs.value.filter((job) => job && job.trim()).slice(0, 3)

  return [0, 1, 2].map((idx) => {
    const title = validTitles[idx]
    const details = title ? detailByTitle.get(title) : null
    const slot = ['slot-a', 'slot-b', 'slot-c'][idx]
    return {
      jobKey: `${summary.code}-${idx}-${title || 'none'}`,
      label: `职位${['A', 'B', 'C'][idx]} · ${title ? `${title.slice(0, 6)}...${title.slice(-4)}` : '未选择'}`,
      cityCount: summary.counts[idx] || 0,
      cityRatio: summary.ratios[idx] || 0,
      salary: details?.salary || '',
      experience: details?.experience || '',
      education: details?.education || '',
      slot
    }
  })
})

const toggleCitySelection = (cityCode) => {
  if (selectedCityCode.value === cityCode) {
    selectedCityCode.value = ''
  } else {
    selectedCityCode.value = cityCode
  }
}

const isMapSlotActive = (slot) => activeMapSlots.value.includes(slot)

const toggleMapSlot = (slot) => {
  if (!MAP_SLOTS.includes(slot)) return

  if (activeMapSlots.value.includes(slot)) {
    if (activeMapSlots.value.length === 1) {
      activeMapSlots.value = [...MAP_SLOTS]
      return
    }
    activeMapSlots.value = activeMapSlots.value.filter((item) => item !== slot)
    return
  }

  const next = [...activeMapSlots.value, slot]
  activeMapSlots.value = MAP_SLOTS.filter((item) => next.includes(item))
}

const onMapViewChange = (viewState) => {
  if (!viewState) return
  if (Number.isFinite(Number(viewState.zoom))) {
    mapViewConfig.value.zoom = Number(Number(viewState.zoom).toFixed(2))
  }
  if (Number.isFinite(Number(viewState.centerX))) {
    mapViewConfig.value.centerX = Number(Number(viewState.centerX).toFixed(1))
  }
  if (Number.isFinite(Number(viewState.centerY))) {
    mapViewConfig.value.centerY = Number(Number(viewState.centerY).toFixed(1))
  }
}

const zoomMapIn = () => cityGeoRef.value?.zoomIn?.()
const zoomMapOut = () => cityGeoRef.value?.zoomOut?.()
const panMapLeft = () => cityGeoRef.value?.panLeft?.()
const panMapRight = () => cityGeoRef.value?.panRight?.()
const panMapUp = () => cityGeoRef.value?.panUp?.()
const panMapDown = () => cityGeoRef.value?.panDown?.()

const resetMapViewport = () => {
  cityGeoRef.value?.resetView?.()
}

const resetMapViewConfig = () => {
  mapViewConfig.value = { ...DEFAULT_MAP_VIEW_CONFIG }
  nextTick(() => {
    cityGeoRef.value?.resetView?.()
  })
}

const stableHash = (text) => {
  let hash = 2166136261
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

const CHINA_PROJECTION = {
  width: 1400,
  height: 980,
  pad: 36,
  minLon: 73.502355,
  maxLon: 135.09567,
  minLat: 3.39716187,
  maxLat: 53.563269
}

const cityAnchorPool = CHINA_CITY_ANCHORS.filter(
  (item) => Number.isFinite(Number(item.lon)) && Number.isFinite(Number(item.lat))
)
const cityAnchorByName = new Map(cityAnchorPool.map((item) => [item.name, item]))
const hotCityAnchors = HOT_CITY_PRIORITY.map((name) => cityAnchorByName.get(name)).filter(Boolean)

// 热门映射目标：优先承接高频编码（真实热门城市）
const HOT_TARGET_CITY_NAMES = [
  '北京市',
  '成都市',
  '武汉市',
  '西安市',
  '重庆市',
  '天津市',
  '郑州市',
  '长沙市',
  '南京市',
  '济南市',
  '合肥市'
]

// 分散映射池：覆盖全国，避免全部压到华东华南
const SPREAD_TARGET_CITY_NAMES = [
  '乌鲁木齐市',
  '西宁市',
  '银川市',
  '兰州市',
  '西安市',
  '呼和浩特市',
  '太原市',
  '石家庄市',
  '北京市',
  '天津市',
  '济南市',
  '郑州市',
  '武汉市',
  '长沙市',
  '南昌市',
  '合肥市',
  '南京市',
  '成都市',
  '重庆市',
  '贵阳市',
  '昆明市',
  '南宁市',
  '长春市',
  '哈尔滨市',
  '沈阳市',
  '青岛市',
  '临沂市'
]

const hotTargetAnchors = HOT_TARGET_CITY_NAMES.map((name) => cityAnchorByName.get(name)).filter(Boolean)
const spreadTargetAnchors = SPREAD_TARGET_CITY_NAMES.map((name) => cityAnchorByName.get(name)).filter(Boolean)
const hotCityNameSet = new Set(hotTargetAnchors.map((item) => item.name))
// 限制最东/最北锚点，避免气泡中心落到海面视觉区域
const nonHotCityAnchors = spreadTargetAnchors.filter(
  (item) =>
    !hotCityNameSet.has(item.name) &&
    Number(item.lon) >= 87 &&
    Number(item.lon) <= 120.6 &&
    Number(item.lat) >= 24 &&
    Number(item.lat) <= 43.6
)

const MAINLAND_BBOX_PERCENT = {
  xMin: 19,
  xMax: 79,
  yMin: 12,
  yMax: 83
}

const HOT_BIND_TOP_N = 9

const projectLonLatToPercent = (lon, lat) => {
  const spanLon = CHINA_PROJECTION.maxLon - CHINA_PROJECTION.minLon
  const spanLat = CHINA_PROJECTION.maxLat - CHINA_PROJECTION.minLat
  const scaleX = (CHINA_PROJECTION.width - CHINA_PROJECTION.pad * 2) / spanLon
  const scaleY = (CHINA_PROJECTION.height - CHINA_PROJECTION.pad * 2) / spanLat
  const scale = Math.min(scaleX, scaleY)
  const mapWidth = spanLon * scale
  const offsetX = (CHINA_PROJECTION.width - mapWidth) / 2
  const x = offsetX + (lon - CHINA_PROJECTION.minLon) * scale
  const y = CHINA_PROJECTION.pad + (CHINA_PROJECTION.maxLat - lat) * scale
  return {
    x: (x / CHINA_PROJECTION.width) * 100,
    y: (y / CHINA_PROJECTION.height) * 100
  }
}

const buildCityAnchorAssignments = (markersRaw) => {
  const mapping = new Map()
  const used = new Set()
  const sorted = [...markersRaw].sort((a, b) => b.total - a.total)

  const findFirstUnused = (pool) => pool.find((candidate) => !used.has(candidate.name)) || null

  const findHashedUnused = (pool, code) => {
    if (!pool.length) return null
    const start = stableHash(code) % pool.length
    for (let step = 0; step < pool.length; step += 1) {
      const candidate = pool[(start + step) % pool.length]
      if (!used.has(candidate.name)) return candidate
    }
    return pool[start]
  }

  // 给编码分配锚点：高频->热门城市，其他->全国分散城市池
  sorted.forEach((item) => {
    let anchor = null

    if (mapping.size < Math.min(HOT_BIND_TOP_N, hotTargetAnchors.length)) {
      anchor = findFirstUnused(hotTargetAnchors)
    }

    if (!anchor) {
      anchor = findHashedUnused(nonHotCityAnchors, item.code)
    }

    if (!anchor) {
      anchor = findHashedUnused(cityAnchorPool, item.code)
    }

    if (anchor) {
      used.add(anchor.name)
      mapping.set(item.code, anchor)
    }
  })

  return mapping
}

const mappedPositionForCity = (cityCode, anchor) => {
  const base = projectLonLatToPercent(Number(anchor.lon), Number(anchor.lat))

  return {
    x: Math.min(MAINLAND_BBOX_PERCENT.xMax, Math.max(MAINLAND_BBOX_PERCENT.xMin, base.x)),
    y: Math.min(MAINLAND_BBOX_PERCENT.yMax, Math.max(MAINLAND_BBOX_PERCENT.yMin, base.y))
  }
}

const buildCityPreferenceMarkers = (jobCityLists) => {
  const cityAgg = new Map()

  jobCityLists.forEach((cities, idx) => {
    cities.forEach((item) => {
      const cityCode = item.city
      const count = Number(item.count || 0)
      if (!cityCode || count <= 0) return

      if (!cityAgg.has(cityCode)) {
        cityAgg.set(cityCode, { code: cityCode, counts: [0, 0, 0], total: 0 })
      }

      const entry = cityAgg.get(cityCode)
      entry.counts[idx] += count
      entry.total += count
    })
  })

  const markersRaw = Array.from(cityAgg.values())
    .sort((a, b) => b.total - a.total)
    .slice(0, 30)

  if (!markersRaw.length) return []
  const anchorMap = buildCityAnchorAssignments(markersRaw)

  const totals = markersRaw.map((m) => m.total)
  const sqrtMin = Math.sqrt(Math.min(...totals))
  const sqrtMax = Math.sqrt(Math.max(...totals))
  const span = Math.max(sqrtMax - sqrtMin, 1)

  const placed = []
  markersRaw.forEach((item, idx) => {
    const anchor = anchorMap.get(item.code)
    const base = anchor ? mappedPositionForCity(item.code, anchor) : { x: 50, y: 50 }
    const norm = (Math.sqrt(item.total) - sqrtMin) / span
    const radius = Math.round(10 + norm * 18)
    const total = Math.max(item.total, 1)
    const ratios = item.counts.map((count) => Number(((count / total) * 100).toFixed(2)))
    const tooltip = [
      `城市编码: ${item.code}`,
      `映射经纬度: ${anchor ? `${Number(anchor.lon).toFixed(3)}, ${Number(anchor.lat).toFixed(3)}` : '未知'}`,
      `总需求: ${item.total}`,
      `职位A: ${item.counts[0]} (${ratios[0]}%)`,
      `职位B: ${item.counts[1]} (${ratios[1]}%)`,
      `职位C: ${item.counts[2]} (${ratios[2]}%)`
    ].join(' | ')

    const marker = {
      ...item,
      x: base.x,
      y: base.y,
      radius,
      ratios,
      tooltip,
      rank: idx + 1,
      mappedCity: anchor?.name || '未知',
      mappedAdcode: anchor?.adcode || '',
      mappedLon: anchor?.lon,
      mappedLat: anchor?.lat
    }
    placed.push(marker)

    // 不再执行自动推挤，确保点位严格贴合映射经纬度。
  })

  return placed
}

const loadJobTitles = async () => {
  try {
    const response = await getJobTitlesList()
    jobTitlesList.value = response?.data?.job_titles || []

    if (jobTitlesList.value.length >= 3 && !hasUnifiedJobs.value) {
      unifiedJobs.value = [jobTitlesList.value[0], jobTitlesList.value[1], jobTitlesList.value[2]]
    }
  } catch (err) {
    console.error('加载职位列表失败:', err)
  }
}

const syncToAllViews = () => {
  selectedJobs.value = [...unifiedJobs.value]
  sankeyJobs.value = [...unifiedJobs.value]
  nestedJobs.value = [...unifiedJobs.value]
}

const loadParallelData = async () => {
  const validJobs = selectedJobs.value.filter((job) => job && job.trim())
  if (!validJobs.length) {
    return
  }
  await execute()
}

const loadSankeyData = async () => {
  try {
    sankeyLoading.value = true
    sankeyError.value = null

    const validJobs = sankeyJobs.value.filter((job) => job && job.trim())
    if (!validJobs.length) {
      return
    }

    const responses = await Promise.all(
      validJobs.slice(0, 3).map((jobTitle) => getSankeyData('compare', [jobTitle], selectedDimensions.value))
    )

    const mergedNodes = []
    const mergedLinks = []
    const nodeByKey = new Map()
    const mergedCategoriesSet = new Set()
    const jobLegend = []

    const ensureNode = (rawName, category) => {
      const safeName = String(rawName || '').trim()
      if (!safeName) return null
      const key = `${category || '未知'}|${safeName}`
      if (!nodeByKey.has(key)) {
        const node = {
          name: key,
          displayName: safeName,
          category: category || '未知'
        }
        nodeByKey.set(key, node)
        mergedNodes.push(node)
      }
      return key
    }

    responses.forEach((resp, idx) => {
      const sankeyPart = resp?.data || {}
      const nodes = Array.isArray(sankeyPart.nodes) ? sankeyPart.nodes : []
      const links = Array.isArray(sankeyPart.links) ? sankeyPart.links : []
      const categories = Array.isArray(sankeyPart.categories) ? sankeyPart.categories : []
      const slotLabel = `职位${['A', 'B', 'C'][idx]}`
      const color = SANKEY_JOB_COLORS[idx] || '#5b6f90'
      const jobTitle = validJobs[idx]

      jobLegend.push({
        slot: slotLabel,
        color,
        jobTitle
      })

      categories.forEach((c) => mergedCategoriesSet.add(c))

      const categoryByName = new Map()
      nodes.forEach((node) => {
        const rawName = String(node?.name || '').trim()
        if (!rawName) return
        const category = node?.category || '未知'
        categoryByName.set(rawName, category)
        ensureNode(rawName, category)
      })

      links.forEach((link) => {
        const sourceName = String(link?.source || '').trim()
        const targetName = String(link?.target || '').trim()
        const value = Number(link?.value || 0)
        if (!sourceName || !targetName || value <= 0) return

        const sourceCategory = categoryByName.get(sourceName) || '未知'
        const targetCategory = categoryByName.get(targetName) || '未知'
        const sourceKey = ensureNode(sourceName, sourceCategory)
        const targetKey = ensureNode(targetName, targetCategory)
        if (!sourceKey || !targetKey) return

        mergedLinks.push({
          source: sourceKey,
          target: targetKey,
          sourceLabel: sourceName,
          targetLabel: targetName,
          value,
          jobSlot: slotLabel,
          jobTitle,
          lineStyle: {
            color,
            opacity: 0.42,
            curveness: 0.45 + idx * 0.06
          }
        })
      })
    })

    sankeyData.value = {
      code: 200,
      message: '获取桑基图数据成功',
      data: {
        nodes: mergedNodes,
        links: mergedLinks,
        categories: Array.from(mergedCategoriesSet),
        jobLegend
      }
    }
  } catch (err) {
    console.error('加载桑基图数据失败:', err)
    sankeyError.value = err?.message || '加载桑基图失败'
  } finally {
    sankeyLoading.value = false
  }
}

const loadNestedData = async () => {
  const validJobs = nestedJobs.value.filter((job) => job && job.trim())
  if (!validJobs.length) {
    nestedData.value = null
    return
  }

  try {
    nestedData.value = await getNestedBarData(validJobs, null)
  } catch (err) {
    console.error('加载嵌套数据失败:', err)
    nestedData.value = null
  }
}

const loadCityBreadthScores = async () => {
  const validJobs = selectedJobs.value.filter((job) => job && job.trim())
  if (!validJobs.length) {
    cityBreadthScores.value = {}
    cityPreferenceMarkers.value = []
    return
  }

  try {
    cityMapLoading.value = true
    selectedCityCode.value = ''
    const pairs = await Promise.all(
      validJobs.map(async (jobTitle) => {
        const response = await getNestedBarData(validJobs, jobTitle)
        const cityCount = Number(response?.data?.micro_analysis?.all_cities?.length || 0)
        const cities = response?.data?.micro_analysis?.all_cities || []
        return { jobTitle, cityCount, cities }
      })
    )

    const rawMap = Object.fromEntries(pairs.map((item) => [item.jobTitle, item.cityCount]))
    const values = Object.values(rawMap)

    if (!values.length) {
      cityBreadthScores.value = {}
      return
    }

    const minV = Math.min(...values)
    const maxV = Math.max(...values)
    const normalized = {}

    Object.entries(rawMap).forEach(([jobTitle, value]) => {
      let score = 0
      if (maxV === minV) {
        score = value > 0 ? 100 : 0
      } else {
        score = ((value - minV) / (maxV - minV)) * 100
      }
      normalized[jobTitle] = Number(score.toFixed(1))
    })

    cityBreadthScores.value = normalized
    const cityLists = pairs.map((item) => item.cities)
    cityPreferenceMarkers.value = buildCityPreferenceMarkers(cityLists)
  } catch (err) {
    console.error('加载城市分布广度失败:', err)
    cityBreadthScores.value = {}
    cityPreferenceMarkers.value = []
  } finally {
    cityMapLoading.value = false
  }
}

const runSyncAnalysis = async () => {
  syncToAllViews()
  await Promise.all([loadParallelData(), loadSankeyData(), loadNestedData(), loadCityBreadthScores()])
}

const resetAll = () => {
  unifiedJobs.value = ['', '', '']
  selectedJobs.value = ['', '', '']
  sankeyJobs.value = ['', '', '']
  nestedJobs.value = ['', '', '']
  sankeyData.value = null
  sankeyError.value = null
  nestedData.value = null
  cityBreadthScores.value = {}
  cityPreferenceMarkers.value = []
  selectedCityCode.value = ''
  activeMapSlots.value = [...MAP_SLOTS]
  chartData.value = null
}

onMounted(async () => {
  await loadJobTitles()
})
</script>

<style scoped>
.q2-layout {
  --job-a: #2f6df6;
  --job-b: #ef5350;
  --job-c: #37b568;
  font-family: 'Noto Sans SC', 'Source Han Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  border-radius: 16px;
  background: radial-gradient(circle at 12% 12%, #f3f7ff 0%, #eef3fb 35%, #e9eef8 100%);
}

.hero-card,
.selector-card,
.panel-card,
.stats-bar {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(80, 111, 174, 0.12);
  border-radius: 14px;
  box-shadow: 0 8px 20px rgba(64, 89, 138, 0.08);
}

.hero-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px 18px;
  gap: 16px;
}

.hero-card h2 {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  color: #0d2a57;
  font-size: 30px;
  line-height: 1.2;
}

.hero-card p {
  margin: 8px 0 0;
  color: #4e6388;
  font-size: 15px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-icon,
.inline-icon {
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #2f6df6;
  flex: 0 0 auto;
}

.title-icon svg,
.inline-icon svg {
  width: 100%;
  height: 100%;
}

.period-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #234677;
  font-size: 13px;
  font-weight: 600;
}

.picker-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.period-picker select {
  border: 1px solid #c9d7ef;
  border-radius: 10px;
  background: #f7f9fe;
  color: #163a71;
  padding: 8px 12px;
}

.selector-card {
  padding: 14px 16px;
  display: grid;
  grid-template-columns: 220px 1fr auto;
  align-items: center;
  gap: 12px;
}

.selector-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #173c72;
  font-size: 19px;
}

.selector-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: 10px;
}

.selector-actions {
  display: flex;
  gap: 8px;
}

.primary-btn,
.ghost-btn {
  border-radius: 10px;
  border: 1px solid transparent;
  padding: 9px 16px;
  font-weight: 700;
  cursor: pointer;
}

.btn-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-inline .inline-icon {
  width: 16px;
  height: 16px;
}

.primary-btn {
  color: #fff;
  background: linear-gradient(135deg, #2f6df6 0%, #1b57dc 100%);
  box-shadow: 0 6px 14px rgba(47, 109, 246, 0.25);
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ghost-btn {
  color: #20457a;
  background: #f4f7fd;
  border-color: #c7d5ec;
}

.three-panel-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.panel-card {
  display: flex;
  flex-direction: column;
  min-height: 620px;
  padding: 12px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.panel-header h3 {
  margin: 0;
  color: #132f60;
  font-size: 30px;
}

.panel-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.panel-title .title-icon {
  width: 22px;
  height: 22px;
}

.tiny-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #315d98;
  background: #edf3ff;
  border: 1px solid #c9daf4;
  font-size: 12px;
  font-weight: 700;
  padding: 5px 10px;
  border-radius: 999px;
}

.tiny-badge .inline-icon {
  width: 14px;
  height: 14px;
  color: #315d98;
}

.panel-subtitle {
  margin: 6px 0 10px;
  color: #4a5f84;
  font-size: 13px;
}

.panel-body {
  flex: 1;
  min-height: 0;
}

.chart-shell {
  border: 1px solid #dbe6f7;
  border-radius: 12px;
  overflow: hidden;
  background: #fbfdff;
}

.map-shell {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid #dbe6f7;
  border-radius: 12px;
  background: #ffffff;
  padding: 10px;
}

.map-controls {
  display: grid;
  grid-template-columns: repeat(7, minmax(140px, 1fr));
  gap: 8px 10px;
  align-items: end;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid #d7e3f7;
  border-radius: 10px;
  padding: 8px 10px;
}

.ctl {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.ctl span {
  font-size: 12px;
  color: #294f84;
  font-weight: 700;
}

.ctl-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ctl-ico {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  display: inline-block;
  border: 1.5px solid #5f84ba;
  background: #f3f8ff;
  position: relative;
}

.ctl-ico.width::before,
.ctl-ico.height::before,
.ctl-ico.layout::before,
.ctl-ico.zoom::before,
.ctl-ico.aspect::before,
.ctl-ico.centerx::before,
.ctl-ico.centery::before {
  content: '';
  position: absolute;
  inset: 2px;
  border-radius: 2px;
  background: rgba(47, 109, 246, 0.24);
}

.ctl-ico.height::before {
  inset: 1px 4px;
}

.ctl-ico.layout::before {
  inset: 4px 1px 4px 1px;
}

.ctl-ico.zoom::before {
  width: 5px;
  height: 5px;
  border-radius: 999px;
  top: 2px;
  left: 2px;
}

.ctl-ico.zoom::after {
  content: '';
  position: absolute;
  width: 5px;
  height: 1.5px;
  background: #5f84ba;
  transform: rotate(45deg);
  right: 0;
  bottom: 1px;
}

.ctl-ico.aspect::before {
  inset: 4px 2px;
}

.ctl-ico.centerx::before {
  inset: 2px 1px;
}

.ctl-ico.centery::before {
  inset: 1px 2px;
}

.ctl input[type='range'] {
  width: 100%;
}

.mini-btn {
  padding: 7px 10px;
  font-size: 12px;
  white-space: nowrap;
}

.mini-btn.with-icon {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.nav-ico {
  width: 13px;
  height: 13px;
  display: inline-block;
  position: relative;
  border: 1.5px solid #4f76ad;
  border-radius: 999px;
}

.nav-ico::before {
  content: '';
  position: absolute;
  inset: 3px;
  border: solid #4f76ad;
  border-width: 0 1.5px 1.5px 0;
  transform: rotate(45deg);
}

.nav-ico.zoom-in::after,
.nav-ico.zoom-out::after {
  content: '';
  position: absolute;
  width: 5px;
  height: 1.5px;
  background: #4f76ad;
  left: 3px;
  top: 5.2px;
}

.nav-ico.zoom-in::before {
  border: none;
  width: 1.5px;
  height: 5px;
  background: #4f76ad;
  left: 5px;
  top: 3px;
  transform: none;
}

.nav-ico.zoom-out::before {
  border: none;
}

.nav-ico.left::before {
  inset: 3px 4px 3px 2px;
  transform: rotate(135deg);
}

.nav-ico.right::before {
  inset: 3px 2px 3px 4px;
  transform: rotate(-45deg);
}

.nav-ico.up::before {
  inset: 2px 3px 4px 3px;
  transform: rotate(-135deg);
}

.nav-ico.down::before {
  inset: 4px 3px 2px 3px;
  transform: rotate(45deg);
}

.nav-ico.reset::before {
  border: none;
  width: 6px;
  height: 6px;
  border-radius: 999px;
  border: 1.5px solid #4f76ad;
  border-right-color: transparent;
  left: 2px;
  top: 2px;
  transform: rotate(-30deg);
}

.nav-ico.fit::before {
  inset: 2px;
  border: none;
  border-radius: 1px;
  background: rgba(79, 118, 173, 0.2);
  transform: none;
}

.map-nav-buttons {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.map-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  grid-column: 1 / -1;
  font-size: 12px;
  color: #5a7093;
  font-weight: 600;
}

.hint-ico {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  border: 1.5px solid #5a7eaf;
  display: inline-block;
  position: relative;
}

.hint-ico::before {
  content: 'i';
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: 10px;
  color: #5a7eaf;
  font-weight: 700;
}

.map-resize-shell {
  resize: both;
  overflow: hidden;
  max-width: 100%;
  min-width: 55%;
  min-height: 360px;
  border-radius: 10px;
  border: 1px solid #d5e1f5;
  align-self: center;
}

.summary-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 800;
  margin-bottom: 4px;
}

.summary-ico,
.drill-ico {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  border: 1.5px solid #4f76ad;
  display: inline-block;
  position: relative;
}

.summary-ico::before {
  content: '';
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 999px;
  background: #4f76ad;
  left: 4px;
  top: 4px;
}

.drill-ico::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 2px;
  width: 4px;
  height: 8px;
  border: 1.5px solid #4f76ad;
  border-top: none;
}

.summary-line {
  font-size: 12px;
  line-height: 1.35;
}

.city-summary-box {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #c8d7f0;
  border-radius: 10px;
  padding: 8px 10px;
  color: #274d81;
}

.map-legend {
  display: grid;
  gap: 6px;
  width: fit-content;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid #c8d7f0;
  border-radius: 10px;
  padding: 8px 10px;
  color: #294f84;
  font-size: 12px;
  font-weight: 600;
  margin-left: auto;
}

.legend-item {
  border: 1px solid rgba(92, 124, 177, 0.28);
  background: rgba(246, 250, 255, 0.92);
  color: #294f84;
  border-radius: 8px;
  padding: 6px 8px;
  font-size: 12px;
  font-weight: 700;
  text-align: left;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.legend-item:hover {
  border-color: rgba(47, 109, 246, 0.42);
  transform: translateY(-1px);
}

.legend-item.active {
  border-color: rgba(47, 109, 246, 0.55);
  background: linear-gradient(135deg, rgba(224, 238, 255, 0.95), rgba(240, 248, 255, 0.95));
  box-shadow: 0 3px 10px rgba(47, 109, 246, 0.18);
}

.legend-status {
  margin-top: 2px;
  color: #4c6996;
  font-size: 11px;
  font-weight: 700;
  text-align: right;
}

.city-drilldown {
  border: 1px solid #d6e2f6;
  border-radius: 10px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.9);
}

.drilldown-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #123a72;
  font-size: 13px;
  font-weight: 800;
}

.drilldown-meta {
  margin-top: 2px;
  color: #4d6690;
  font-size: 12px;
}

.drilldown-grid {
  margin-top: 7px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.drill-cell {
  border-radius: 8px;
  border: 1px solid #d5e2f6;
  padding: 6px 7px;
  background: #f9fbff;
}

.drill-cell.slot-a {
  border-left: 3px solid var(--job-a);
}

.drill-cell.slot-b {
  border-left: 3px solid var(--job-b);
}

.drill-cell.slot-c {
  border-left: 3px solid var(--job-c);
}

.cell-head {
  color: #214980;
  font-size: 12px;
  font-weight: 700;
}

.cell-main {
  color: #163c72;
  font-size: 14px;
  font-weight: 800;
  margin-top: 2px;
}

.cell-sub {
  color: #5a7093;
  font-size: 11px;
  margin-top: 2px;
}

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  margin-right: 6px;
}

.dot.a {
  background: var(--job-a);
}

.dot.b {
  background: var(--job-b);
}

.dot.c {
  background: var(--job-c);
}

.stats-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  padding: 8px;
}

.stat-item {
  background: #f7faff;
  border: 1px solid #d9e4f8;
  border-radius: 10px;
  padding: 10px 12px;
}

.stat-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #5b6d8d;
  font-size: 12px;
  margin-bottom: 4px;
}

.stat-ico {
  width: 13px;
  height: 13px;
  border-radius: 4px;
  display: inline-block;
  background: #dbe8fb;
  border: 1px solid #9bb8e0;
  position: relative;
}

.stat-ico::before {
  content: '';
  position: absolute;
  inset: 3px;
  border-radius: 2px;
  background: #5f88bf;
}

.stat-ico.industry::before {
  border-radius: 999px;
}

.stat-ico.city::before {
  inset: 2px 4px;
}

.stat-ico.dimension::before {
  inset: 4px 2px;
}

.stat-value {
  color: #18386b;
  font-size: 25px;
  font-weight: 700;
}

@media (max-width: 1200px) {
  .hero-card h2 {
    font-size: 26px;
  }

  .panel-header h3 {
    font-size: 24px;
  }

  .selector-card {
    grid-template-columns: 1fr;
  }

  .selector-actions {
    justify-content: flex-end;
  }

  .three-panel-grid {
    grid-template-columns: 1fr;
  }

  .panel-card {
    min-height: 560px;
  }

  .drilldown-grid {
    grid-template-columns: 1fr;
  }

  .map-controls {
    grid-template-columns: 1fr 1fr 1fr;
  }
}
</style>
