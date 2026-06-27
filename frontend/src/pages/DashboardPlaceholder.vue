<template>
  <main class="placeholder-page">
    <section class="panel">
      <p class="eyebrow">研备通 AI</p>
      <h1>教师工作台</h1>
      <p>登录成功。完整工作台页面已接入，请从导航进入对应功能。</p>
    </section>
  </main>
</template>

<style scoped>
.placeholder-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  background: var(--bg);
}

section {
  width: min(100%, 560px);
}

h1 {
  margin: 0 0 10px;
  font-size: 1.75rem;
}

p {
  color: var(--muted);
}
</style>
