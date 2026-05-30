<template>
  <section class="q4-tab">
    <header class="q4-hero">
      <h2>Q4 地域招聘结构与分群洞察</h2>
      <p>聚合热力分布、地域聚类和城市画像，形成从宏观到微观的地域策略视图。</p>
    </header>
    <article class="q4-shell">
      <Q4RegionAnalysis />
    </article>
  </section>
</template>

<script setup>
import Q4RegionAnalysis from '../Q4/Q4_RegionAnalysis.vue';
</script>

<style scoped>
.q4-tab {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border-radius: 16px;
  background: radial-gradient(circle at 12% 12%, #f3f7ff 0%, #eef3fb 35%, #e9eef8 100%);
}

.q4-hero,
.q4-shell {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(80, 111, 174, 0.12);
  border-radius: 14px;
  box-shadow: 0 8px 20px rgba(64, 89, 138, 0.08);
}

.q4-hero {
  padding: 16px 18px;
}

.q4-hero h2 {
  margin: 0;
  color: #102f5c;
  font-size: 28px;
}

.q4-hero p {
  margin: 8px 0 0;
  color: #56739a;
  font-size: 14px;
}

.q4-shell {
  padding: 10px;
}
</style>
