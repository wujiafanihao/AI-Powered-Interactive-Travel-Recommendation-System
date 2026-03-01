<template>
  <router-view />
</template>

<script setup lang="ts">
// 这里是根组件，我们只让它渲染路由视图
</script>

<style>
/* 覆盖默认的内边距和外边距 */
html, body, #app {
  margin: 0;
  padding: 0;
  width: 100vw;
  height: 100vh;
}
</style>