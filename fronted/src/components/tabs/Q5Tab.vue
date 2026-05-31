<template>
  <section class="q5-tab">
    <header class="q5-hero">
      <div>
        <h2>Q5 行业引力网络</h2>
        <p>仅保留引力图视图：展示新兴岗位与行业节点的关联结构。</p>
      </div>
    </header>

    <div class="q5-workspace">
      <div class="chart-section chart-full">
        <h3>引力网络图：行业破壁与核心枢纽</h3>

        <div v-if="forceJobsError" class="error-message">
          <p>加载失败: {{ forceJobsError }}</p>
        </div>
        <div v-if="forceAtlasError" class="error-message">
          <p>网络图加载失败: {{ forceAtlasError }}</p>
        </div>
        <div v-if="rankingError" class="error-message">
          <p>对比岗位来源加载失败: {{ rankingError }}</p>
        </div>
        <div v-if="contrastSourceError" class="error-message">
          <p>对比岗位兜底来源加载失败: {{ contrastSourceError }}</p>
        </div>

        <div class="force-top-console">
          <button
            v-for="(job, idx) in forceJobs"
            :key="job.job_title"
            class="force-job-card"
            :class="{ active: job.job_title === activeForceJobTitle }"
            @click="selectForceJob(job.job_title)"
          >
            <div class="force-job-icon">{{ idx + 1 }}</div>
            <div class="force-job-title">{{ job.job_title }}</div>
            <div class="force-job-metrics">
              <span>需求量</span>
              <b>{{ formatNum(job.records_count) }} 岗</b>
            </div>
            <div class="force-job-metrics">
              <span>学历门槛</span>
              <b>{{ job.education_label || '-' }}</b>
            </div>
            <div class="force-job-metrics">
              <span>经验门槛</span>
              <b>{{ job.experience_label || '-' }}</b>
            </div>
          </button>

          <div v-if="forceJobsLoading" class="force-card-loading">正在加载前5新兴职业...</div>
        </div>

        <div class="force-controls">
          <label>城市等级：</label>
          <select v-model="forceTier">
            <option value="all">全部</option>
            <option value="first_tier">一线</option>
            <option value="second_tier">二线</option>
            <option value="third_tier">三线</option>
            <option value="other">其他</option>
          </select>

          <label>行业节点上限：</label>
          <input v-model.number="forceTopKIndustry" type="range" min="10" max="15" step="1" />
          <span>{{ forceTopKIndustry }}</span>

          <label class="switch-inline">
            <input v-model="hideOtherForceGraphs" type="checkbox" />
            <span>显示其他引力图：{{ hideOtherForceGraphs ? '关闭' : '开启' }}</span>
          </label>
          <span class="mode-hint">
            {{ hideOtherForceGraphs ? '对比模式：仅显示当前新兴岗位 + 对比岗位' : '全景模式：显示全部新兴岗位引力图' }}
          </span>
        </div>

        <div v-if="hideOtherForceGraphs" class="contrast-panel">
          <h4>对比岗位（非新兴）</h4>
          <div class="contrast-list">
            <button
              v-for="job in contrastJobs"
              :key="`contrast-${job.job_title}`"
              class="contrast-chip"
              :class="{ active: job.job_title === selectedContrastJobTitle }"
              @click="selectContrastJob(job.job_title)"
            >
              <span class="title">{{ job.job_title }}</span>
              <span class="meta">{{ formatNum(job.records_count) }} 岗</span>
              <span class="tag">{{ job.contrast_tag || '对比岗位' }}</span>
            </button>
          </div>
          <div v-if="rankingLoading || contrastSourceLoading" class="force-card-loading">正在加载对比岗位...</div>
        </div>

        <div class="force-summary-panel" v-if="activeForceNetwork?.summary">
          <div class="force-kpi"><span>核心岗位</span><b>{{ activeForceJob?.job_title || activeForceNetwork.job_title }}</b></div>
          <div class="force-kpi"><span>岗位需求量</span><b>{{ formatNum(activeForceNetwork.summary.job_total_count) }}</b></div>
          <div class="force-kpi"><span>行业覆盖度</span><b>{{ activeForceNetwork.summary.industry_degree }}</b></div>
          <div class="force-kpi"><span>核心/星尘</span><b>{{ activeForceNetwork.summary.industry_degree_core }}/{{ activeForceNetwork.summary.industry_degree_dust }}</b></div>
          <div class="force-kpi"><span>破壁熵</span><b>{{ formatFloat(activeForceNetwork.summary.industry_entropy, 3) }}</b></div>
          <div class="force-kpi"><span>枢纽分</span><b>{{ formatFloat(activeForceNetwork.summary.hub_score, 3) }}</b></div>
        </div>

        <div class="force-map-wrapper">
          <div v-if="forceAtlasLoading" class="force-map-loading">正在加载引力图...</div>
          <Q5ForceAtlasGraph
            v-else
            :networks="displayedForceNetworks"
            :activeJobTitle="activeForceJobTitle"
            :loading="false"
            :error="forceAtlasError"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useFetchData } from '@/utils/fetchData.js'
import { getQ5ForceEmergingJobs, getQ5ForceJobNetwork, getJobRanking, getQ5ForceContrastJobs } from '@/api/industryApi.js'
import Q5ForceAtlasGraph from '@/components/charts/Q5ForceAtlasGraph.vue'

const { data: forceJobsData, loading: forceJobsLoading, error: forceJobsError, execute: executeForceJobs } = useFetchData(getQ5ForceEmergingJobs)
const { data: rankingData, loading: rankingLoading, error: rankingError, execute: executeRanking } = useFetchData(getJobRanking)
const { data: contrastSourceData, loading: contrastSourceLoading, error: contrastSourceError, execute: executeContrastSource } = useFetchData(getQ5ForceContrastJobs)

const forceTier = ref('all')
const forceTopKIndustry = ref(12)
const activeForceJobTitle = ref('')
const hideOtherForceGraphs = ref(false)
const selectedContrastJobTitle = ref('')
const forceAtlasLoading = ref(false)
const forceAtlasError = ref('')
const forceNetworkByJob = ref({})
const contrastNetworkByJob = ref({})

const forceJobs = computed(() => forceJobsData.value?.data?.jobs || [])
const activeForceJob = computed(() => forceJobs.value.find(j => j.job_title === activeForceJobTitle.value) || null)

const contrastJobs = computed(() => {
  const emergingTitles = new Set(forceJobs.value.map(j => j.job_title))
  const fallbackJobs = () => {
    const fallbackRaw = Array.isArray(contrastSourceData.value?.data?.jobs) ? contrastSourceData.value.data.jobs : []
    return fallbackRaw
      .filter((j) => j?.job_title && !emergingTitles.has(j.job_title))
      .map((j) => ({
        job_title: j.job_title,
        records_count: Number(j.records_count || 0),
        contrast_tag: j.contrast_tag || '常规对比型'
      }))
      .slice(0, 6)
  }

  const all = Array.isArray(rankingData.value?.data?.jobs) ? rankingData.value.data.jobs : []
  if (!all.length) return fallbackJobs()

  const candidates = all
    .filter((j) => j?.job_title && !emergingTitles.has(j.job_title))
    .map((j) => ({
      job_title: j.job_title,
      // ranking 接口当前提供的是归一化规模字段，这里还原为可比较的“伪规模”
      records_count: Number(j.records_count || j.job_count || 0),
      records_count_norm: Number(j.records_count_norm || 0),
      approx_count: Number(j.records_count || j.job_count || 0) > 0
        ? Number(j.records_count || j.job_count || 0)
        : Math.round(Number(j.records_count_norm || 0) * 10000),
      avg_education_rank: Number(j.avg_education_rank || j.education_rank || 0),
      avg_experience_rank: Number(j.avg_experience_rank || j.experience_rank || 0),
      composite_score: Number(j.composite_score || 0)
    }))
    .filter((j) => (j.approx_count > 0 || j.records_count_norm > 0))

  if (!candidates.length) return fallbackJobs()

  // 前端轻量多样性挑选：规模/门槛/综合分差异拉开
  const logs = candidates.map((j) => Math.log1p(Math.max(1, j.approx_count)))
  const edu = candidates.map((j) => j.avg_education_rank)
  const exp = candidates.map((j) => j.avg_experience_rank)
  const scs = candidates.map((j) => j.composite_score)
  const norm = (v, arr) => {
    const lo = Math.min(...arr); const hi = Math.max(...arr)
    if (!Number.isFinite(lo) || !Number.isFinite(hi) || hi <= lo) return 0.5
    return (v - lo) / (hi - lo)
  }
  const vec = (j) => [
    norm(Math.log1p(Math.max(1, j.approx_count)), logs),
    norm(j.avg_education_rank, edu),
    norm(j.avg_experience_rank, exp),
    norm(j.composite_score, scs)
  ]
  const dist = (a, b) => Math.sqrt(a.reduce((s, x, i) => s + (x - b[i]) ** 2, 0))

  const byCount = [...candidates].sort((a, b) => b.approx_count - a.approx_count)
  const picks = []
  if (byCount[0]) picks.push(byCount[0])
  const lowScore = [...candidates].sort((a, b) => a.composite_score - b.composite_score)[0]
  if (lowScore && !picks.find((x) => x.job_title === lowScore.job_title)) picks.push(lowScore)
  while (picks.length < 6) {
    let best = null
    let bestScore = -1
    for (const c of candidates) {
      if (picks.find((x) => x.job_title === c.job_title)) continue
      const vc = vec(c)
      const d = picks.length ? Math.min(...picks.map((p) => dist(vc, vec(p)))) : 0
      const score = d + 0.12 * vc[0]
      if (score > bestScore) { best = c; bestScore = score }
    }
    if (!best) break
    picks.push(best)
  }

  const rankingPicks = picks.slice(0, 6).map((j) => {
    const barrier = (j.avg_education_rank + j.avg_experience_rank) / 2
    let contrast_tag = '常规对比型'
    if (j.approx_count >= byCount[Math.floor(Math.max(0, byCount.length * 0.2))]?.approx_count) contrast_tag = '高规模普及型'
    if (barrier >= 7) contrast_tag = '高门槛型'
    if (j.composite_score <= 0.15) contrast_tag = '低综合稳态型'
    return { ...j, records_count: j.approx_count, contrast_tag }
  })

  if (rankingPicks.length) return rankingPicks

  // 兜底：当排名来源无法提供足够候选（例如旧后端固定 top5）时，用专用对比接口
  return fallbackJobs()
})

const activeForceNetwork = computed(() => {
  if (!activeForceJobTitle.value) return null
  return forceNetworkByJob.value[activeForceJobTitle.value] || null
})

const forceAtlasNetworks = computed(() => {
  const jobs = forceJobs.value
  if (!jobs.length) return []
  const scores = jobs.map(j => Number(j.composite_score) || 0)
  const minScore = Math.min(...scores)
  const maxScore = Math.max(...scores)
  const span = Math.max(maxScore - minScore, 1e-9)

  return jobs.map((job) => {
    const network = forceNetworkByJob.value[job.job_title]
    if (!network) return null
    const score = Number(job.composite_score) || 0
    const t = (score - minScore) / span
    const centerScale = 1.0 + t * 0.65
    const leafScale = 0.9 + t * 0.25
    const nodes = Array.isArray(network.nodes)
      ? network.nodes.map((n) => {
          const isCenter = n.type === 'job'
          const base = Number(n.symbolSize || (isCenter ? 56 : 26))
          const factor = isCenter ? centerScale : leafScale
          return {
            ...n,
            symbolSize: Math.round(base * factor * 100) / 100
          }
        })
      : []

    return { ...network, nodes }
  }).filter(Boolean)
})

const selectedContrastNetwork = computed(() => {
  if (!selectedContrastJobTitle.value) return null
  return contrastNetworkByJob.value[selectedContrastJobTitle.value] || null
})

const displayedForceNetworks = computed(() => {
  if (!hideOtherForceGraphs.value) return forceAtlasNetworks.value

  const focused = activeForceNetwork.value
  const contrast = selectedContrastNetwork.value
  const arr = []
  if (focused) arr.push(focused)
  if (contrast) arr.push(contrast)
  return arr
})

const loadForceAtlasNetworks = async () => {
  const jobs = forceJobs.value
  if (!jobs.length) return
  forceAtlasLoading.value = true
  forceAtlasError.value = ''
  try {
    const pairs = await Promise.all(
      jobs.map(async (job) => {
        const res = await getQ5ForceJobNetwork(job.job_title, forceTopKIndustry.value, forceTier.value)
        return [job.job_title, res?.data || null]
      })
    )
    const map = {}
    pairs.forEach(([title, data]) => {
      if (data) map[title] = data
    })
    forceNetworkByJob.value = map
    if (!activeForceJobTitle.value && jobs.length) {
      activeForceJobTitle.value = jobs[0].job_title
    }
  } catch (err) {
    forceAtlasError.value = err?.message || '加载引力图失败'
    console.error('加载引力图集合失败:', err)
  } finally {
    forceAtlasLoading.value = false
  }
}

const autoLoadForceData = async () => {
  try {
    await executeForceJobs(5)
    if (!activeForceJobTitle.value && forceJobs.value.length) {
      activeForceJobTitle.value = forceJobs.value[0].job_title
    }
    await loadForceAtlasNetworks()
  } catch (err) {
    console.error('自动加载 Q5 引力图数据失败:', err)
  }
}

const loadContrastNetwork = async (jobTitle) => {
  if (!jobTitle) return
  if (contrastNetworkByJob.value[jobTitle]) return
  forceAtlasLoading.value = true
  forceAtlasError.value = ''
  try {
    const res = await getQ5ForceJobNetwork(jobTitle, forceTopKIndustry.value, forceTier.value)
    if (res?.data) {
      contrastNetworkByJob.value = { ...contrastNetworkByJob.value, [jobTitle]: res.data }
    }
  } catch (err) {
    forceAtlasError.value = err?.message || '加载对比引力图失败'
  } finally {
    forceAtlasLoading.value = false
  }
}

const selectForceJob = (jobTitle) => {
  if (!jobTitle) return
  activeForceJobTitle.value = jobTitle
}

const selectContrastJob = async (jobTitle) => {
  if (!jobTitle) return
  selectedContrastJobTitle.value = jobTitle
  await loadContrastNetwork(jobTitle)
}

const formatNum = (val) => {
  const n = Number(val)
  if (!Number.isFinite(n)) return '-'
  return n.toLocaleString()
}

const formatFloat = (val, d = 2) => {
  const n = Number(val)
  if (!Number.isFinite(n)) return '-'
  return n.toFixed(d)
}

watch([forceTier, forceTopKIndustry], async () => {
  if (forceJobs.value.length) {
    contrastNetworkByJob.value = {}
    await loadForceAtlasNetworks()
    if (hideOtherForceGraphs.value && selectedContrastJobTitle.value) {
      await loadContrastNetwork(selectedContrastJobTitle.value)
    }
  }
})

watch(hideOtherForceGraphs, async (v) => {
  if (!v) return
  if (!contrastJobs.value.length) {
    await executeContrastSource(6, 5)
  }
  if (!selectedContrastJobTitle.value && contrastJobs.value.length) {
    selectedContrastJobTitle.value = contrastJobs.value[0].job_title
  }
  if (selectedContrastJobTitle.value) {
    await loadContrastNetwork(selectedContrastJobTitle.value)
  }
})

watch(contrastJobs, async (list) => {
  if (!hideOtherForceGraphs.value) return
  if (selectedContrastJobTitle.value && !list.find((j) => j.job_title === selectedContrastJobTitle.value)) {
    selectedContrastJobTitle.value = ''
  }
  if (!selectedContrastJobTitle.value && list.length) {
    selectedContrastJobTitle.value = list[0].job_title
    await loadContrastNetwork(selectedContrastJobTitle.value)
  }
})

onMounted(async () => {
  await Promise.all([autoLoadForceData(), executeRanking(180), executeContrastSource(6, 5)])
  if (selectedContrastJobTitle.value) {
    await loadContrastNetwork(selectedContrastJobTitle.value)
  }
})
</script>

<style scoped>
.q5-tab {
  --q5-border: rgba(80, 111, 174, 0.14);
  --q5-text-main: #10315d;
  --q5-text-sub: #58739a;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.q5-hero,
.q5-workspace {
  border: 1px solid var(--q5-border);
  border-radius: 14px;
  background: linear-gradient(180deg, #fafdff 0%, #f3f8ff 100%);
}

.q5-hero {
  padding: 14px 16px;
}

.q5-hero h2 {
  margin: 0;
  font-size: 24px;
  color: var(--q5-text-main);
}

.q5-hero p {
  margin: 6px 0 0;
  color: var(--q5-text-sub);
  font-size: 13px;
}

.q5-workspace {
  padding: 12px;
}

.chart-section {
  background: #fff;
  border: 1px solid rgba(86, 122, 182, 0.16);
  border-radius: 12px;
  padding: 12px;
}

.chart-section h3 {
  margin: 0 0 10px;
  font-size: 18px;
  color: #204a7e;
}

.error-message {
  padding: 8px 10px;
  border: 1px solid #efc5c5;
  border-radius: 8px;
  color: #b14e4e;
  background: #fff8f8;
  margin-bottom: 8px;
}

.force-top-console {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.force-job-card {
  border: 1px solid #c7d6ec;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
  border-radius: 10px;
  padding: 10px;
  text-align: left;
  cursor: pointer;
}

.force-job-card.active {
  border-color: #5f8fdc;
  box-shadow: 0 0 0 2px rgba(95, 143, 220, 0.18);
}

.force-job-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #5f8fdc;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
}

.force-job-title {
  font-weight: 700;
  color: #1f4576;
  margin-bottom: 6px;
}

.force-job-metrics {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #5f7fa7;
}

.force-job-metrics b {
  color: #284f84;
}

.force-card-loading,
.force-map-loading {
  color: #5f7fa7;
  font-size: 13px;
  padding: 8px 4px;
}

.force-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.force-controls label,
.force-controls span {
  color: #4f6f9b;
  font-size: 13px;
}

.switch-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 8px;
}

.switch-inline input {
  accent-color: #2f6ed8;
}

.mode-hint {
  color: #5a7ea8;
  font-size: 12px;
}

.force-controls select {
  border: 1px solid #c8d9f0;
  border-radius: 8px;
  padding: 4px 8px;
  background: #f8fbff;
  color: #2d5587;
}

.contrast-panel {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px dashed #c8d9f0;
  border-radius: 10px;
  background: #f8fbff;
}

.contrast-panel h4 {
  margin: 0 0 8px;
  color: #2a5286;
  font-size: 14px;
}

.contrast-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.contrast-chip {
  border: 1px solid #c7d6ec;
  border-radius: 999px;
  background: #fff;
  color: #2a4f80;
  padding: 6px 10px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.contrast-chip .title {
  font-weight: 600;
}

.contrast-chip .meta {
  color: #6a87ac;
  font-size: 12px;
}

.contrast-chip .tag {
  color: #7b5b2a;
  background: #fff4df;
  border: 1px solid #f0d8ab;
  border-radius: 999px;
  padding: 1px 6px;
  font-size: 11px;
}

.contrast-chip.active {
  border-color: #5f8fdc;
  box-shadow: 0 0 0 2px rgba(95, 143, 220, 0.18);
}

.force-summary-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.force-kpi {
  border: 1px solid #d6e2f4;
  border-radius: 8px;
  padding: 8px 10px;
  background: #f9fcff;
  display: flex;
  justify-content: space-between;
  gap: 6px;
  font-size: 12px;
  color: #5f7fa7;
}

.force-kpi b {
  color: #244a7b;
}

.force-map-wrapper {
  border: 1px solid #d4e0f2;
  border-radius: 10px;
  padding: 8px;
  background: #fdfefe;
}
</style>
