<template>
  <div class="industry-heatmap-wrap">
    <div class="heatmap-pane">
      <div class="pane-head">
        <h3>视图 C：行业-地域热力图</h3>
        <p>点击单元格可联动地域画像；颜色表示地域内行业占比。</p>
      </div>
      <div v-if="error" class="state-box error">{{ error }}</div>
      <div v-else-if="loading" class="state-box">加载中...</div>
      <div v-else-if="!matrix?.heatmap_data?.length" class="state-box">暂无热力图数据</div>
      <div v-else ref="chartRef" class="heatmap-chart"></div>
    </div>

    <aside class="co-pane">
      <div class="side-head">
        <h4>职位-行业共现摘要（视图D并入）</h4>
      </div>
      <div v-if="coError" class="state-box error small">{{ coError }}</div>
      <div v-else-if="coLoading" class="state-box small">加载中...</div>
      <div v-else-if="!cooccurrence?.top_pairs?.length" class="state-box small">暂无共现数据</div>
      <div v-else class="pair-list">
        <div class="pair-row" v-for="(p, idx) in cooccurrence.top_pairs" :key="`${p.job_title}-${p.industry}-${idx}`">
          <div class="left">
            <span class="job">{{ p.job_title }}</span>
            <span class="arrow">→</span>
            <span class="ind">{{ p.industry }}</span>
          </div>
          <strong>{{ p.count }}</strong>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  matrix: {
    type: Object,
    default: null,
  },
  cooccurrence: {
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
  coLoading: {
    type: Boolean,
    default: false,
  },
  coError: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['select-region']);

const chartRef = ref(null);
let chart = null;

const render = () => {
  if (!chartRef.value || !props.matrix?.heatmap_data?.length) return;
  if (chart) chart.dispose();
  chart = echarts.init(chartRef.value);

  const xAxis = props.matrix.dimensions?.x_axis || [];
  const yAxis = props.matrix.dimensions?.y_axis || [];
  const data = (props.matrix.heatmap_data || [])
    .map((it) => {
      const xi = xAxis.indexOf(it.x);
      const yi = yAxis.indexOf(it.y);
      if (xi < 0 || yi < 0) return null;
      return [xi, yi, Number(it.value || 0), it];
    })
    .filter(Boolean);
  const maxV = data.reduce((m, d) => Math.max(m, Number(d[2] || 0)), 0) || 1;

  chart.setOption({
    grid: { left: 96, right: 18, top: 48, bottom: 68 },
    xAxis: {
      type: 'category',
      data: xAxis,
      axisLabel: { interval: 0, rotate: 28, color: '#5f7ea8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#a8bee0' } },
    },
    yAxis: {
      type: 'category',
      data: yAxis,
      axisLabel: { color: '#5f7ea8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#a8bee0' } },
    },
    visualMap: {
      min: 0,
      max: maxV,
      orient: 'horizontal',
      left: 'center',
      bottom: 10,
      inRange: { color: ['#f5f8ff', '#b7d1fb', '#5b90e2', '#1f5cb8'] },
      text: ['高', '低'],
      textStyle: { color: '#6281ac' },
    },
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        const d = p.data?.[3];
        if (!d) return '';
        return [
          `<strong>${d.y}</strong> · ${d.city_tier || '-'}`,
          `行业：${d.x}`,
          `占比：${(Number(d.value || 0) * 100).toFixed(2)}%`,
          `岗位数：${d.count || 0}`,
          `城市内排名：${d.rank_in_region ?? '--'}`,
        ].join('<br/>');
      },
    },
    series: [
      {
        type: 'heatmap',
        data,
        emphasis: { itemStyle: { borderColor: '#285fba', borderWidth: 1 } },
      },
    ],
  });

  chart.off('click');
  chart.on('click', (params) => {
    const item = params?.data?.[3];
    if (item?.y) {
      emit('select-region', item.y);
    }
  });
};

watch(
  () => props.matrix,
  () => nextTick(() => render()),
  { deep: true },
);

onMounted(() => nextTick(() => render()));
onUnmounted(() => {
  if (chart) {
    chart.dispose();
    chart = null;
  }
});
</script>

<style scoped>
.industry-heatmap-wrap {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(280px, 1fr);
  gap: 12px;
  min-height: 460px;
}

.heatmap-pane,
.co-pane {
  border: 1px solid #cddcf2;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
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

.heatmap-chart {
  margin-top: 6px;
  height: 380px;
}

.side-head h4 {
  margin: 2px 0 8px;
  font-size: 15px;
  color: #2c4f87;
}

.state-box {
  min-height: 210px;
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

.pair-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pair-row {
  border: 1px solid #d7e3f5;
  border-radius: 8px;
  padding: 8px;
  background: #f9fbff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.left {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.job,
.ind {
  font-size: 12px;
  color: #315b93;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow {
  color: #7b96bb;
}

.pair-row strong {
  color: #244c83;
  font-size: 12px;
}

@media (max-width: 1280px) {
  .industry-heatmap-wrap {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

