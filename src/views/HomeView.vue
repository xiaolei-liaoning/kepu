<script setup lang="ts">
// 入口页：两个模块的门户
</script>

<template>
  <main class="home">
    <header class="home-head">
      <p class="eyebrow">科普互动体验</p>
      <h1>线索里的中国</h1>
      <p class="sub">顺着线索，解锁一段段故事——从尧舜走到今天，从节气走到瓷器。</p>
    </header>

    <section class="entries">
      <router-link class="entry" to="/timeline">
        <span class="entry-index">壹</span>
        <div class="entry-body">
          <h2>上下五千年</h2>
          <p>从尧舜禅让到现代中国，十六个时代节点。看完正文，点开线索，解锁下一段。</p>
          <span class="entry-go">进入时间线 →</span>
        </div>
      </router-link>

      <router-link class="entry" to="/culture">
        <span class="entry-index">贰</span>
        <div class="entry-body">
          <h2>传统文化画卷</h2>
          <p>五幅长卷徐徐展开：节气、端午、书法、丝路、瓷器。一幕一画，一线索一故事。</p>
          <span class="entry-go">展开画卷 →</span>
        </div>
      </router-link>
    </section>

    <footer class="home-foot">内容取自本地科普脚本 · 逐段线索解锁</footer>
  </main>
</template>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 48px;
  padding: 48px 24px;
  background:
    radial-gradient(1200px 500px at 50% -10%, rgba(166, 128, 45, 0.12), transparent 70%),
    radial-gradient(800px 400px at 90% 110%, rgba(47, 93, 98, 0.1), transparent 70%),
    var(--paper);
}

.home-head {
  text-align: center;
  max-width: 720px;
}

.eyebrow {
  margin: 0 0 12px;
  letter-spacing: 0.5em;
  text-indent: 0.5em;
  font-size: 13px;
  color: var(--gold);
}

.home-head h1 {
  margin: 0;
  font-size: clamp(40px, 7vw, 64px);
  font-weight: 600;
  letter-spacing: 0.18em;
  text-indent: 0.18em;
}

.sub {
  margin: 16px 0 0;
  color: var(--ink-soft);
  font-size: 16px;
  line-height: 1.9;
}

.entries {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  justify-content: center;
}

.entry {
  display: flex;
  gap: 20px;
  width: min(420px, 90vw);
  padding: 28px;
  background: rgba(255, 253, 247, 0.75);
  border: 1px solid var(--line);
  border-radius: 4px;
  box-shadow: var(--shadow-soft);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}

.entry:hover {
  transform: translateY(-4px);
  border-color: var(--seal);
  box-shadow: 0 16px 40px rgba(31, 27, 22, 0.18);
}

.entry-index {
  flex: none;
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border: 1.5px solid var(--seal);
  border-radius: 50%;
  color: var(--seal);
  font-size: 22px;
}

.entry-body h2 {
  margin: 0 0 8px;
  font-size: 22px;
  letter-spacing: 0.1em;
}

.entry-body p {
  margin: 0 0 14px;
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 1.9;
}

.entry-go {
  font-size: 14px;
  color: var(--seal);
  letter-spacing: 0.08em;
}

.home-foot {
  font-size: 12px;
  color: var(--ink-faint);
  letter-spacing: 0.2em;
}
</style>
