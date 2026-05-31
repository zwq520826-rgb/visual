<template>
  <div class="region-cluster-wrap">
    <div class="chart-pane">
      <div class="pane-head">
        <h3>视图 A：地域招聘画像散点图</h3>
        <p>{{ chartDesc }}</p>
        <p class="count-meta">显示 {{ renderedPointCount }} / {{ regions.length }} 个城市点</p>
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
          <label class="switch-label">
            <input v-model="expandDense" type="checkbox" />
            <span>密集区展开</span>
          </label>
          <label class="switch-label">
            <input v-model="showSimilarLinks" type="checkbox" />
            <span>显示相似连线</span>
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
const showSimilarLinks = ref(true)
const expandDense = ref(true)

const axisOptions = [
  { value: 'job_count', label: '岗位数量' },
  { value: 'pca_x', label: '主成分1 (PCA1)' },
  { value: 'pca_y', label: '主成分2 (PCA2)' },
  { value: 'structure_index', label: '结构指数(行业熵+职位熵)' },
  { value: 'industry_entropy', label: '行业多样性(熵)' },
  { value: 'position_entropy', label: '职位多样性(熵)' },
  { value: 'top_industry_share', label: '头部行业占比' },
  { value: 'top_position_share', label: '头部职位占比' },
  { value: 'barrier_index', label: '门槛指数(学历+经验)' },
  { value: 'high_salary_share', label: '高薪岗位占比' },
  { value: 'salary_median', label: '中位薪资' },
  { value: 'salary_mean', label: '平均薪资' }
]

const axisX = ref('job_count')
const axisY = ref('salary_mean')

const axisLabelMap = computed(() => {
  const m = {}
  axisOptions.forEach((o) => { m[o.value] = o.label })
  return m
})

const quantile = (arr, q) => {
  if (!arr.length) return 0
  if (arr.length === 1) return arr[0]
  const p = Math.max(0, Math.min(1, q))
  const idx = (arr.length - 1) * p
  const lo = Math.floor(idx)
  const hi = Math.ceil(idx)
  if (lo === hi) return arr[lo]
  const t = idx - lo
  return arr[lo] * (1 - t) + arr[hi] * t
}

const calcDisplayCap = (key) => {
  // 仅对长尾最明显的岗位数量做展示截断，避免“中间空白、两端拥挤”
  if (!expandDense.value || key !== 'job_count') return null
  const vals = props.regions
    .map((r) => Number(r?.[key] ?? 0))
    .filter((v) => Number.isFinite(v) && v >= 0)
    .sort((a, b) => a - b)
  if (vals.length < 20) return null
  const p50 = quantile(vals, 0.5)
  const p97 = quantile(vals, 0.97)
  const p99 = quantile(vals, 0.99)
  const vmax = vals[vals.length - 1]
  // 只有当长尾足够明显时才启用
  if (vmax < p97 * 1.6 || p99 < p50 * 2.2) return null
  return Math.max(p97, p50 + 1)
}

const axisDisplayCaps = computed(() => ({
  [axisX.value]: calcDisplayCap(axisX.value),
  [axisY.value]: calcDisplayCap(axisY.value)
}))

const chartDesc = computed(() => {
  const suffix = expandDense.value ? '（开启密集区展开）' : ''
  const xCap = axisDisplayCaps.value[axisX.value]
  const yCap = axisDisplayCaps.value[axisY.value]
  const capHint = (xCap != null || yCap != null) ? '；极端值已做P97截断展示' : ''
  const xLogHint = axisX.value === 'job_count' ? '；X轴为对数轴' : ''
  return `横轴 ${axisLabelMap.value[axisX.value]}，纵轴 ${axisLabelMap.value[axisY.value]}${suffix}；每个散点是一个城市地域，点大小表示招聘数量，颜色表示城市等级（冷暖色调，已做防重叠）${capHint}${xLogHint}。`
})

const hashUnit = (text, salt = 0) => {
  const s = `${text || ''}_${salt}`
  let h = 0
  for (let i = 0; i < s.length; i += 1) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0
  }
  return Math.abs(h % 100000) / 100000
}

const normalizeTier = (tier) => {
  const t = String(tier || '').trim()
  if (t === '一线' || t === 'first_tier') return '一线'
  if (t === '新一线' || t === 'new_first_tier') return '二线'
  if (t === '二线' || t === 'second_tier') return '二线'
  if (t === '三线' || t === 'third_tier') return '三线'
  return '其他'
}

const cityTierOrder = ['其他', '三线', '二线', '一线']
const cityTierColorMap = {
  其他: '#4f8fd7',
  三线: '#2b6cb0',
  二线: '#f2b35e',
  一线: '#e65a5a'
}
const cityTierToIndex = (tier) => {
  const idx = cityTierOrder.indexOf(normalizeTier(tier))
  return idx >= 0 ? idx : 0
}

const rawValueOf = (r, key) => {
  return Number(r?.[key] ?? 0)
}

const displayValueOf = (r, key) => {
  const raw = rawValueOf(r, key)
  const cap = axisDisplayCaps.value[key]
  if (cap == null) {
    if (key === 'job_count') return Math.max(1, raw)
    return raw
  }
  if (!Number.isFinite(raw)) return 0
  const clipped = Math.min(raw, cap)
  if (key === 'job_count') return Math.max(1, clipped)
  return clipped
}

const axisStats = computed(() => {
  const xs = props.regions.map((r) => displayValueOf(r, axisX.value)).filter((v) => Number.isFinite(v))
  const ys = props.regions.map((r) => displayValueOf(r, axisY.value)).filter((v) => Number.isFinite(v))
  const xMin = xs.length ? Math.min(...xs) : -1
  const xMax = xs.length ? Math.max(...xs) : 1
  const yMin = ys.length ? Math.min(...ys) : -1
  const yMax = ys.length ? Math.max(...ys) : 1
  const dx = Math.max(1e-9, xMax - xMin)
  const dy = Math.max(1e-9, yMax - yMin)
  return { xMin, xMax, yMin, yMax, dx, dy }
})

const coordMap = computed(() => {
  const points = []
  const map = new Map()
  const { xMin, yMin, dx, dy } = axisStats.value
  const isLogX = axisX.value === 'job_count'
  const xMinSafe = isLogX ? Math.max(1e-6, xMin) : xMin
  const xMaxSafe = isLogX ? Math.max(xMinSafe * 1.000001, xMin + dx) : (xMin + dx)
  const lxMin = isLogX ? Math.log10(xMinSafe) : 0
  const lxMax = isLogX ? Math.log10(xMaxSafe) : 1
  const ldx = isLogX ? Math.max(1e-9, lxMax - lxMin) : 1
  const chartW = Math.max(480, Number(chartRef.value?.clientWidth || 980))
  const chartH = Math.max(360, Number(chartRef.value?.clientHeight || 460))
  const plotW = Math.max(240, chartW - 70 - 16)
  const plotH = Math.max(180, chartH - 56 - 56)

  const toPxX = (x) => {
    if (isLogX) {
      const xx = Math.max(1e-6, Number(x || 0))
      return ((Math.log10(xx) - lxMin) / ldx) * plotW
    }
    return ((x - xMin) / dx) * plotW
  }
  const toPxY = (y) => ((y - yMin) / dy) * plotH
  const toDataX = (px) => {
    if (isLogX) {
      const lv = lxMin + (px / plotW) * ldx
      return Math.pow(10, lv)
    }
    return xMin + (px / plotW) * dx
  }
  const toDataY = (py) => yMin + (py / plotH) * dy

  const clampPoint = (p) => {
    if (!p) return
    p.x = Math.max(p.r, Math.min(plotW - p.r, p.x))
    p.y = Math.max(p.r, Math.min(plotH - p.r, p.y))
  }

  props.regions.forEach((r) => {
    const xRaw = rawValueOf(r, axisX.value)
    const yRaw = rawValueOf(r, axisY.value)
    const xDisp = displayValueOf(r, axisX.value)
    const yDisp = displayValueOf(r, axisY.value)
    const baseR = symbolSize(Number(r.job_count || 0)) * 0.5 + 0.8
    const jitA = hashUnit(r.region_id, 131) * Math.PI * 2
    const jitM = 1.6 + hashUnit(r.region_id, 137) * 2.6
    const jitR = baseR * jitM
    const p = {
      region_id: r.region_id,
      xRaw,
      yRaw,
      x0: xDisp,
      y0: yDisp,
      x: toPxX(xDisp) + Math.cos(jitA) * jitR,
      y: toPxY(yDisp) + Math.sin(jitA) * jitR,
      r: baseR
    }
    points.push(p)
  })

  // 碰撞分离：在像素空间做迭代，避免圆点相互覆盖
  const n = points.length
  const order = [...Array(n).keys()].sort((i, j) => {
    const hi = hashUnit(points[i]?.region_id, 617)
    const hj = hashUnit(points[j]?.region_id, 617)
    return hi - hj
  })
  const iters = n > 500 ? 120 : 150
  for (let t = 0; t < iters; t += 1) {
    for (let oi = 0; oi < n; oi += 1) {
      const i = order[oi]
      const a = points[i]
      for (let oj = oi + 1; oj < n; oj += 1) {
        const j = order[oj]
        const b = points[j]
        let dxp = b.x - a.x
        let dyp = b.y - a.y
        let dist = Math.hypot(dxp, dyp)
        const minDist = (a.r + b.r) * 1.32
        if (dist >= minDist) continue
        if (dist < 1e-6) {
          const ang = (hashUnit(`${a.region_id}_${b.region_id}`, 97) * Math.PI * 2)
          dxp = Math.cos(ang) * 1e-3
          dyp = Math.sin(ang) * 1e-3
          dist = Math.hypot(dxp, dyp)
        }
        const overlap = (minDist - dist) * 0.6
        const ux = dxp / dist
        const uy = dyp / dist
        const tx = -uy
        const ty = ux
        const swirl = (hashUnit(`${a.region_id}_${b.region_id}`, 509) - 0.5) * overlap * 0.28
        a.x -= ux * overlap
        a.y -= uy * overlap
        b.x += ux * overlap
        b.y += uy * overlap
        a.x += tx * swirl
        a.y += ty * swirl
        b.x -= tx * swirl
        b.y -= ty * swirl
      }
    }
    // 软回拉：尽量贴近原坐标语义，防止图形失真
    for (let i = 0; i < n; i += 1) {
      const p = points[i]
      const x0 = toPxX(p.x0)
      const y0 = toPxY(p.y0)
      p.x += (x0 - p.x) * 0.01
      p.y += (y0 - p.y) * 0.01
      clampPoint(p)
    }
  }

  // 最终硬性无重叠校正：确保散点不互相覆盖
  for (let pass = 0; pass < 120; pass += 1) {
    let moved = false
    for (let i = 0; i < n; i += 1) {
      const a = points[i]
      for (let j = i + 1; j < n; j += 1) {
        const b = points[j]
        let dxp = b.x - a.x
        let dyp = b.y - a.y
        let dist = Math.hypot(dxp, dyp)
        const minDist = (a.r + b.r) * 1.24
        if (dist >= minDist) continue
        moved = true
        if (dist < 1e-6) {
          const ang = (hashUnit(`${a.region_id}_${b.region_id}`, 211) * Math.PI * 2)
          dxp = Math.cos(ang) * 1e-3
          dyp = Math.sin(ang) * 1e-3
          dist = Math.hypot(dxp, dyp)
        }
        const overlap = (minDist - dist) * 0.5
        const ux = dxp / dist
        const uy = dyp / dist
        a.x -= ux * overlap
        a.y -= uy * overlap
        b.x += ux * overlap
        b.y += uy * overlap
      }
      clampPoint(a)
    }
    if (!moved) break
  }

  // 收敛后再做一次严格检查，若仍有重叠则继续小步排斥直到清零
  for (let pass = 0; pass < 160; pass += 1) {
    let overlaps = 0
    for (let i = 0; i < n; i += 1) {
      const a = points[i]
      for (let j = i + 1; j < n; j += 1) {
        const b = points[j]
        let dxp = b.x - a.x
        let dyp = b.y - a.y
        let dist = Math.hypot(dxp, dyp)
        const minDist = (a.r + b.r) * 1.2
        if (dist >= minDist) continue
        overlaps += 1
        if (dist < 1e-6) {
          const ang = (hashUnit(`${a.region_id}_${b.region_id}`, 307) * Math.PI * 2)
          dxp = Math.cos(ang) * 1e-3
          dyp = Math.sin(ang) * 1e-3
          dist = Math.hypot(dxp, dyp)
        }
        const need = (minDist - dist) * 0.52
        const ux = dxp / dist
        const uy = dyp / dist
        a.x -= ux * need
        a.y -= uy * need
        b.x += ux * need
        b.y += uy * need
        clampPoint(a)
        clampPoint(b)
      }
    }
    if (overlaps === 0) break
  }

  // 有约束随机微扰：打散“蜂窝感”，每一步都做碰撞检查
  const canPlace = (idx, nx, ny, factor = 1.18) => {
    const a = points[idx]
    for (let j = 0; j < n; j += 1) {
      if (j === idx) continue
      const b = points[j]
      const d = Math.hypot(nx - b.x, ny - b.y)
      if (d < (a.r + b.r) * factor) return false
    }
    return true
  }
  for (let oi = 0; oi < n; oi += 1) {
    const i = order[oi]
    const p = points[i]
    const a1 = hashUnit(p.region_id, 721) * Math.PI * 2
    const a2 = hashUnit(p.region_id, 727) * Math.PI * 2
    const amp = p.r * (0.18 + hashUnit(p.region_id, 733) * 0.52)
    const tries = [1, -1, 0.65, -0.65, 0.35, -0.35]
    for (let k = 0; k < tries.length; k += 1) {
      const t = tries[k]
      const nx = Math.max(
        p.r,
        Math.min(
          plotW - p.r,
          p.x + Math.cos(a1) * amp * t + Math.cos(a2) * amp * 0.34 * t
        )
      )
      const ny = Math.max(
        p.r,
        Math.min(
          plotH - p.r,
          p.y + Math.sin(a1) * amp * t + Math.sin(a2) * amp * 0.34 * t
        )
      )
      if (canPlace(i, nx, ny, 1.16)) {
        p.x = nx
        p.y = ny
        break
      }
    }
  }

  // 微扰后再做一次硬性无重叠收敛
  for (let pass = 0; pass < 90; pass += 1) {
    let overlaps = 0
    for (let i = 0; i < n; i += 1) {
      const a = points[i]
      for (let j = i + 1; j < n; j += 1) {
        const b = points[j]
        let dxp = b.x - a.x
        let dyp = b.y - a.y
        let dist = Math.hypot(dxp, dyp)
        const minDist = (a.r + b.r) * 1.18
        if (dist >= minDist) continue
        overlaps += 1
        if (dist < 1e-6) {
          const ang = (hashUnit(`${a.region_id}_${b.region_id}`, 739) * Math.PI * 2)
          dxp = Math.cos(ang) * 1e-3
          dyp = Math.sin(ang) * 1e-3
          dist = Math.hypot(dxp, dyp)
        }
        const push = (minDist - dist) * 0.55
        const ux = dxp / dist
        const uy = dyp / dist
        a.x -= ux * push
        a.y -= uy * push
        b.x += ux * push
        b.y += uy * push
        clampPoint(a)
        clampPoint(b)
      }
    }
    if (overlaps === 0) break
  }

  // 去规则化：在“无重叠”约束下做轻微错位，打散一排一排的视觉规律
  const canPlaceNoOverlap = (idx, nx, ny, factor = 1.03) => {
    const a = points[idx]
    for (let j = 0; j < n; j += 1) {
      if (j === idx) continue
      const b = points[j]
      const d = Math.hypot(nx - b.x, ny - b.y)
      if (d < (a.r + b.r) * factor) return false
    }
    return true
  }
  for (let pass = 0; pass < 3; pass += 1) {
    for (let oi = 0; oi < n; oi += 1) {
      const i = order[(oi + pass * 17) % n]
      const p = points[i]
      const ax = hashUnit(p.region_id, 811 + pass * 13) * Math.PI * 2
      const ay = hashUnit(p.region_id, 823 + pass * 17) * Math.PI * 2
      const sx = p.r * (0.18 + hashUnit(p.region_id, 829 + pass * 19) * 0.36)
      const sy = p.r * (0.34 + hashUnit(p.region_id, 839 + pass * 23) * 0.58)
      const cands = [
        [Math.cos(ax) * sx, Math.sin(ay) * sy],
        [Math.cos(ax + 1.7) * sx * 0.82, Math.sin(ay + 2.1) * sy * 0.92],
        [Math.cos(ax + 3.4) * sx * 0.65, Math.sin(ay + 4.0) * sy * 0.78]
      ]
      for (let k = 0; k < cands.length; k += 1) {
        const [dxj, dyj] = cands[k]
        const nx = Math.max(p.r, Math.min(plotW - p.r, p.x + dxj))
        const ny = Math.max(p.r, Math.min(plotH - p.r, p.y + dyj))
        if (canPlaceNoOverlap(i, nx, ny, 1.02)) {
          p.x = nx
          p.y = ny
          break
        }
      }
    }
  }

  // 去规则化后终轮收敛，保证严格不重叠
  for (let pass = 0; pass < 80; pass += 1) {
    let overlaps = 0
    for (let i = 0; i < n; i += 1) {
      const a = points[i]
      for (let j = i + 1; j < n; j += 1) {
        const b = points[j]
        let dxp = b.x - a.x
        let dyp = b.y - a.y
        let dist = Math.hypot(dxp, dyp)
        const minDist = (a.r + b.r) * 1.14
        if (dist >= minDist) continue
        overlaps += 1
        if (dist < 1e-6) {
          const ang = (hashUnit(`${a.region_id}_${b.region_id}`, 857) * Math.PI * 2)
          dxp = Math.cos(ang) * 1e-3
          dyp = Math.sin(ang) * 1e-3
          dist = Math.hypot(dxp, dyp)
        }
        const push = (minDist - dist) * 0.55
        const ux = dxp / dist
        const uy = dyp / dist
        a.x -= ux * push
        a.y -= uy * push
        b.x += ux * push
        b.y += uy * push
        clampPoint(a)
        clampPoint(b)
      }
    }
    if (overlaps === 0) break
  }

  // 保底策略：若空间仍过密，整体轻微缩径后再做终轮分离，确保无重叠
  const countOverlaps = () => {
    let k = 0
    for (let i = 0; i < n; i += 1) {
      const a = points[i]
      for (let j = i + 1; j < n; j += 1) {
        const b = points[j]
        const dist = Math.hypot(b.x - a.x, b.y - a.y)
        if (dist < (a.r + b.r) * 1.12) k += 1
      }
    }
    return k
  }

  if (countOverlaps() > 0) {
    for (let i = 0; i < n; i += 1) {
      points[i].r = Math.max(2.2, points[i].r * 0.9)
      clampPoint(points[i])
    }
    for (let pass = 0; pass < 100; pass += 1) {
      let overlaps = 0
      for (let i = 0; i < n; i += 1) {
        const a = points[i]
        for (let j = i + 1; j < n; j += 1) {
          const b = points[j]
          let dxp = b.x - a.x
          let dyp = b.y - a.y
          let dist = Math.hypot(dxp, dyp)
          const minDist = (a.r + b.r) * 1.14
          if (dist >= minDist) continue
          overlaps += 1
          if (dist < 1e-6) {
            const ang = (hashUnit(`${a.region_id}_${b.region_id}`, 401) * Math.PI * 2)
            dxp = Math.cos(ang) * 1e-3
            dyp = Math.sin(ang) * 1e-3
            dist = Math.hypot(dxp, dyp)
          }
          const push = (minDist - dist) * 0.54
          const ux = dxp / dist
          const uy = dyp / dist
          a.x -= ux * push
          a.y -= uy * push
          b.x += ux * push
          b.y += uy * push
          clampPoint(a)
          clampPoint(b)
        }
      }
      if (overlaps === 0) break
    }
  }

  points.forEach((p) => {
    map.set(p.region_id, {
      x: toDataX(p.x),
      y: toDataY(p.y),
      xRaw: p.xRaw,
      yRaw: p.yRaw
    })
  })

  return map
})

const extent = computed(() => {
  const vals = [...coordMap.value.values()]
  if (!vals.length) return { minX: -1, maxX: 1, minY: -1, maxY: 1 }
  const xs = vals.map((v) => v.x)
  const ys = vals.map((v) => v.y)
  const minXRaw = Math.min(...xs)
  const maxXRaw = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const dx = Math.max(1e-9, maxXRaw - minXRaw)
  const dy = Math.max(1e-9, maxY - minY)

  let minX = minXRaw - dx * 0.08
  let maxX = maxXRaw + dx * 0.08
  // X轴为对数轴时，必须保持 min/max > 0，且用乘法留白避免回落到 1~10 默认域
  if (axisX.value === 'job_count') {
    const pos = xs.filter((v) => Number.isFinite(v) && v > 0)
    const pMin = pos.length ? Math.min(...pos) : 1
    const pMax = pos.length ? Math.max(...pos) : 10
    minX = Math.max(1e-6, pMin / 1.12)
    maxX = Math.max(minX * 1.5, pMax * 1.08)
  }

  return {
    minX,
    maxX,
    minY: minY - dy * 0.08,
    maxY: maxY + dy * 0.08
  }
})

const sizeStats = computed(() => {
  const counts = props.regions
    .map((r) => Number(r.job_count || 0))
    .filter((n) => Number.isFinite(n) && n >= 0)
    .sort((a, b) => a - b)
  if (!counts.length) return { max: 1 }
  return {
    max: counts[counts.length - 1]
  }
})

const symbolSize = (count) => {
  const c = Math.max(0, Number(count || 0))
  const maxCount = Math.max(10001, Number(sizeStats.value.max || 10001))
  if (c <= 0) return 4

  // 0 ~ 300：小气泡（4 ~ 12）
  if (c <= 300) {
    const t = Math.sqrt(c / 300)
    return 4 + t * 8
  }

  // 300 ~ 500：平滑过渡（12 ~ 15）
  if (c < 500) {
    const t = (c - 300) / 200
    return 12 + t * 3
  }

  // 500 ~ 10000：中气泡（15 ~ 20）
  if (c <= 10000) {
    const t = Math.sqrt((c - 500) / 9500)
    return 15 + t * 5
  }

  // >10000：大气泡（25 ~ 36，明显放大）
  const t = Math.sqrt(Math.min(1, (c - 10000) / Math.max(1, maxCount - 10000)))
  return 25 + t * 11
}

const visibleRegions = computed(() => props.regions)

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
const renderedPointCount = computed(() => visibleRegions.value.length)

const buildSeries = () => {
  const series = []
  series.push({
    name: '地域散点',
    type: 'scatter',
    data: visibleRegions.value.map((r) => {
      const p = coordMap.value.get(r.region_id) || { x: 0, y: 0, xRaw: 0, yRaw: 0 }
      const cid = Number(r.cluster_id)
      const tierNorm = normalizeTier(r.city_tier)
      const colorVal = Number(r.industry_count ?? (Array.isArray(r.industry_top) ? r.industry_top.length : 0))
      return {
        value: [p.x, p.y, Number(r.job_count || 0), colorVal, cityTierToIndex(tierNorm)],
        region_id: r.region_id,
        region_label: r.region_label,
        city_tier: tierNorm,
        cluster_id: cid,
        salary_mean: r.salary_mean,
        salary_median: r.salary_median,
        xRaw: p.xRaw,
        yRaw: p.yRaw,
        colorVal,
        industry_top: r.industry_top || []
      }
    }),
    symbolSize: (_v, params) => symbolSize(params?.data?.value?.[2]),
    itemStyle: {
      opacity: 0.62
    },
    emphasis: {
      scale: 1.16,
      itemStyle: { opacity: 0.95 }
    },
    z: 3
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

  if (showSimilarLinks.value && lineData.length) {
    series.push({
      name: 'similar-links',
      type: 'lines',
      legendHoverLink: false,
      coordinateSystem: 'cartesian2d',
      data: lineData,
      z: 9,
      lineStyle: {
        width: 1.1,
        opacity: 0.5,
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
    legend: { show: false },
    visualMap: {
      type: 'piecewise',
      dimension: 4,
      seriesIndex: 0,
      calculable: false,
      orient: 'vertical',
      right: 8,
      top: 80,
      textStyle: { color: '#4f6f9f', fontSize: 11 },
      pieces: [
        { value: 0, label: '其他', color: cityTierColorMap['其他'] },
        { value: 1, label: '三线', color: cityTierColorMap['三线'] },
        { value: 2, label: '二线', color: cityTierColorMap['二线'] },
        { value: 3, label: '一线', color: cityTierColorMap['一线'] }
      ]
    },
    xAxis: {
      type: axisX.value === 'job_count' ? 'log' : 'value',
      logBase: axisX.value === 'job_count' ? 10 : undefined,
      min: axisX.value === 'job_count' ? Math.max(1e-6, extent.value.minX) : extent.value.minX,
      max: axisX.value === 'job_count' ? Math.max(1, extent.value.maxX) : extent.value.maxX,
      name: axisLabelMap.value[axisX.value],
      nameLocation: 'middle',
      nameGap: 32,
      axisLine: { lineStyle: { color: '#9cb4d8' } },
      splitLine: { lineStyle: { color: '#ecf1fb' } },
      axisLabel: { color: '#6a86af' }
    },
    yAxis: {
      type: 'value',
      scale: true,
      min: extent.value.minY,
      max: extent.value.maxY,
      name: axisLabelMap.value[axisY.value],
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
        const xCap = axisDisplayCaps.value[axisX.value]
        const yCap = axisDisplayCaps.value[axisY.value]
        const capNotes = []
        if (xCap != null && Number(d.xRaw || 0) > xCap) capNotes.push(`X轴超过P97截断阈值(${Number(xCap).toLocaleString()})`)
        if (yCap != null && Number(d.yRaw || 0) > yCap) capNotes.push(`Y轴超过P97截断阈值(${Number(yCap).toLocaleString()})`)
        return [
          `<strong>${d.region_label || ''} ${d.region_id || ''}</strong>`,
          `城市等级：${d.city_tier || '-'}`,
          `簇：C${d.cluster_id ?? '-'} ${summaryLabelMap.value[Number(d.cluster_id)] || ''}`,
          `岗位数量：${Number(d.value?.[2] || 0).toLocaleString()}`,
          `行业数量：${Number(d.colorVal || 0).toLocaleString()}`,
          `${axisLabelMap.value[axisX.value]}：${Number(d.xRaw || 0).toFixed(4)}`,
          `${axisLabelMap.value[axisY.value]}：${Number(d.yRaw || 0).toFixed(4)}`,
          `平均薪资：${Number(d.salary_mean || 0).toFixed(2)}`,
          `主导行业：${inds}`,
          ...(capNotes.length ? [`<span style="color:#b06a3c;">${capNotes.join('；')}</span>`] : [])
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
  () => [props.regions, props.selectedRegionId, props.focusCityId, props.heatmapSimilarRegions, showSimilarLinks.value, axisX.value, axisY.value, expandDense.value],
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

.count-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #4e6f9d;
  font-weight: 600;
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

.switch-label {
  gap: 4px;
}

.switch-label input {
  accent-color: #2f6ed8;
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
