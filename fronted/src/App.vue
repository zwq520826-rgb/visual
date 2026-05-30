<template>
  <div class="app">
    <Dashboard />
  </div>
</template>

<script setup>
import Dashboard from './components/Dashboard.vue'
</script>

<style scoped>
.app {
  min-height: 100vh;
  background:
    radial-gradient(circle at 8% 0%, rgba(46, 122, 198, 0.12), transparent 30%),
    radial-gradient(circle at 88% 2%, rgba(214, 107, 61, 0.11), transparent 28%),
    linear-gradient(180deg, #f8fbff, #edf4fb);
  position: relative;
  overflow-x: hidden;
}

.app::before {
  content: '';
  position: fixed;
  top: -14%;
  left: -8%;
  width: 52vw;
  height: 52vw;
  background: radial-gradient(circle, rgba(46, 122, 198, 0.13), transparent 68%);
  pointer-events: none;
  z-index: 0;
  filter: blur(4px);
}

.app::after {
  content: '';
  position: fixed;
  right: -12%;
  bottom: -26%;
  width: 44vw;
  height: 44vw;
  background: radial-gradient(circle, rgba(214, 107, 61, 0.14), transparent 70%);
  pointer-events: none;
  z-index: 0;
  filter: blur(8px);
}

/* 确保内容在背景之上 */
.app > * {
  position: relative;
  z-index: 1;
}
</style>
