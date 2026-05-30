<template>
  <div class="q3-dual-view">
    <div class="toolbar">
      <div class="toolbar-item">
        <label>聚类数</label>
        <select v-model.number="nClusters">
          <option v-for="n in [4, 5, 6, 7]" :key="`k-${n}`" :value="n">{{ n }} 类</option>
        </select>
      </div>

      <div class="toolbar-item">
        <label>算法</label>
        <select v-model="algorithm">
          <option value="gmm">GMM</option>
          <option value="kmeans">KMeans</option>
        </select>
      </div>

      <div class="toolbar-item">
        <label>样本量</label>
        <select v-model.number="sampleSize">
          <option :value="6000">6000</option>
          <option :value="12000">12000</option>
          <option :value="20000">20000</option>
          <option :value="30000">30000</option>
          <option :value="50000">50000</option>
        </select>
      </div>

      <div class="toolbar-item">
        <label>投影模式</label>
        <select v-model="coordMode" @change="renderScatter">
          <option value="business">业务坐标</option>
          <option value="pca">PCA坐标</option>
        </select>
      </div>

      <div class="toolbar-item">
        <label>平行模式</label>
        <select v-model="parallelMode" @change="renderParallel">
          <option value="centroid">质心聚合</option>
          <option value="sampled">分层抽样</option>
        </select>
      </div>

      <button class="reload-btn" type="button" @click="reloadData">刷新聚类</button>
    </div>

    <div v-if="loading" class="state">聚类计算中...</div>
    <div v-else-if="error" class="state error">{{ error }}</div>
    <div v-else-if="!points.length" class="state">暂无可用聚类数据</div>
    <div v-else-if="renderError" class="state error">{{ renderError }}</div>

    <div v-else class="main-grid">
      <section class="panel">
        <div class="panel-head">
          <h3>视图一：薪酬模式聚类降维图</h3>
          <span class="meta">{{ coordModeLabel }} · 显示 {{ visiblePointCount }} / {{ points.length }} 点 · scatter</span>
        </div>

        <div class="legend-row">
          <span
            v-for="item in clusterSummary"
            :key="`legend-c${item.cluster_id}`"
            class="legend-item"
            :class="{ active: activeClusterId === item.cluster_id }"
            @click="toggleCluster(item.cluster_id)"
          >
            <i class="dot" :style="{ background: clusterColor(item.cluster_id) }"></i>
            C{{ item.cluster_id }} {{ item.cluster_label }}
          </span>
        </div>

        <div ref="scatterRef" class="chart scatter"></div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h3>视图二：多维特征关联平行坐标系</h3>
          <span class="meta">{{ parallelModeLabel }} · {{ parallelRows.length }} 线</span>
        </div>
        <div ref="parallelRef" class="chart parallel"></div>
      </section>
    </div>

    <div v-if="points.length" class="insight-grid">
      <div class="insight-card">
        <h4>Scatter -> Parallel</h4>
        <p>{{ scatterToParallelDesc }}</p>
      </div>
      <div class="insight-card">
        <h4>Parallel -> Scatter</h4>
        <p>{{ parallelToScatterDesc }}</p>
      </div>
      <div class="insight-card" v-if="selectedPoint">
        <h4>当前点位</h4>
        <p>
          {{ selectedPoint.job_title }} · C{{ selectedPoint.cluster_id }}
          · 中位薪资 {{ formatSalary(selectedPoint.features?.median_salary) }}
          · {{ selectedPoint.company_type }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' }
})

const emit = defineEmits(['reload'])

const scatterRef = ref(null)
const parallelRef = ref(null)

const nClusters = ref(5)
const algorithm = ref('gmm')
const sampleSize = ref(12000)
const coordMode = ref('pca')
const parallelMode = ref('centroid')

const activeClusterId = ref(null)
const selectedPoint = ref(null)

const scatterSelectedIds = ref([])
const parallelFilteredPointIds = ref([])
const renderError = ref('')

let scatterChart = null
let parallelChart = null
let scatterObserver = null
let parallelObserver = null

const points = computed(() => props.data?.points || [])
const clusterSummary = computed(() => props.data?.cluster_summary || [])
const metadata = computed(() => props.data?.metadata || {})
const parallelPayload = computed(() => props.data?.parallel_payload || {})
const axisMeta = computed(() => parallelPayload.value?.axis_meta || {})

const projectionMethodText = computed(() => {
  const m = String(metadata.value?.projection_method || '').toLowerCase()
  if (m.startsWith('pca')) return m.includes('separated') ? 'PCA(簇分离)' : 'PCA'
  if (m === 'umap') return 'UMAP'
  if (m === 'lda') return 'LDA'
  return 'Projection'
})

const coordModeLabel = computed(() => (
  coordMode.value === 'business'
    ? '业务坐标(薪资/门槛)'
    : `${projectionMethodText.value}坐标`
))
const axisXName = computed(() => (coordMode.value === 'business' ? '中位薪资(K)' : 'PC1'))
const axisYName = computed(() => (coordMode.value === 'business' ? '门槛指数' : 'PC2'))

const parallelModeLabel = computed(() => parallelMode.value === 'centroid' ? '方案A：质心聚合' : '方案B：分层抽样')

const parallelRows = computed(() => {
  const p = parallelPayload.value || {}
  return parallelMode.value === 'centroid'
    ? (p.centroid_lines || [])
    : (p.sampled_lines || [])
})

const clusterPalette = ['#2d7cff', '#ef4444', '#00b894', '#f59e0b', '#7b61ff', '#14b8a6', '#f97316', '#ec4899']
const clusterColor = (cid) => clusterPalette[Math.abs(Number(cid) || 0) % clusterPalette.length]

const formatSalary = (v) => `${Number(v || 0).toFixed(1)}K`

const pointById = computed(() => {
  const out = new Map()
  points.value.forEach((p, i) => {
    out.set(Number(p.point_id ?? i), p)
  })
  return out
})

const pointIdsByCluster = computed(() => {
  const m = new Map()
  points.value.forEach((p, i) => {
    const cid = Number(p.cluster_id || 0)
    const pid = Number(p.point_id ?? i)
    if (!m.has(cid)) m.set(cid, [])
    m.get(cid).push(pid)
  })
  return m
})

const selectedClusterSetFromScatter = computed(() => {
  if (!scatterSelectedIds.value.length) return new Set()
  const s = new Set()
  scatterSelectedIds.value.forEach((id) => {
    const p = pointById.value.get(Number(id))
    if (p) s.add(Number(p.cluster_id || 0))
  })
  return s
})

const effectiveHighlightSet = computed(() => {
  const a = new Set((scatterSelectedIds.value || []).map((x) => Number(x)))
  const b = new Set((parallelFilteredPointIds.value || []).map((x) => Number(x)))
  if (!a.size && !b.size) return null
  if (a.size && !b.size) return a
  if (!a.size && b.size) return b
  const inter = new Set()
  a.forEach((x) => {
    if (b.has(x)) inter.add(x)
  })
  return inter
})

const scatterToParallelDesc = computed(() => {
  const n = scatterSelectedIds.value.length
  if (!n) return '在散点图使用矩形/套索框选后，平行坐标中对应线条会高亮，其余线条置灰。'
  return `已从散点图选中 ${n} 个点，平行坐标联动高亮中。`
})

const parallelToScatterDesc = computed(() => {
  const n = parallelFilteredPointIds.value.length
  if (!n) return '在平行坐标轴上刷选区间后，散点图中满足条件的点会放大高亮。'
  return `已从平行坐标筛出 ${n} 个点，散点图联动高亮中。`
})

const reloadData = () => {
  emit('reload', {
    nClusters: Number(nClusters.value || 5),
    algorithm: String(algorithm.value || 'gmm'),
    sampleSize: Number(sampleSize.value || 12000)
  })
}

const toggleCluster = (cid) => {
  const next = Number(cid)
  activeClusterId.value = Number(activeClusterId.value) === next ? null : next
  renderScatter()
}

const pointIsHighlighted = (pid) => {
  const set = effectiveHighlightSet.value
  if (!set) return true
  return set.has(Number(pid))
}

const visiblePointCount = computed(() => {
  if (activeClusterId.value == null) return points.value.length
  return points.value.filter((p) => Number(p.cluster_id) === Number(activeClusterId.value)).length
})

const baseCoordOfPoint = (p) => {
  if (coordMode.value === 'business') {
    return [
      Number(p?.features?.median_salary || 0),
      Number(p?.cluster_inputs?.barrier_index || 0)
    ]
  }
  return [Number(p?.umap_x || 0), Number(p?.umap_y || 0)]
}

const axisRange = (values, padRatio = 0.08) => {
  if (!values.length) return { min: 0, max: 1 }
  const minVal = Math.min(...values)
  const maxVal = Math.max(...values)
  const span = Math.max(1e-6, maxVal - minVal)
  const pad = Math.max(span * padRatio, coordMode.value === 'business' ? 0.05 : 0.02)
  return { min: minVal - pad, max: maxVal + pad }
}

const buildDuplicateAwareJitter = () => {
  const buckets = new Map()
  points.value.forEach((p, i) => {
    const pid = Number(p.point_id ?? i)
    const [bx, by] = baseCoordOfPoint(p)
    // 以原始坐标+簇分桶，避免不同簇完全压在同一点位
    const key = [
      Number(bx || 0).toFixed(4),
      Number(by || 0).toFixed(4),
      Number(p.cluster_id || 0)
    ].join('|')
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key).push(pid)
  })

  const jitterByPid = new Map()
  const dupCountByPid = new Map()
  const golden = Math.PI * (3 - Math.sqrt(5))

  buckets.forEach((pidList) => {
    const n = pidList.length
    const sorted = [...pidList].sort((a, b) => a - b)
    const spread = coordMode.value === 'pca'
      ? Math.min(1.3, 1 + 0.08 * Math.log2(n + 1))
      : Math.min(2.1, 1 + 0.18 * Math.log2(n + 1))

    sorted.forEach((pid, idx) => {
      dupCountByPid.set(pid, n)
      if (n <= 1) {
        jitterByPid.set(pid, [0, 0])
        return
      }
      // Sunflower 排布：重复越多，半径越大，但整体仍围绕原坐标
      const r = Math.sqrt(idx + 0.5)
      const a = idx * golden
      const base = coordMode.value === 'pca' ? 0.012 : 0.075
      const ratioY = coordMode.value === 'pca' ? 0.92 : 0.3
      const dx = Math.cos(a) * r * base * spread
      const dy = Math.sin(a) * r * base * ratioY * spread
      jitterByPid.set(pid, [dx, dy])
    })
  })

  return { jitterByPid, dupCountByPid }
}

const renderScatter = () => {
  try {
    renderError.value = ''
    if (!scatterRef.value || !points.value.length) return
    if (!scatterChart) scatterChart = echarts.init(scatterRef.value)
    const { jitterByPid, dupCountByPid } = buildDuplicateAwareJitter()
    const dense = points.value.length >= 10000
    const countVals = points.value.map((p) => Math.log1p(Math.max(0, Number(p?.features?.records_count || 0))))
    const minLogCount = Math.min(...countVals)
    const maxLogCount = Math.max(...countVals)
    const logSpan = Math.max(1e-6, maxLogCount - minLogCount)

    const rows = points.value.map((p, i) => {
      const pid = Number(p.point_id ?? i)
      const clusterMatch = activeClusterId.value == null || Number(p.cluster_id) === Number(activeClusterId.value)
      const visible = clusterMatch
      const [bx, by] = baseCoordOfPoint(p)
      const [jx, jy] = jitterByPid.get(pid) || [0, 0]
      const rec = Math.log1p(Math.max(0, Number(p?.features?.records_count || 0)))
      const norm = (rec - minLogCount) / logSpan
      const sized = 2.1 + norm * 4.1
      return {
        value: [Number(bx || 0) + jx, Number(by || 0) + jy],
        baseValue: [Number(bx || 0), Number(by || 0)],
        raw: p,
        pid,
        duplicateCount: Number(dupCountByPid.get(pid) || 1),
        itemStyle: {
          color: clusterColor(p.cluster_id),
          opacity: visible ? (dense ? 0.42 : 0.58) : 0.05
        },
        symbolSize: visible ? sized : 1.5
      }
    })
    const xRange = axisRange(rows.map((r) => Number(r.value?.[0] || 0)))
    const yRange = axisRange(rows.map((r) => Number(r.value?.[1] || 0)))

    const centerMap = new Map()
    rows.forEach((row) => {
      const cid = Number(row?.raw?.cluster_id || 0)
      if (activeClusterId.value != null && cid !== Number(activeClusterId.value)) return
      if (!centerMap.has(cid)) centerMap.set(cid, { sx: 0, sy: 0, n: 0 })
      const c = centerMap.get(cid)
      c.sx += Number(row.value?.[0] || 0)
      c.sy += Number(row.value?.[1] || 0)
      c.n += 1
    })
    const centerData = [...centerMap.entries()]
      .filter(([, c]) => c.n > 0)
      .map(([cid, c]) => ({
        value: [c.sx / c.n, c.sy / c.n],
        cid: Number(cid)
      }))

    scatterChart.setOption({
    animation: false,
    grid: { left: 48, right: 22, top: 42, bottom: 48 },
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params) => {
        const d = params?.data?.raw
        if (!d) return ''
        const f = d.features || {}
        return [
          `<b>${d.job_title}</b>`,
          `簇：C${d.cluster_id} ${d.cluster_label || ''}`,
          `行业：${d.company_type || '未知'}`,
          `城市等级：${d.city_tier || '未知'}`,
          `中位薪资：${formatSalary(f.median_salary)}`,
          `经验/学历：${Number(f.avg_experience_rank || 0).toFixed(2)} / ${Number(f.avg_education_rank || 0).toFixed(2)}`,
          `同位重叠点：${Number(params?.data?.duplicateCount || 1)}`
        ].join('<br/>')
      }
    },
    toolbox: {
      right: 8,
      feature: {
        brush: { type: ['rect', 'polygon', 'clear'] }
      }
    },
    brush: {
      toolbox: ['rect', 'polygon', 'clear'],
      xAxisIndex: 0,
      yAxisIndex: 0,
      brushLink: 'all',
      outOfBrush: { colorAlpha: 0.06 }
    },
    xAxis: {
      type: 'value',
      name: axisXName.value,
      min: xRange.min,
      max: xRange.max,
      scale: true,
      nameTextStyle: { color: '#59687a' },
      axisLabel: { color: '#6d7786' },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } }
    },
    yAxis: {
      type: 'value',
      name: axisYName.value,
      min: yRange.min,
      max: yRange.max,
      scale: true,
      nameTextStyle: { color: '#59687a' },
      axisLabel: { color: '#6d7786' },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } }
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
      { type: 'inside', yAxisIndex: 0, filterMode: 'none' }
    ],
    series: [
      {
        type: 'scatter',
        symbol: 'circle',
        progressive: 5000,
        // 关闭 large 模式，确保每个点都能按 cluster_id 正确着色
        large: false,
        emphasis: {
          itemStyle: {
            borderColor: '#111827',
            borderWidth: 1
          }
        },
        data: rows
      },
      {
        type: 'scatter',
        symbol: 'diamond',
        data: centerData,
        symbolSize: 12,
        itemStyle: {
          color: '#111827',
          borderColor: '#ffffff',
          borderWidth: 1.2,
          opacity: 0.95
        },
        label: {
          show: true,
          position: 'top',
          formatter: (p) => `C${Number(p?.data?.cid || 0)}`,
          color: '#0f172a',
          fontSize: 11,
          fontWeight: 700
        },
        z: 8,
        tooltip: {
          formatter: (p) => `簇中心：C${Number(p?.data?.cid || 0)}`
        }
      }
    ]
    }, true)

    scatterChart.off('click')
    scatterChart.on('click', (params) => {
      const d = params?.data?.raw
      if (!d) return
      selectedPoint.value = d
    })

    scatterChart.off('brushselected')
    scatterChart.on('brushselected', (evt) => {
      const batch = evt?.batch?.[0]
      if (!batch || !Array.isArray(batch.selected)) {
        scatterSelectedIds.value = []
        renderParallel()
        return
      }
      const idxSet = new Set()
      batch.selected.forEach((part) => {
        ;(part.dataIndex || []).forEach((idx) => idxSet.add(Number(idx)))
      })
      const ids = [...idxSet]
        .map((idx) => rows[idx]?.pid)
        .filter((v) => Number.isFinite(Number(v)))
      scatterSelectedIds.value = Array.from(new Set(ids)).map((x) => Number(x))
      renderParallel()
    })
  } catch (e) {
    renderError.value = `散点渲染失败: ${e?.message || String(e)}`
    console.error('Q3 scatter render failed:', e)
  }
}

const lineHighlightedByScatter = (row) => {
  if (!scatterSelectedIds.value.length) return true
  if (parallelMode.value === 'centroid') {
    return selectedClusterSetFromScatter.value.has(Number(row.cluster_id || 0))
  }
  return scatterSelectedIds.value.includes(Number(row.id))
}

const rowToPointIds = (row) => {
  if (parallelMode.value === 'centroid') {
    return pointIdsByCluster.value.get(Number(row.cluster_id || 0)) || []
  }
  return [Number(row.id)]
}

const renderParallel = () => {
  try {
    renderError.value = ''
    if (!parallelRef.value || !parallelRows.value.length) return
    if (!parallelChart) parallelChart = echarts.init(parallelRef.value)

  const edu = axisMeta.value.education_labels || ['大专及以下', '本科', '硕士', '博士及以上']
  const exp = axisMeta.value.experience_labels || ['无经验', '1年以下', '1-3年', '3-5年', '5-7年', '7-10年', '10年以上']
  const city = axisMeta.value.city_labels || ['一线', '新一线', '二线', '其他']
  const company = axisMeta.value.company_labels || ['Other']
  const salaryRange = axisMeta.value.salary_range || [0, 100]

  const data = parallelRows.value.map((row) => {
    const picked = lineHighlightedByScatter(row)
    return {
      value: row.values,
      raw: row,
      lineStyle: {
        color: clusterColor(row.cluster_id),
        opacity: picked ? 0.85 : 0.06,
        width: picked ? 1.9 : 0.8
      }
    }
  })

    parallelChart.setOption({
    animation: false,
    parallel: {
      left: 56,
      right: 24,
      top: 56,
      bottom: 24,
      parallelAxisExpandable: true,
      parallelAxisExpandCount: 1,
      parallelAxisExpandCenter: 2
    },
    parallelAxisDefault: {
      type: 'value',
      nameLocation: 'end',
      nameGap: 10,
      axisLabel: { color: '#607286', fontSize: 10 },
      nameTextStyle: { color: '#4a5b6d', fontSize: 11 },
      areaSelectStyle: { width: 16, opacity: 0.2 },
      realtime: true
    },
    parallelAxis: [
      { dim: 0, name: 'education', min: 0, max: Math.max(0, edu.length - 1), interval: 1, axisLabel: { formatter: (v) => edu[Math.round(v)] || '' } },
      { dim: 1, name: 'experience', min: 0, max: Math.max(0, exp.length - 1), interval: 1, axisLabel: { formatter: (v) => exp[Math.round(v)] || '' } },
      { dim: 2, name: 'city_tier', min: 0, max: Math.max(0, city.length - 1), interval: 1, axisLabel: { formatter: (v) => city[Math.round(v)] || '' } },
      { dim: 3, name: 'company_type', min: 0, max: Math.max(0, company.length - 1), interval: 1, axisLabel: { formatter: (v) => company[Math.round(v)] || '' } },
      { dim: 4, name: 'salary_mean', min: Number(salaryRange[0] || 0), max: Number(salaryRange[1] || 100) }
    ],
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params) => {
        const d = params?.data?.raw
        if (!d) return ''
        return [
          `簇：C${d.cluster_id}`,
          `学历：${d.education_label}`,
          `经验：${d.experience_label}`,
          `城市：${d.city_label}`,
          `行业：${d.company_label}`,
          `薪资：${Number(d.salary_mean || 0).toFixed(1)}K`
        ].join('<br/>')
      }
    },
      series: [
        {
          type: 'parallel',
          lineStyle: { width: 1, opacity: 0.25 },
          data
        }
      ]
    }, true)

    parallelChart.off('click')
    parallelChart.on('click', (params) => {
      const row = params?.data?.raw
      if (!row) return
      const ids = rowToPointIds(row)
      parallelFilteredPointIds.value = ids
      if (parallelMode.value === 'centroid') {
        activeClusterId.value = Number(row.cluster_id)
        selectedPoint.value = null
      } else {
        const p = pointById.value.get(Number(row.id))
        if (p) {
          selectedPoint.value = p
          activeClusterId.value = Number(p.cluster_id)
        }
      }
      renderScatter()
      renderParallel()
    })

    parallelChart.off('axisareaselected')
    parallelChart.on('axisareaselected', () => {
      applyParallelAxisFilter()
    })
  } catch (e) {
    renderError.value = `平行坐标渲染失败: ${e?.message || String(e)}`
    console.error('Q3 parallel render failed:', e)
  }
}

const matchIntervals = (val, intervals) => {
  if (!intervals || !intervals.length) return true
  const numVal = Number(val)
  return intervals.some((it) => {
    if (!Array.isArray(it) || it.length < 2) return false
    const lo = Number(it[0])
    const hi = Number(it[1])
    return numVal >= lo && numVal <= hi
  })
}

const applyParallelAxisFilter = () => {
  if (!parallelChart || !parallelRows.value.length) return
  const option = parallelChart.getOption() || {}
  const axes = option.parallelAxis || []
  const intervalsByDim = {}

  axes.forEach((ax) => {
    const dim = Number(ax.dim)
    const intervals = Array.isArray(ax.activeIntervals) ? ax.activeIntervals : []
    if (Number.isFinite(dim) && intervals.length) {
      intervalsByDim[dim] = intervals
    }
  })

  const dims = Object.keys(intervalsByDim).map((x) => Number(x))
  if (!dims.length) {
    parallelFilteredPointIds.value = []
    renderScatter()
    renderParallel()
    return
  }

  const matchedRows = parallelRows.value.filter((row) => {
    const vals = row.values || []
    return dims.every((d) => matchIntervals(vals[d], intervalsByDim[d]))
  })

  const ids = []
  matchedRows.forEach((row) => {
    rowToPointIds(row).forEach((id) => ids.push(Number(id)))
  })
  parallelFilteredPointIds.value = Array.from(new Set(ids))
  renderScatter()
  renderParallel()
}

const handleWindowResize = () => {
  if (scatterChart) scatterChart.resize()
  if (parallelChart) parallelChart.resize()
}

const bindResizeObservers = () => {
  if (typeof ResizeObserver === 'undefined') return
  if (scatterRef.value && !scatterObserver) {
    scatterObserver = new ResizeObserver(() => {
      if (scatterChart) scatterChart.resize()
    })
    scatterObserver.observe(scatterRef.value)
  }
  if (parallelRef.value && !parallelObserver) {
    parallelObserver = new ResizeObserver(() => {
      if (parallelChart) parallelChart.resize()
    })
    parallelObserver.observe(parallelRef.value)
  }
}

watch(() => props.data, async (newData) => {
  if (!newData) return
  const m = newData?.metadata || {}
  nClusters.value = Number(m.n_clusters || nClusters.value || 5)
  algorithm.value = String(m.cluster_algorithm || algorithm.value || 'gmm')
  sampleSize.value = Number(m.sample_size || sampleSize.value || 12000)
  parallelMode.value = String(newData?.parallel_payload?.default_mode || 'centroid')

  scatterSelectedIds.value = []
  parallelFilteredPointIds.value = []
  selectedPoint.value = null

  // 默认展示全部类，不自动聚焦单个簇
  activeClusterId.value = null

  await nextTick()
  renderScatter()
  renderParallel()
}, { deep: true, immediate: true })

watch([parallelMode, activeClusterId, coordMode], () => {
  nextTick(() => {
    renderScatter()
    renderParallel()
  })
})

watch(() => props.loading, (v) => {
  if (!v) {
    nextTick(() => {
      renderScatter()
      renderParallel()
    })
  }
})

onMounted(() => {
  window.addEventListener('resize', handleWindowResize)
  nextTick(() => {
    bindResizeObservers()
    renderScatter()
    renderParallel()
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleWindowResize)
  if (scatterObserver) {
    scatterObserver.disconnect()
    scatterObserver = null
  }
  if (parallelObserver) {
    parallelObserver.disconnect()
    parallelObserver = null
  }
  if (scatterChart) scatterChart.dispose()
  if (parallelChart) parallelChart.dispose()
})
</script>

<style scoped>
.q3-dual-view {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.toolbar-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-item label {
  font-size: 12px;
  color: #475569;
}

.toolbar-item select {
  height: 30px;
  padding: 0 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
}

.reload-btn {
  height: 30px;
  padding: 0 12px;
  border: 1px solid #2563eb;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
}

.reload-btn:hover {
  background: #1d4ed8;
}

.state {
  padding: 14px;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
}

.state.error {
  background: #fef2f2;
  color: #b91c1c;
}

.main-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.panel {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  padding: 10px 12px 8px 12px;
}

.panel-head h3 {
  margin: 0;
  font-size: 14px;
  color: #1e293b;
}

.meta {
  font-size: 12px;
  color: #64748b;
}

.legend-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 12px 8px 12px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #475569;
  padding: 3px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  cursor: pointer;
}

.legend-item.active {
  border-color: #1d4ed8;
  background: #dbeafe;
  color: #1d4ed8;
}

.legend-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.chart {
  width: 100%;
}

.scatter {
  height: 560px;
}

.parallel {
  height: 560px;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.insight-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
}

.insight-card h4 {
  margin: 0 0 6px 0;
  font-size: 13px;
  color: #334155;
}

.insight-card p {
  margin: 0;
  font-size: 12px;
  line-height: 1.55;
  color: #475569;
}

@media (max-width: 1400px) {
  .main-grid {
    grid-template-columns: 1fr;
  }

  .scatter,
  .parallel {
    height: 520px;
  }

  .insight-grid {
    grid-template-columns: 1fr;
  }
}
</style>
