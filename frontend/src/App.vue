<template>
  <!-- 路由视图：不同的页面会在这里渲染，就像一个容器 -->
  <router-view />
</template>

<script setup lang="ts">
// 这里是根组件，我们只让它渲染路由视图，其他什么都不做
</script>

<style>
/* 覆盖浏览器默认的内边距和外边距，让页面铺满整个屏幕 */
html, body, #app {
  margin: 0;
  padding: 0;
  width: 100vw;
  height: 100vh;
}
</style>