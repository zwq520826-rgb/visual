<template>
  <section class="q4-region-analysis">
    <header class="control-bar">
      <div class="title-block">
        <h2>Q4 地域招聘活动画像</h2>
        <p>基于特征空间聚类与相似性构建：主视图热力图 + 地域分组聚簇图 + 单地域画像。</p>
      </div>
      <div class="controls">
        <label>
          <span>簇数</span>
          <select v-model.number="nClusters" @change="reloadRegionArtifacts">
            <option :value="4">4</option>
            <option :value="5">5</option>
            <option :value="6">6</option>
            <option :value="7">7</option>
          </select>
        </label>
        <label>
          <span>算法</span>
          <select v-model="algorithm" @change="reloadRegionArtifacts">
            <option value="kmeans">KMeans</option>
          </select>
        </label>
        <label>
          <span>度量指标</span>
          <select v-model="selectedMetric" @change="reloadHeatmap">
            <option v-for="metric in metricOptions" :key="metric.value" :value="metric.value">
              {{ metric.label }}
            </option>
          </select>
        </label>
        <button type="button" class="btn" @click="clearClusterFilter">清除簇筛选</button>
      </div>
    </header>

    <div class="quality-bar" v-if="quality">
      <span>地域数：{{ metadata?.n_regions ?? regions.length }}</span>
      <span>聚类：{{ metadata?.cluster_algorithm || algorithm }} / {{ metadata?.n_clusters ?? nClusters }} 簇</span>
      <span>Silhouette：{{ formatMetric(quality.silhouette_score) }}</span>
      <span>DBI：{{ formatMetric(quality.davies_bouldin_index) }}</span>
    </div>

    <div class="heatmap-main">
      <div class="heatmap-pane">
        <div class="pane-head">
          <h3>视图 C：城市等级矩形热力图（主视图）</h3>
          <p>沿用项目原有热力图组件（城市等级 × 公司类型）。点击城市方块可联动下方视图。</p>
          <div class="tier-switch" role="tablist" aria-label="城市等级切换">
            <button
              v-for="tier in tierOptions"
              :key="`tier-inline-${tier.value}`"
              type="button"
              class="tier-btn"
              :class="{ active: selectedTier === tier.value }"
              @click="setTierInline(tier.value)"
            >
              {{ tier.label }}
            </button>
          </div>
        </div>
        <CityTierHeatmap
          :tier="selectedTier"
          :metric="selectedMetric"
          dimension-label="公司类型"
          :dataset="heatmapPayload"
          :loading="loadingHeatmap"
          :error="heatmapError"
          :auto-fetch="false"
          @city-click="handleCityClick"
        />
      </div>
      <aside class="right-panel">
        <RegionProfile
          :region="regionDetail"
          :loading="loadingDetail"
          :error="detailError"
          @select-region="selectRegion"
        />
      </aside>
    </div>

    <div class="top-grid">
      <RegionClusterMap
        :regions="regions"
        :cluster-summary="clusterSummary"
        :metadata="metadata"
        :selected-region-id="selectedRegionId"
        :selected-cluster-id="selectedClusterId"
        :focus-city-id="selectedCityCode"
        :heatmap-similar-regions="heatmapSimilarRegions"
        :loading="loadingSummary || loadingCluster"
        :error="summaryError || clusterError"
        @select-region="selectRegion"
        @select-cluster="toggleCluster"
      />
      <RegionSimilarityChart
        :city="selectedCityCode"
        :auto-fetch="true"
        :top-similar="5"
      />
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import RegionClusterMap from './RegionClusterMap.vue';
import RegionProfile from './RegionProfile.vue';
import CityTierHeatmap from '../charts/CityTierHeatmap.vue';
import RegionSimilarityChart from '../charts/RegionSimilarityChart.vue';
import { getRegionProfile } from '../../api/regionProfileApi';
import {
  getQ4DataQuality,
  getRegionClusterSummary,
  getRegionDetail,
  getRegionsSummary,
} from '../../api/q4RegionApi';
import { useHeatmapData } from '../../composables/useHeatmapData';

const nClusters = ref(4);
const algorithm = ref('kmeans');
const sampleSize = ref(0);
const selectedTier = ref('first_tier');
const selectedMetric = ref('job_count');

const tierOptions = [
  { value: 'first_tier', label: '一线城市' },
  { value: 'second_tier', label: '二线城市' },
  { value: 'third_tier', label: '三线城市' },
  { value: 'other', label: '其他城市' },
];

const metricOptions = [
  { value: 'job_count', label: '职位数量' },
  { value: 'industry_ratio', label: '行业占比' },
  { value: 'location_quotient', label: '区位商' },
];

const regions = ref([]);
const clusterSummary = ref([]);
const metadata = ref(null);
const quality = ref(null);
const regionDetail = ref(null);
const heatmapSimilarRegions = ref([]);

const selectedRegionId = ref(null);
const selectedClusterId = ref(null);
const selectedCityCode = ref(null);
const selectedCityName = ref(null);

const loadingSummary = ref(false);
const loadingCluster = ref(false);
const loadingDetail = ref(false);

const summaryError = ref('');
const clusterError = ref('');
const detailError = ref('');

const {
  loading: loadingHeatmap,
  error: heatmapErrorRaw,
  heatmapPayload,
  loadHeatmap: loadCityTierHeatmap,
} = useHeatmapData();
const heatmapError = computed(() => heatmapErrorRaw.value || '');

const formatMetric = (v) => (v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : Number(v).toFixed(4));

const clusterParams = () => ({
  nClusters: nClusters.value,
  algorithm: algorithm.value,
  sampleSize: sampleSize.value,
});

const loadSummary = async () => {
  loadingSummary.value = true;
  summaryError.value = '';
  try {
    const res = await getRegionsSummary(clusterParams());
    regions.value = res?.data?.regions || [];
    metadata.value = res?.data?.metadata || null;
    if (!selectedRegionId.value && regions.value.length) {
      selectedRegionId.value = regions.value[0].region_id;
      selectedCityCode.value = regions.value[0].region_id;
      selectedCityName.value = regions.value[0].region_id;
    }
  } catch (e) {
    summaryError.value = e?.message || String(e);
    regions.value = [];
  } finally {
    loadingSummary.value = false;
  }
};

const loadClusterSummary = async () => {
  loadingCluster.value = true;
  clusterError.value = '';
  try {
    const res = await getRegionClusterSummary(clusterParams());
    clusterSummary.value = res?.data?.clusters || [];
  } catch (e) {
    clusterError.value = e?.message || String(e);
    clusterSummary.value = [];
  } finally {
    loadingCluster.value = false;
  }
};

const loadQuality = async () => {
  try {
    const res = await getQ4DataQuality(clusterParams());
    quality.value = res?.data || null;
  } catch (_) {
    quality.value = null;
  }
};

const loadDetail = async (regionId) => {
  if (!regionId) {
    regionDetail.value = null;
    return;
  }
  loadingDetail.value = true;
  detailError.value = '';
  try {
    const res = await getRegionDetail(regionId, clusterParams());
    regionDetail.value = res?.data || null;
  } catch (e) {
    detailError.value = e?.message || String(e);
    regionDetail.value = null;
  } finally {
    loadingDetail.value = false;
  }
};

const loadHeatmap = async () => {
  await loadCityTierHeatmap({
    tier: selectedTier.value,
    metric: selectedMetric.value,
    dimension_y: 'company_type',
  });
};

const loadHeatmapSimilarity = async (cityCode) => {
  if (!cityCode) {
    heatmapSimilarRegions.value = [];
    return;
  }
  try {
    const res = await getRegionProfile(cityCode, 5);
    const data = res?.data || {};
    heatmapSimilarRegions.value = Array.isArray(data.similar_regions) ? data.similar_regions : [];
  } catch (_) {
    heatmapSimilarRegions.value = [];
  }
};

const reloadRegionArtifacts = async () => {
  await Promise.all([loadSummary(), loadClusterSummary()]);
  await loadQuality();
};

const reloadHeatmap = async () => {
  await loadHeatmap();
};

const setTierInline = async (tierValue) => {
  if (!tierValue || selectedTier.value === tierValue) return;
  selectedTier.value = tierValue;
  await reloadHeatmap();
};

const selectRegion = (regionId) => {
  selectedRegionId.value = regionId;
  selectedCityCode.value = regionId || null;
};

const toggleCluster = (cid) => {
  if (selectedClusterId.value === cid) {
    selectedClusterId.value = null;
  } else {
    selectedClusterId.value = cid;
  }
};

const clearClusterFilter = () => {
  selectedClusterId.value = null;
};

const handleCityClick = (payload) => {
  if (!payload || !payload.city) return;
  selectedCityCode.value = payload.city;
  selectedCityName.value = payload.cityName || payload.city;
  selectedRegionId.value = payload.city;
};

watch(
  () => selectedRegionId.value,
  async (val) => {
    await Promise.all([loadDetail(val), loadHeatmapSimilarity(selectedCityCode.value || val)]);
  },
  { immediate: true },
);

onMounted(async () => {
  await Promise.all([reloadRegionArtifacts(), reloadHeatmap()]);
  if (selectedRegionId.value) {
    await loadDetail(selectedRegionId.value);
  }
});
</script>

<style scoped>
.q4-region-analysis {
  --q4-border: rgba(86, 122, 182, 0.16);
  --q4-text-main: #163a6a;
  --q4-text-sub: #5c7aa3;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
  border: 1px solid var(--q4-border);
  border-radius: 12px;
  padding: 14px 16px;
  background: linear-gradient(180deg, #f9fcff, #f1f7ff);
  box-shadow: 0 8px 20px rgba(64, 89, 138, 0.07);
}

.title-block h2 {
  margin: 0;
  font-size: 24px;
  color: var(--q4-text-main);
}

.title-block p {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--q4-text-sub);
}

.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-end;
}

.controls label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.controls label span {
  font-size: 11px;
  color: #6785ad;
  font-weight: 700;
}

.controls select {
  min-width: 94px;
  border: 1px solid #bfd1ec;
  border-radius: 8px;
  padding: 7px 8px;
  color: #2d527f;
  background: #f9fcff;
}

.btn {
  border: 1px solid #b9cdef;
  border-radius: 8px;
  background: #f4f8ff;
  color: #2d5488;
  padding: 8px 10px;
  cursor: pointer;
  font-weight: 600;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 12px rgba(66, 108, 172, 0.14);
}

.quality-bar {
  border: 1px solid var(--q4-border);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.86);
  padding: 10px 12px;
  color: #4e6c97;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 12px;
}

.top-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
  gap: 12px;
}

.heatmap-main {
  display: grid;
  grid-template-columns: minmax(0, 1.78fr) minmax(300px, 1fr);
  gap: 12px;
}

.heatmap-pane {
  border: 1px solid var(--q4-border);
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #f9fcff 100%);
  padding: 10px;
  box-shadow: 0 6px 14px rgba(72, 106, 161, 0.08);
}

.pane-head h3 {
  margin: 0;
  font-size: 18px;
  color: #2b4f86;
}

.pane-head p {
  margin: 4px 0 8px;
  font-size: 12px;
  color: #6f88af;
}

.tier-switch {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 2px 0 8px;
}

.tier-btn {
  border: 1px solid #c8d9f2;
  background: #f7faff;
  color: #3a5f93;
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 12px;
  cursor: pointer;
}

.tier-btn.active {
  background: #2f5e9c;
  border-color: #2f5e9c;
  color: #fff;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.right-panel :deep(.region-profile) {
  min-height: 520px;
}

.side-head h4 {
  margin: 2px 0 8px;
  font-size: 15px;
  color: #2c4f87;
}

.state-box {
  min-height: 120px;
  border: 1px dashed #c2d4ef;
  border-radius: 8px;
  color: #6f88af;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 13px;
}

.state-box.small {
  min-height: 120px;
}

.state-box.error {
  color: #b05050;
  border-color: #ebc6c6;
}

@media (max-width: 1320px) {
  .control-bar {
    flex-direction: column;
  }

  .top-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .heatmap-main {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
