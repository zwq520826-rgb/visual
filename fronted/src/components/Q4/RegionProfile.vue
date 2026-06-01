<template>
  <div class="region-profile">
    <div class="head">
      <h3>视图 B：精简单地域画像</h3>
      <p>当前地域：{{ region?.region_label || '—' }} {{ region?.region_id || '' }}</p>
    </div>

    <div v-if="error" class="state-box error">{{ error }}</div>
    <div v-else-if="loading" class="state-box">加载中...</div>
    <div v-else-if="!region" class="state-box">请选择左侧地域点查看画像</div>
    <div v-else class="body">
      <div class="kpi-grid">
        <div class="kpi"><span>城市等级</span><strong>{{ region.city_tier || '-' }}</strong></div>
        <div class="kpi"><span>岗位数量</span><strong>{{ Number(region.job_count || 0).toLocaleString() }}</strong></div>
        <div class="kpi"><span>平均薪资</span><strong>{{ Number(region.salary_profile?.mean || 0).toFixed(2) }}</strong></div>
        <div class="kpi"><span>中位薪资</span><strong>{{ Number(region.salary_profile?.median || 0).toFixed(2) }}</strong></div>
      </div>

      <div class="charts-grid">
        <div ref="industryRef" class="mini-chart"></div>
        <div ref="positionRef" class="mini-chart"></div>
      </div>
      <div ref="radarRef" class="radar-chart"></div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  region: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: '',
  },
});

defineEmits(['select-region']);

const industryRef = ref(null);
const positionRef = ref(null);
const radarRef = ref(null);
let industryChart = null;
let positionChart = null;
let radarChart = null;

const disposeAll = () => {
  if (industryChart) industryChart.dispose();
  if (positionChart) positionChart.dispose();
  if (radarChart) radarChart.dispose();
  industryChart = null;
  positionChart = null;
  radarChart = null;
};

const renderBars = () => {
  if (!props.region || !industryRef.value || !positionRef.value) return;
  if (industryChart) industryChart.dispose();
  if (positionChart) positionChart.dispose();
  industryChart = echarts.init(industryRef.value);
  positionChart = echarts.init(positionRef.value);

  const isOtherLabel = (label) => {
    const v = String(label || '').trim().toLowerCase();
    return v === '其他' || v === 'other';
  };

  const inds = (props.region.industry_top || [])
    .filter((i) => !isOtherLabel(i?.industry))
    .slice(0, 5);
  const poss = (props.region.position_category_top || [])
    .filter((i) => !isOtherLabel(i?.category))
    .slice(0, 5);
  industryChart.setOption({
    title: { text: '行业 Top5', left: 8, top: 2, textStyle: { fontSize: 13, color: '#2d538c' } },
    grid: { left: 80, right: 12, top: 34, bottom: 20 },
    xAxis: { type: 'value', axisLabel: { color: '#6985ad', fontSize: 11 }, splitLine: { lineStyle: { color: '#edf2fa' } } },
    yAxis: {
      type: 'category',
      data: inds.map((i) => i.industry),
      axisLabel: { color: '#5878a6', fontSize: 11 },
    },
    tooltip: { trigger: 'item', formatter: (p) => `${p.name}<br/>${p.value}` },
    series: [{ type: 'bar', data: inds.map((i) => i.count), itemStyle: { color: '#5f8fdc' }, barWidth: 12 }],
  });

  positionChart.setOption({
    title: { text: '职位 Top5', left: 8, top: 2, textStyle: { fontSize: 13, color: '#2d538c' } },
    grid: { left: 80, right: 12, top: 34, bottom: 20 },
    xAxis: { type: 'value', axisLabel: { color: '#6985ad', fontSize: 11 }, splitLine: { lineStyle: { color: '#edf2fa' } } },
    yAxis: {
      type: 'category',
      data: poss.map((i) => i.category),
      axisLabel: { color: '#5878a6', fontSize: 11 },
    },
    tooltip: { trigger: 'item', formatter: (p) => `${p.name}<br/>${p.value}` },
    series: [{ type: 'bar', data: poss.map((i) => i.count), itemStyle: { color: '#8d72d1' }, barWidth: 12 }],
  });
};

const renderRadar = () => {
  if (!props.region || !radarRef.value) return;
  if (radarChart) radarChart.dispose();
  radarChart = echarts.init(radarRef.value);
  const m = props.region.radar_metrics || {};

  const tierRaw = String(props.region.city_tier || '').trim();
  const tierMap = {
    '一线': 1.0,
    '二线': 0.75,
    '三线': 0.5,
    '其他': 0.25,
  };
  const cityTierScore = Number.isFinite(tierMap[tierRaw]) ? tierMap[tierRaw] : Number(m.finance_maturity || 0);

  const radarDims = [
    {
      name: '招聘规模强度',
      value: Number(m.scale_intensity ?? m.log_job_count ?? 0),
      desc: '对应热力图 metric=job_count 与聚类规模。',
    },
    {
      name: '学历要求',
      value: Number(m.education_level ?? 0),
      desc: '地域招聘学历门槛强度。',
    },
    {
      name: '经验要求',
      value: Number(m.experience_demand ?? 0),
      desc: '地域招聘经验门槛强度。',
    },
    {
      name: '行业多样性',
      value: Number(m.industry_entropy ?? 0),
      desc: '行业分布越分散，数值越高。',
    },
    {
      name: '职位多样性',
      value: Number(m.position_entropy ?? 0),
      desc: '职位分布越分散，数值越高。',
    },
    {
      name: '城市等级',
      value: cityTierScore,
      desc: '由一线/二线/三线/其他映射为数值。',
    },
  ];
  const v = radarDims.map((d) => Math.max(0, Math.min(1, Number(d.value || 0))));
  const indicators = radarDims.map((d) => ({ name: d.name, max: 1 }));

  radarChart.setOption({
    title: { text: 'Q4 任务导向雷达', left: 8, top: 4, textStyle: { fontSize: 13, color: '#2d538c' } },
    radar: {
      center: ['50%', '56%'],
      radius: '62%',
      splitNumber: 4,
      axisName: { color: '#5f7ea8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#e6eefb' } },
      splitArea: { show: true, areaStyle: { color: ['#fbfdff', '#f5f9ff'] } },
      indicator: indicators,
    },
    tooltip: {
      trigger: 'item',
      formatter: () => {
        const lines = radarDims.map((d, i) => `${d.name}：${(v[i] * 100).toFixed(1)}%`);
        return [`${props.region.region_label || props.region.region_id || '地域画像'}`, ...lines].join('<br/>');
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: v,
            areaStyle: { color: 'rgba(91,130,212,0.35)' },
            lineStyle: { color: '#3f79d6' },
            itemStyle: { color: '#3f79d6' },
          },
        ],
      },
    ],
  });
};

watch(
  () => props.region,
  () => {
    nextTick(() => {
      renderBars();
      renderRadar();
    });
  },
  { deep: true },
);

onMounted(() => {
  nextTick(() => {
    renderBars();
    renderRadar();
  });
});

onUnmounted(() => disposeAll());
</script>

<style scoped>
.region-profile {
  border: 1px solid #cddcf2;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
  min-height: 520px;
}

.head h3 {
  margin: 0;
  font-size: 18px;
  color: #2b4f86;
}

.head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #6f88af;
}

.state-box {
  min-height: 280px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #6f88af;
  font-size: 13px;
  border: 1px dashed #c1d4ef;
  border-radius: 8px;
  margin-top: 8px;
}

.state-box.error {
  color: #b05050;
  border-color: #e8c3c3;
}

.kpi-grid {
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.kpi {
  border: 1px solid #d8e4f6;
  border-radius: 8px;
  padding: 8px;
  background: #f9fbff;
}

.kpi span {
  display: block;
  font-size: 11px;
  color: #7090b7;
}

.kpi strong {
  margin-top: 4px;
  display: block;
  color: #244b82;
  font-size: 15px;
}

.charts-grid {
  margin-top: 8px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.mini-chart {
  height: 220px;
  border: 1px solid #dbe6f7;
  border-radius: 8px;
}

.radar-chart {
  margin-top: 8px;
  height: 250px;
  border: 1px solid #dbe6f7;
  border-radius: 8px;
}

</style>
