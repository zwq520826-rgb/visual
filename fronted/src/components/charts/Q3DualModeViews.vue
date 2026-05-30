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
        <label>坐标模式</label>
        <select v-model="coordMode" @change="renderScatter">
          <option value="pca">聚类投影</option>
          <option value="business">业务坐标</option>
        </select>
      </div>

      <div class="toolbar-item">
        <label>轮廓模式</label>
        <select v-model="contourMode" @change="renderScatter">
          <option value="circle">圆形</option>
          <option value="original">原始</option>
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
          <h3>视图一：薪酬模式聚类分布图</h3>
          <span class="meta">{{ coordModeLabel }} · 显示 {{ visiblePointCount }} / {{ points.length }} 点 · scatter</span>
        </div>

        <div class="legend-row">
          <span
            v-for="item in clusterSummaryDisplay"
            :key="`legend-c${item.cluster_id}`"
            class="legend-item"
            :class="{ active: Number(activeClusterId) === Number(item.cluster_id) }"
            @click="toggleCluster(item.cluster_id)"
          >
            <i class="dot" :style="{ background: clusterColor(item.cluster_id) }"></i>
            {{ clusterDisplayText(item.cluster_id) }}
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
          {{ selectedPoint.job_title }} · {{ clusterDisplayText(selectedPoint.cluster_id) }}
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
const contourMode = ref('circle')
const parallelMode = ref('sampled')

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
const rawClusterSummary = computed(() => props.data?.cluster_summary || [])
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
  `${
    coordMode.value === 'business'
      ? '聚类输入坐标(薪资指数/门槛指数)'
      : `${projectionMethodText.value}坐标(仅用于分簇可视化)`
  } · ${
    contourMode.value === 'circle' ? '圆形轮廓' : '原始轮廓'
  }`
))
const axisXName = computed(() => (
  coordMode.value === 'business'
    ? '薪资指数（聚类输入）'
    : '聚类主轴1（投影）'
))
const axisYName = computed(() => (
  coordMode.value === 'business'
    ? '门槛指数（聚类输入）'
    : '聚类主轴2（投影）'
))

const parallelModeLabel = computed(() => parallelMode.value === 'centroid' ? '方案A：质心聚合' : '方案B：分层抽样')

const parallelRows = computed(() => {
  const p = parallelPayload.value || {}
  return parallelMode.value === 'centroid'
    ? (p.centroid_lines || [])
    : (p.sampled_lines || [])
})

const getBarrierValue = (p) => {
  const f = p?.features || {}
  const expRank = Number(f?.avg_experience_rank || 0)
  const eduRank = Number(f?.avg_education_rank || 0)
  if (Number.isFinite(Number(p?.cluster_inputs?.barrier_index))) {
    return Number(p.cluster_inputs.barrier_index)
  }
  return Number((expRank + eduRank).toFixed(4))
}

const clusterStatsMap = computed(() => {
  const map = new Map()
  points.value.forEach((p, i) => {
    const cid = Number(p?.cluster_id ?? 0)
    const ci = p?.cluster_inputs || {}
    const salary = Number.isFinite(Number(ci?.salary_index))
      ? Number(ci.salary_index)
      : Number(p?.features?.median_salary || 0)
    const barrier = Number.isFinite(Number(ci?.barrier_index))
      ? Number(ci.barrier_index)
      : getBarrierValue(p)
    const volatility = Number.isFinite(Number(ci?.volatility_index)) ? Number(ci.volatility_index) : 0
    const scale = Number.isFinite(Number(ci?.scale_index)) ? Number(ci.scale_index) : 0
    const entropy = Number.isFinite(Number(ci?.entropy_index)) ? Number(ci.entropy_index) : 0
    if (!map.has(cid)) {
      map.set(cid, {
        cid,
        n: 0,
        salarySum: 0,
        barrierSum: 0,
        volatilitySum: 0,
        scaleSum: 0,
        entropySum: 0
      })
    }
    const acc = map.get(cid)
    acc.n += 1
    acc.salarySum += salary
    acc.barrierSum += barrier
    acc.volatilitySum += volatility
    acc.scaleSum += scale
    acc.entropySum += entropy
  })
  map.forEach((v, cid) => {
    const n = Math.max(1, Number(v.n || 0))
    map.set(cid, {
      cid,
      n,
      salaryMean: v.salarySum / n,
      barrierMean: v.barrierSum / n,
      volatilityMean: v.volatilitySum / n,
      scaleMean: v.scaleSum / n,
      entropyMean: v.entropySum / n
    })
  })
  return map
})

const clusterSemantics = computed(() => {
  const fixed = new Map([
    [0, { label: '高薪高门槛型' }],
    [1, { label: '低薪低门槛型' }],
    [2, { label: '高薪波动型' }],
    [3, { label: '热门普及型' }],
    [4, { label: '大众稳定型' }]
  ])
  // 兜底：如果簇ID超出0-4，仍给一个默认标签
  const ids = new Set([
    ...rawClusterSummary.value.map((x) => Number(x?.cluster_id ?? 0)),
    ...points.value.map((x) => Number(x?.cluster_id ?? 0))
  ])
  ids.forEach((cid) => {
    if (!fixed.has(cid)) fixed.set(cid, { label: `扩展簇${cid}` })
  })
  return fixed
})

const clusterSummaryDisplay = computed(() =>
  (rawClusterSummary.value || [])
    .map((item) => ({
      ...item,
      cluster_id: Number(item?.cluster_id ?? 0),
      cluster_label: clusterSemantics.value.get(Number(item?.cluster_id ?? 0))?.label || `簇${Number(item?.cluster_id ?? 0)}`
    }))
    .sort((a, b) => Number(a.cluster_id) - Number(b.cluster_id))
)

const clusterDisplayText = (cid) => {
  const c = Number(cid || 0)
  const sem = clusterSemantics.value.get(c)
  return sem?.label ? `C${c} ${sem.label}` : `C${c}`
}

const clusterPalette = ['#2d7cff', '#ef4444', '#00b894', '#f59e0b', '#7b61ff', '#14b8a6', '#f97316', '#ec4899']
const clusterColor = (cid) => {
  const c = Number(cid || 0)
  return clusterPalette[Math.abs(c) % clusterPalette.length]
}
const hexToRgb = (hex) => {
  const h = String(hex || '').replace('#', '')
  if (h.length !== 6) return [45, 124, 255]
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]
}
const rgba = (hex, alpha) => {
  const [r, g, b] = hexToRgb(hex)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
const pointGradientColor = (hex, visible) => {
  const inner = visible ? 0.92 : 0.15
  const mid = visible ? 0.52 : 0.08
  const outer = visible ? 0.26 : 0.04
  return {
    type: 'radial',
    x: 0.45,
    y: 0.4,
    r: 0.85,
    colorStops: [
      { offset: 0, color: rgba(hex, inner) },
      { offset: 0.62, color: rgba(hex, mid) },
      { offset: 1, color: rgba(hex, outer) }
    ]
  }
}

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
    const ci = p?.cluster_inputs || {}
    const salaryIndex = Number.isFinite(Number(ci?.salary_index))
      ? Number(ci.salary_index)
      : Number(p?.features?.median_salary || 0)
    const barrier = Number.isFinite(Number(ci?.barrier_index))
      ? Number(ci.barrier_index)
      : getBarrierValue(p)
    return [
      salaryIndex,
      barrier
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

const quantile = (arr, q) => {
  if (!Array.isArray(arr) || !arr.length) return 0
  const sorted = [...arr].sort((a, b) => a - b)
  const pos = (sorted.length - 1) * Math.min(1, Math.max(0, q))
  const lo = Math.floor(pos)
  const hi = Math.ceil(pos)
  if (lo === hi) return sorted[lo]
  const w = pos - lo
  return sorted[lo] * (1 - w) + sorted[hi] * w
}

const displayAxisRange = (values) => {
  if (!values.length) return { min: 0, max: 1 }
  // 业务圆形模式用稳健分位数范围，避免少量离群点制造大空白
  if (coordMode.value === 'business' && contourMode.value === 'circle') {
    const q1 = quantile(values, 0.01)
    const q99 = quantile(values, 0.99)
    const span = Math.max(1e-6, q99 - q1)
    const pad = Math.max(0.12, span * 0.08)
    return { min: q1 - pad, max: q99 + pad }
  }
  // 业务原始模式也做轻度稳健缩轴，缓解“点挤在一起”
  if (coordMode.value === 'business' && contourMode.value === 'original') {
    const q1 = quantile(values, 0.005)
    const q99 = quantile(values, 0.995)
    const span = Math.max(1e-6, q99 - q1)
    const pad = Math.max(0.1, span * 0.07)
    return { min: q1 - pad, max: q99 + pad }
  }
  return axisRange(values)
}

const circularizeRows = (rows) => {
  if (!Array.isArray(rows) || rows.length < 3 || contourMode.value !== 'circle') return rows

  const vals = rows.map((r) => [Number(r.value?.[0] || 0), Number(r.value?.[1] || 0)])
  const xs = vals.map((v) => v[0])
  const ys = vals.map((v) => v[1])
  const meanX = xs.reduce((a, b) => a + b, 0) / xs.length
  const meanY = ys.reduce((a, b) => a + b, 0) / ys.length
  const stdX = Math.sqrt(xs.reduce((a, b) => a + (b - meanX) ** 2, 0) / Math.max(1, xs.length - 1)) || 1
  const stdY = Math.sqrt(ys.reduce((a, b) => a + (b - meanY) ** 2, 0) / Math.max(1, ys.length - 1)) || 1

  // PCA 模式：保持原有的全局圆形投影
  if (coordMode.value === 'pca') {
    const polar = vals.map(([x, y], i) => {
      const nx = (x - meanX) / stdX
      const ny = (y - meanY) / stdY
      const r = Math.sqrt(nx * nx + ny * ny)
      const theta = Math.atan2(ny, nx)
      return { i, r, theta }
    })

    const sorted = [...polar].sort((a, b) => a.r - b.r)
    const rankMap = new Map()
    sorted.forEach((p, idx) => rankMap.set(p.i, idx))
    const maxR = Math.max(...polar.map((p) => p.r), 1e-6)
    const targetMax = 3.0
    const blend = 0.64

    return rows.map((row, idx) => {
      const p = polar[idx]
      const rank = Number(rankMap.get(idx) || 0)
      const q = (rank + 0.5) / rows.length
      const rDisc = Math.sqrt(q) * targetMax
      const rOrig = (p.r / maxR) * targetMax
      const rNew = rOrig * (1 - blend) + rDisc * blend
      const xNew = rNew * Math.cos(p.theta)
      const yNew = rNew * Math.sin(p.theta)
      return {
        ...row,
        value: [xNew, yNew]
      }
    })
  }

  // 业务坐标：保留簇结构，同时做“更圆 + 更分散”的展示变换
  const normRows = rows.map((row) => {
    const x = Number(row.value?.[0] || 0)
    const y = Number(row.value?.[1] || 0)
    return {
      ...row,
      _nx: (x - meanX) / stdX,
      _ny: (y - meanY) / stdY
    }
  })

  const clusterMap = new Map()
  normRows.forEach((r) => {
    const cid = Number(r?.raw?.cluster_id || 0)
    if (!clusterMap.has(cid)) clusterMap.set(cid, [])
    clusterMap.get(cid).push(r)
  })

  const centers = []
  clusterMap.forEach((arr, cid) => {
    const cx = arr.reduce((s, r) => s + r._nx, 0) / arr.length
    const cy = arr.reduce((s, r) => s + r._ny, 0) / arr.length
    centers.push({ cid, cx, cy, n: arr.length, theta: Math.atan2(cy, cx), r: Math.hypot(cx, cy) })
  })
  const sortedCenter = [...centers].sort((a, b) => a.theta - b.theta)
  const k = Math.max(1, sortedCenter.length)
  const meanCenterR = sortedCenter.reduce((s, c) => s + c.r, 0) / k
  const targetRingR = Math.max(2.6, meanCenterR * 1.48)

  const targetCenterByCid = new Map()
  sortedCenter.forEach((c, idx) => {
    const a = (idx / k) * Math.PI * 2
    const tx = Math.cos(a) * targetRingR
    const ty = Math.sin(a) * targetRingR
    // 保留原簇相对关系，且让整体更接近圆
    targetCenterByCid.set(c.cid, {
      x: c.cx * 0.2 + tx * 0.8,
      y: c.cy * 0.2 + ty * 0.8
    })
  })

  const localStatsByCid = new Map()
  centers.forEach((c) => {
    const arr = clusterMap.get(c.cid) || []
    const sx = Math.sqrt(arr.reduce((s, r) => s + (r._nx - c.cx) ** 2, 0) / Math.max(1, arr.length - 1)) || 1
    const sy = Math.sqrt(arr.reduce((s, r) => s + (r._ny - c.cy) ** 2, 0) / Math.max(1, arr.length - 1)) || 1
    localStatsByCid.set(c.cid, { cx: c.cx, cy: c.cy, sx, sy })
  })

  return normRows.map((r) => {
    const cid = Number(r?.raw?.cluster_id || 0)
    const st = localStatsByCid.get(cid) || { cx: 0, cy: 0, sx: 1, sy: 1 }
    const tc = targetCenterByCid.get(cid) || { x: st.cx, y: st.cy }
    const iso = (st.sx + st.sy) / 2
    const ox = ((r._nx - st.cx) / st.sx) * iso
    const oy = ((r._ny - st.cy) / st.sy) * iso
    const spread = 0.94 + Math.min(0.12, Number(r.densityNorm || 0) * 0.16)
    return {
      ...r,
      value: [tc.x + ox * spread, tc.y + oy * spread]
    }
  })
}

const buildDuplicateAwareJitter = () => {
  const basePoints = []
  let minX = Number.POSITIVE_INFINITY
  let maxX = Number.NEGATIVE_INFINITY
  let minY = Number.POSITIVE_INFINITY
  let maxY = Number.NEGATIVE_INFINITY

  points.value.forEach((p, i) => {
    const pid = Number(p.point_id ?? i)
    const [bx, by] = baseCoordOfPoint(p)
    const x = Number(bx || 0)
    const y = Number(by || 0)
    basePoints.push({ pid, x, y, cid: Number(p.cluster_id || 0) })
    if (x < minX) minX = x
    if (x > maxX) maxX = x
    if (y < minY) minY = y
    if (y > maxY) maxY = y
  })

  const spanX = Math.max(1e-6, maxX - minX)
  const spanY = Math.max(1e-6, maxY - minY)
  const gridX = coordMode.value === 'pca' ? 56 : 96
  const gridY = coordMode.value === 'pca' ? 44 : 84
  const cellX = spanX / gridX
  const cellY = spanY / gridY
  const densityCellMap = new Map()

  basePoints.forEach((pt) => {
    const gx = Math.floor((pt.x - minX) / Math.max(1e-6, cellX))
    const gy = Math.floor((pt.y - minY) / Math.max(1e-6, cellY))
    const k = `${gx}|${gy}`
    densityCellMap.set(k, (densityCellMap.get(k) || 0) + 1)
  })

  const densityRawByPid = new Map()
  let maxDensity = 1
  basePoints.forEach((pt) => {
    const gx = Math.floor((pt.x - minX) / Math.max(1e-6, cellX))
    const gy = Math.floor((pt.y - minY) / Math.max(1e-6, cellY))
    const k = `${gx}|${gy}`
    const d = Number(densityCellMap.get(k) || 1)
    densityRawByPid.set(pt.pid, d)
    if (d > maxDensity) maxDensity = d
  })

  const buckets = new Map()
  basePoints.forEach((pt) => {
    // 以原始坐标+簇分桶，避免不同簇完全压在同一点位
    const key = [
      Number(pt.x || 0).toFixed(4),
      Number(pt.y || 0).toFixed(4),
      Number(pt.cid || 0)
    ].join('|')
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key).push(pt.pid)
  })

  const jitterByPid = new Map()
  const dupCountByPid = new Map()
  const densityNormByPid = new Map()
  const golden = Math.PI * (3 - Math.sqrt(5))

  buckets.forEach((pidList) => {
    const n = pidList.length
    const sorted = [...pidList].sort((a, b) => a - b)
    const spreadDup = coordMode.value === 'pca'
      ? Math.min(1.3, 1 + 0.08 * Math.log2(n + 1))
      : Math.min(2.9, 1 + 0.24 * Math.log2(n + 1))

    sorted.forEach((pid, idx) => {
      dupCountByPid.set(pid, n)
      const density = Number(densityRawByPid.get(pid) || 1)
      const densityNorm = (density - 1) / Math.max(1, maxDensity - 1)
      densityNormByPid.set(pid, densityNorm)
      const spreadDensity = 1 + densityNorm * (coordMode.value === 'pca' ? 0.45 : 0.58)
      const spread = spreadDup * spreadDensity
      if (n <= 1) {
        if (density <= 2) {
          jitterByPid.set(pid, [0, 0])
          return
        }
        // 非重复点但处在密集网格时，给一个轻微抖动，降低完全重叠
        const a = (Number(pid) + 1) * golden
        const r0 = coordMode.value === 'pca' ? 0.008 : 0.038
        const r = r0 * (1 + densityNorm * 1.7)
        const ratioY = coordMode.value === 'pca' ? 0.9 : 0.58
        const dx = Math.cos(a) * r
        const dy = Math.sin(a) * r * ratioY
        jitterByPid.set(pid, [dx, dy])
        return
      }
      // Sunflower 排布：重复越多，半径越大，但整体仍围绕原坐标
      const r = Math.sqrt(idx + 0.5)
      const a = idx * golden
      const base = coordMode.value === 'pca' ? 0.012 : 0.125
      const ratioY = coordMode.value === 'pca' ? 0.92 : 0.62
      const dx = Math.cos(a) * r * base * spread
      const dy = Math.sin(a) * r * base * ratioY * spread
      jitterByPid.set(pid, [dx, dy])
    })
  })

  return { jitterByPid, dupCountByPid, densityRawByPid, densityNormByPid }
}

const renderScatter = () => {
  try {
    renderError.value = ''
    if (!scatterRef.value || !points.value.length) return
    if (!scatterChart) scatterChart = echarts.init(scatterRef.value)
    const { jitterByPid, dupCountByPid, densityRawByPid, densityNormByPid } = buildDuplicateAwareJitter()
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
      const localDensity = Number(densityRawByPid.get(pid) || 1)
      const densityNorm = Number(densityNormByPid.get(pid) || 0)
      const sizeFromDemand = 1.35 + norm * 2.45
      const sizeDensityFactor = dense ? (1 - densityNorm * 0.54) : (1 - densityNorm * 0.33)
      const sized = Math.max(1.1, sizeFromDemand * sizeDensityFactor)
      const baseOpacity = dense ? 0.58 : 0.74
      const densePenalty = densityNorm * (dense ? 0.38 : 0.24)
      const visibleOpacity = Math.max(dense ? 0.08 : 0.18, baseOpacity - densePenalty)
      return {
        value: [Number(bx || 0) + jx, Number(by || 0) + jy],
        baseValue: [Number(bx || 0), Number(by || 0)],
        raw: p,
        pid,
        duplicateCount: Number(dupCountByPid.get(pid) || 1),
        localDensity,
        densityNorm,
        clusterBaseColor: clusterColor(p.cluster_id),
        itemStyle: {
          color: pointGradientColor(clusterColor(p.cluster_id), visible),
          borderColor: visible ? rgba(clusterColor(p.cluster_id), dense ? 0.4 : 0.52) : 'rgba(0,0,0,0)',
          borderWidth: visible ? 0.28 : 0,
          shadowBlur: visible ? (dense ? 1 : 2) : 0,
          shadowColor: visible ? rgba(clusterColor(p.cluster_id), dense ? 0.22 : 0.3) : 'rgba(0,0,0,0)',
          opacity: visible ? visibleOpacity : 0.05
        },
        symbolSize: visible ? sized : 1.5
      }
    })
    const plotRows = circularizeRows(rows)
    const xRange = displayAxisRange(plotRows.map((r) => Number(r.value?.[0] || 0)))
    const yRange = displayAxisRange(plotRows.map((r) => Number(r.value?.[1] || 0)))

    const centerMap = new Map()
    plotRows.forEach((row) => {
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
          `簇：${clusterDisplayText(d.cluster_id)}`,
          `行业：${d.company_type || '未知'}`,
          `城市等级：${d.city_tier || '未知'}`,
          `中位薪资：${formatSalary(f.median_salary)}`,
          `经验/学历：${Number(f.avg_experience_rank || 0).toFixed(2)} / ${Number(f.avg_education_rank || 0).toFixed(2)}`,
          `同位重叠点：${Number(params?.data?.duplicateCount || 1)}`,
          `局部密度：${Number(params?.data?.localDensity || 1)}`
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
        blendMode: 'source-over',
        emphasis: {
          scale: 1.45,
          itemStyle: {
            borderColor: '#0f172a',
            borderWidth: 1.4,
            shadowBlur: 14,
            shadowColor: 'rgba(15, 23, 42, 0.28)'
          }
        },
        data: plotRows
      },
      {
        type: 'scatter',
        symbol: 'diamond',
        data: centerData,
        symbolSize: 12,
        itemStyle: {
          color: 'rgba(255,255,255,0.95)',
          borderColor: '#111827',
          borderWidth: 1.1,
          shadowBlur: 10,
          shadowColor: 'rgba(17, 24, 39, 0.25)',
          opacity: 0.95
        },
        label: {
          show: true,
          position: 'top',
          formatter: (p) => clusterDisplayText(Number(p?.data?.cid || 0)),
          color: '#0f172a',
          fontSize: 11,
          fontWeight: 700
        },
        z: 8,
        tooltip: {
          formatter: (p) => `簇中心：${clusterDisplayText(Number(p?.data?.cid || 0))}`
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
        .map((idx) => plotRows[idx]?.pid)
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
          `簇：${clusterDisplayText(d.cluster_id)}`,
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
  parallelMode.value = 'sampled'

  scatterSelectedIds.value = []
  parallelFilteredPointIds.value = []
  selectedPoint.value = null

  // 默认展示全部类，不自动聚焦单个簇
  activeClusterId.value = null

  await nextTick()
  renderScatter()
  renderParallel()
}, { deep: true, immediate: true })

watch([parallelMode, activeClusterId, coordMode, contourMode], () => {
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
