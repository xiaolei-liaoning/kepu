<script setup lang="ts">
// 时间线视图：水墨宣纸质感的纵向时间线，线索卡逐段解锁。
// 交互契约：节点索引 ≤ unlockedIndex 方可阅读；当前段线索全部阅毕后自动解锁下一段。
// 数据只依赖 src/types.ts 的契约，节点数量任意（≥1），不做任何硬编码。
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { timelineData } from '@/data/timeline'
import { sceneVideos, timelineVideoKey } from '@/data/videos'
import type { TimelineNode } from '@/types'
import SceneVideo from '@/components/SceneVideo.vue'

/** 节点配视频路径：无值则不渲染视频槽 */
function nodeVideoSrc(nodeId: number): string | undefined {
  return sceneVideos[timelineVideoKey(nodeId)]
}

const nodes = timelineData.nodes

/** 最高可读节点索引（0 起） */
const unlockedIndex = ref(0)
/** 已阅线索集合，键为 `${nodeId}:${clueIndex}` */
const revealed = ref<Set<string>>(new Set())
/** 刚解锁、需要高亮提示的节点 id */
const highlightId = ref<number | null>(null)
/** 底部提示条文案 */
const toastText = ref('')

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

const unlockedCount = computed(() => Math.min(unlockedIndex.value + 1, nodes.length))
const progressPercent = computed(() =>
  nodes.length === 0 ? 0 : (unlockedCount.value / nodes.length) * 100,
)
const allDone = computed(() => nodes.length > 0 && unlockedIndex.value >= nodes.length - 1)

const CN_NUMERALS = [
  '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
  '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
] as const

/** 每节点装饰色（artNote 仅作内部美术指引，不参与可见文案） */
const ACCENTS = ['var(--seal)', 'var(--gold)', 'var(--azure)', 'var(--jade)'] as const

function cnNum(n: number): string {
  return n >= 1 && n <= CN_NUMERALS.length ? CN_NUMERALS[n - 1] : String(n)
}

function accentAt(index: number): string {
  return ACCENTS[index % ACCENTS.length]
}

function clueKey(nodeId: number, clueIndex: number): string {
  return `${nodeId}:${clueIndex}`
}

function isNodeReadable(index: number): boolean {
  return index <= unlockedIndex.value
}

function isRevealed(nodeId: number, clueIndex: number): boolean {
  return revealed.value.has(clueKey(nodeId, clueIndex))
}

function revealedCount(node: TimelineNode): number {
  let count = 0
  for (let ci = 0; ci < node.clues.length; ci++) {
    if (isRevealed(node.id, ci)) count += 1
  }
  return count
}

function allCluesRevealed(node: TimelineNode): boolean {
  return node.clues.every((_, clueIndex) => isRevealed(node.id, clueIndex))
}

let toastTimer: number | undefined
let highlightTimer: number | undefined

function showToast(text: string): void {
  toastText.value = text
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => {
    toastText.value = ''
  }, 2800)
}

/** 点开一条线索；若因此阅毕本段全部线索，则自动解锁下一段 */
function revealClue(nodeIndex: number, clueIndex: number): void {
  const node = nodes[nodeIndex]
  if (!node || !isNodeReadable(nodeIndex)) return
  const key = clueKey(node.id, clueIndex)
  if (revealed.value.has(key)) return
  const next = new Set(revealed.value)
  next.add(key)
  revealed.value = next
  if (allCluesRevealed(node) && nodeIndex + 1 < nodes.length) {
    void unlockNode(nodeIndex + 1)
  }
}

async function unlockNode(index: number): Promise<void> {
  const node = nodes[index]
  if (!node) return
  unlockedIndex.value = index
  highlightId.value = node.id
  window.clearTimeout(highlightTimer)
  highlightTimer = window.setTimeout(() => {
    highlightId.value = null
  }, 2600)
  showToast(`下一段已解锁 · ${node.title}`)
  await nextTick()
  document
    .getElementById(`node-${node.id}`)
    ?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'center' })
}

/** 重新封缄：回到第一段，清空全部已阅线索 */
async function resetTimeline(): Promise<void> {
  unlockedIndex.value = 0
  revealed.value = new Set()
  highlightId.value = null
  showToast('已重新封缄 · 从第一段再读')
  await nextTick()
  window.scrollTo({ behavior: prefersReducedMotion ? 'auto' : 'smooth', top: 0 })
}

function scrollToList(): void {
  document
    .getElementById('node-list')
    ?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' })
}

onBeforeUnmount(() => {
  window.clearTimeout(toastTimer)
  window.clearTimeout(highlightTimer)
})
</script>

<template>
  <main class="timeline-page">
    <div class="grain" aria-hidden="true"></div>

    <header class="hero">
      <p class="hero-eyebrow">科普互动体验 · 线索解锁</p>
      <h1 class="hero-title">{{ timelineData.title }}</h1>
      <div class="hero-rule" aria-hidden="true"></div>
      <p class="hero-sub">
        共 {{ nodes.length }} 个时代节点，逐段阅读。每段正文之后藏着线索，全部阅毕，下一段才会展开。
      </p>
      <div class="hero-side" aria-hidden="true">{{ timelineData.title }}</div>
      <button type="button" class="hero-scroll" @click="scrollToList">
        <span>向下展卷</span>
        <i class="hero-scroll-line" aria-hidden="true"></i>
      </button>
    </header>

    <div class="progress-bar" role="status" :aria-label="`已解锁 ${unlockedCount} / ${nodes.length}`">
      <div class="progress-head">
        <span class="progress-title">{{ timelineData.title }}</span>
        <span class="progress-count">已解锁 {{ unlockedCount }} / {{ nodes.length }}</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${progressPercent}%` }"></div>
      </div>
    </div>

    <section id="node-list" class="timeline" aria-label="历史时间线">
      <div class="axis" aria-hidden="true"></div>

      <article
        v-for="(node, i) in nodes"
        :key="node.id"
        :id="`node-${node.id}`"
        class="node"
        :class="[`node--${i % 2 === 0 ? 'left' : 'right'}`, { 'is-locked': !isNodeReadable(i), 'is-frontier': i === unlockedIndex, 'is-new': highlightId === node.id }]"
        :style="{ '--accent': accentAt(i) }"
      >
        <div class="node-marker" aria-hidden="true">
          <span class="marker-ring">{{ cnNum(i + 1) }}</span>
        </div>

        <div v-if="isNodeReadable(i)" class="node-card">
          <header class="node-head">
            <p class="node-era">{{ node.era }}</p>
            <p class="node-date">{{ node.dateLabel }}</p>
            <h2 class="node-title">{{ node.title }}</h2>
          </header>
          <p class="node-body">{{ node.body }}</p>

          <!-- 节点配视频槽：仅在 sceneVideos 有值时渲染（无值则完全不出此槽） -->
          <SceneVideo
            v-if="nodeVideoSrc(node.id)"
            class="node-video"
            :src="nodeVideoSrc(node.id)"
            :label="`${node.era} · ${node.title}`"
          />

          <div class="clues">
            <p class="clues-label">线索 · 逐条点开细看</p>
            <button
              v-for="(clue, ci) in node.clues"
              :key="ci"
              type="button"
              class="clue"
              :class="{ 'is-revealed': isRevealed(node.id, ci) }"
              :aria-expanded="isRevealed(node.id, ci)"
              @click="revealClue(i, ci)"
            >
              <span class="clue-row">
                <span class="clue-index">{{ cnNum(ci + 1) }}</span>
                <span class="clue-title">{{ clue.title }}</span>
                <span class="clue-hint">{{ isRevealed(node.id, ci) ? '已阅' : '展开' }}</span>
              </span>
              <span class="clue-detail">
                <span class="clue-text">{{ clue.text }}</span>
                <span class="clue-stamp" aria-hidden="true">已阅</span>
              </span>
            </button>
            <p v-if="allCluesRevealed(node)" class="clues-done">
              {{ i + 1 < nodes.length ? '本段线索已阅毕，下一段已解锁。' : '全卷线索已阅毕。' }}
            </p>
            <p v-else class="clues-tip">尚有 {{ node.clues.length - revealedCount(node) }} 条线索未阅。</p>
          </div>
        </div>

        <div v-else class="node-card node-card--sealed">
          <span class="seal" aria-hidden="true">封</span>
          <p class="sealed-title">此段封缄</p>
          <p class="sealed-hint">阅毕上一段全部线索，此段自会展开。</p>
          <span class="sealed-num" aria-hidden="true">{{ cnNum(i + 1) }}</span>
        </div>
      </article>

      <footer class="endcap">
        <span class="seal seal--end" aria-hidden="true">{{ allDone ? '终' : '续' }}</span>
        <p class="endcap-line">全卷 {{ nodes.length }} 段 · 已解锁 {{ unlockedCount }} 段</p>
        <button type="button" class="reset-btn" @click="resetTimeline">重新封缄 · 再读一遍</button>
      </footer>
    </section>

    <transition name="toast">
      <p v-if="toastText" class="toast" role="status">{{ toastText }}</p>
    </transition>
  </main>
</template>

<style scoped>
.timeline-page {
  min-height: 100vh;
  background:
    radial-gradient(1200px 600px at 50% -8%, rgba(166, 128, 45, 0.1), transparent 70%),
    radial-gradient(900px 500px at 88% 108%, rgba(47, 93, 98, 0.08), transparent 70%),
    radial-gradient(700px 400px at 8% 60%, rgba(176, 58, 46, 0.04), transparent 70%),
    var(--paper);
}

/* 宣纸纹理：本地 SVG 噪点，无网络资源 */
.grain {
  position: fixed;
  inset: 0;
  z-index: 90;
  pointer-events: none;
  opacity: 0.05;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/></filter><rect width='180' height='180' filter='url(%23n)'/></svg>");
}

/* ===== 卷首 ===== */
.hero {
  position: relative;
  min-height: 92vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 120px 24px 80px;
  overflow: hidden;
}

.hero-eyebrow {
  margin: 0 0 20px;
  color: var(--gold);
  font-size: 13px;
  letter-spacing: 0.5em;
  text-indent: 0.5em;
}

.hero-title {
  margin: 0;
  font-size: clamp(44px, 8vw, 84px);
  font-weight: 600;
  letter-spacing: 0.16em;
  text-indent: 0.16em;
}

.hero-rule {
  position: relative;
  width: 72px;
  height: 2px;
  margin: 32px 0 24px;
  background: var(--seal);
}

.hero-rule::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 8px;
  height: 8px;
  background: var(--seal);
  transform: translate(-50%, -50%) rotate(45deg);
}

.hero-sub {
  max-width: 560px;
  margin: 0;
  color: var(--ink-soft);
  font-size: 16px;
  line-height: 2;
}

.hero-side {
  position: absolute;
  right: 4vw;
  top: 50%;
  transform: translateY(-50%);
  writing-mode: vertical-rl;
  font-size: clamp(20px, 3vw, 34px);
  font-weight: 600;
  letter-spacing: 0.6em;
  color: rgba(31, 27, 22, 0.07);
  user-select: none;
  pointer-events: none;
}

.hero-scroll {
  display: grid;
  justify-items: center;
  gap: 12px;
  margin-top: 56px;
  padding: 0;
  background: none;
  border: none;
  color: var(--ink-faint);
  font-size: 13px;
  letter-spacing: 0.3em;
  text-indent: 0.3em;
}

.hero-scroll:focus-visible {
  outline: 2px solid var(--seal);
  outline-offset: 4px;
}

.hero-scroll-line {
  position: relative;
  width: 1px;
  height: 56px;
  overflow: hidden;
  background: var(--line-strong);
}

.hero-scroll-line::after {
  content: '';
  position: absolute;
  left: 0;
  top: -50%;
  width: 100%;
  height: 50%;
  background: var(--seal);
  animation: scroll-drip 1.8s ease-in-out infinite;
}

@keyframes scroll-drip {
  to {
    top: 110%;
  }
}

/* ===== 吸顶进度 ===== */
.progress-bar {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(246, 241, 229, 0.88);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line);
}

.progress-head {
  max-width: 1080px;
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
}

.progress-title {
  font-size: 15px;
  letter-spacing: 0.2em;
  color: var(--ink-soft);
}

.progress-count {
  font-size: 14px;
  letter-spacing: 0.12em;
  color: var(--seal);
}

.progress-track {
  height: 2px;
  background: var(--line);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(to right, var(--gold), var(--seal));
  transition: width 0.4s cubic-bezier(0.22, 0.61, 0.36, 1);
}

/* ===== 时间线主体 ===== */
.timeline {
  position: relative;
  max-width: 1080px;
  margin: 0 auto;
  padding: 24px 24px 120px;
}

.axis {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 1px;
  transform: translateX(-50%);
  background: linear-gradient(
    to bottom,
    transparent,
    var(--line-strong) 6%,
    var(--line-strong) 94%,
    transparent
  );
}

.node {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 72px;
  padding: 56px 0;
  scroll-margin-top: 90px;
}

.node--left .node-card {
  grid-column: 1;
  grid-row: 1;
}

.node--right .node-card {
  grid-column: 2;
  grid-row: 1;
}

.node-marker {
  position: absolute;
  top: 40px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
}

.marker-ring {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1.5px solid var(--accent);
  background: var(--paper);
  color: var(--accent);
  font-size: 15px;
  transition:
    background 0.3s ease,
    color 0.3s ease,
    box-shadow 0.3s ease;
}

.node.is-frontier .marker-ring {
  background: var(--accent);
  color: var(--paper);
  box-shadow: 0 0 0 5px color-mix(in srgb, var(--accent) 16%, transparent);
}

.node.is-locked .marker-ring {
  border-color: var(--line-strong);
  color: var(--ink-faint);
  background: transparent;
}

.node.is-new .marker-ring {
  animation: marker-pulse 0.9s ease-out 2;
}

@keyframes marker-pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--accent) 45%, transparent);
  }
  100% {
    box-shadow: 0 0 0 18px transparent;
  }
}

.node.is-new .node-card {
  animation: card-flash 2.4s ease-out;
}

@keyframes card-flash {
  0%,
  30% {
    border-color: var(--seal);
    box-shadow:
      0 0 0 4px rgba(176, 58, 46, 0.12),
      var(--shadow-soft);
  }
  100% {
    border-color: var(--line);
    box-shadow: var(--shadow-soft);
  }
}

/* ===== 节点卡片 ===== */
.node-card {
  position: relative;
  padding: 32px 36px;
  background: rgba(255, 253, 247, 0.82);
  border: 1px solid var(--line);
  border-radius: 4px;
  box-shadow: var(--shadow-soft);
  transition:
    border-color 0.3s ease,
    box-shadow 0.3s ease;
}

.node-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 36px;
  right: 36px;
  height: 2px;
  background: linear-gradient(to right, var(--accent), transparent 60%);
  opacity: 0.7;
}

.node-era {
  margin: 0;
  color: var(--seal);
  font-size: 14px;
  letter-spacing: 0.35em;
}

.node-date {
  margin: 8px 0 0;
  color: var(--ink-faint);
  font-size: 13px;
  letter-spacing: 0.18em;
}

.node-title {
  margin: 14px 0 0;
  font-size: 30px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.node-body {
  margin: 18px 0 0;
  color: var(--ink-soft);
  font-size: 16.5px;
  line-height: 2;
  text-align: justify;
}

/* ===== 封缄（未解锁） ===== */
.node-card--sealed {
  display: grid;
  place-items: center;
  gap: 10px;
  padding: 48px 32px;
  background: rgba(236, 227, 207, 0.5);
  border: 1px dashed var(--line-strong);
  box-shadow: none;
  text-align: center;
}

.node-card--sealed::before {
  display: none;
}

.seal {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  background: var(--seal);
  color: #f9f4e8;
  font-size: 30px;
  font-weight: 600;
  border-radius: 5px;
  transform: rotate(-7deg);
  box-shadow:
    inset 0 0 0 2px rgba(249, 244, 232, 0.4),
    inset 0 0 12px rgba(31, 27, 22, 0.25),
    0 3px 8px rgba(176, 58, 46, 0.25);
  opacity: 0.94;
}

.sealed-title {
  margin: 0;
  color: var(--ink-faint);
  font-size: 15px;
  letter-spacing: 0.4em;
  text-indent: 0.4em;
}

.sealed-hint {
  margin: 0;
  color: var(--ink-faint);
  font-size: 13px;
  opacity: 0.8;
}

.sealed-num {
  position: absolute;
  right: 18px;
  bottom: 4px;
  font-size: 84px;
  font-weight: 600;
  line-height: 1;
  color: rgba(31, 27, 22, 0.05);
  pointer-events: none;
}

/* ===== 节点配视频槽（卡片本体样式在 SceneVideo 内） ===== */
.node-card .node-video {
  margin: 20px 0 0;
}

/* ===== 线索卡 ===== */
.clues {
  display: grid;
  gap: 10px;
  margin-top: 26px;
  padding-top: 18px;
  border-top: 1px solid var(--line);
}

.clues-label {
  margin: 0;
  color: var(--ink-faint);
  font-size: 13px;
  letter-spacing: 0.25em;
}

.clue {
  display: grid;
  grid-template-rows: auto 0fr;
  width: 100%;
  padding: 0;
  background: transparent;
  border: 1px solid var(--line);
  border-radius: 3px;
  color: inherit;
  font: inherit;
  text-align: left;
  transition:
    grid-template-rows 0.38s cubic-bezier(0.22, 0.61, 0.36, 1),
    border-color 0.25s ease,
    background 0.25s ease;
}

.clue:not(.is-revealed):hover {
  border-color: var(--line-strong);
  background: rgba(255, 253, 247, 0.6);
}

.clue:focus-visible {
  outline: 2px solid var(--seal);
  outline-offset: 2px;
}

.clue.is-revealed {
  grid-template-rows: auto 1fr;
  border-color: color-mix(in srgb, var(--seal) 40%, transparent);
}

.clue-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
}

.clue-index {
  display: grid;
  place-items: center;
  flex: none;
  width: 26px;
  height: 26px;
  border: 1px solid var(--line-strong);
  border-radius: 3px;
  color: var(--ink-soft);
  font-size: 13px;
  transition:
    border-color 0.25s ease,
    color 0.25s ease;
}

.clue.is-revealed .clue-index {
  border-color: var(--seal);
  color: var(--seal);
}

.clue-title {
  font-size: 15px;
  letter-spacing: 0.06em;
}

.clue-hint {
  margin-left: auto;
  color: var(--ink-faint);
  font-size: 12px;
  letter-spacing: 0.2em;
  transition: color 0.25s ease;
}

.clue.is-revealed .clue-hint {
  color: var(--seal);
}

.clue-detail {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 0 16px 14px;
  overflow: hidden;
  opacity: 0;
  transform: translateY(8px);
  transition:
    opacity 0.3s ease 0.12s,
    transform 0.3s ease 0.12s;
}

.clue.is-revealed .clue-detail {
  opacity: 1;
  transform: translateY(0);
}

.clue-text {
  flex: 1;
  color: var(--ink-soft);
  font-size: 14.5px;
  line-height: 1.9;
}

.clue-stamp {
  display: grid;
  place-items: center;
  flex: none;
  width: 44px;
  height: 44px;
  border: 1.5px solid var(--seal);
  border-radius: 4px;
  color: var(--seal);
  font-size: 15px;
  letter-spacing: 0.1em;
  opacity: 0;
  transform: rotate(-6deg) scale(1.6);
  transition:
    transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1) 0.22s,
    opacity 0.2s ease 0.22s;
}

.clue.is-revealed .clue-stamp {
  opacity: 0.95;
  transform: rotate(-6deg) scale(1);
}

.clues-done {
  margin: 4px 0 0;
  color: var(--jade);
  font-size: 13px;
  letter-spacing: 0.1em;
}

.clues-tip {
  margin: 4px 0 0;
  color: var(--ink-faint);
  font-size: 13px;
  letter-spacing: 0.08em;
}

/* ===== 卷终 ===== */
.endcap {
  display: grid;
  justify-items: center;
  gap: 16px;
  padding: 40px 0 0;
  text-align: center;
}

.seal--end {
  width: 64px;
  height: 64px;
  font-size: 32px;
}

.endcap-line {
  margin: 0;
  color: var(--ink-faint);
  font-size: 14px;
  letter-spacing: 0.25em;
}

.reset-btn {
  padding: 10px 22px;
  background: transparent;
  border: 1px solid var(--line-strong);
  border-radius: 3px;
  color: var(--ink-soft);
  font: inherit;
  font-size: 14px;
  letter-spacing: 0.15em;
  transition:
    border-color 0.25s ease,
    color 0.25s ease;
}

.reset-btn:hover {
  border-color: var(--seal);
  color: var(--seal);
}

.reset-btn:focus-visible {
  outline: 2px solid var(--seal);
  outline-offset: 2px;
}

/* ===== 提示条 ===== */
.toast {
  position: fixed;
  left: 50%;
  bottom: 40px;
  z-index: 100;
  transform: translateX(-50%);
  margin: 0;
  padding: 12px 24px;
  background: var(--ink);
  border-radius: 4px;
  box-shadow: var(--shadow-soft);
  color: var(--paper);
  font-size: 14px;
  letter-spacing: 0.1em;
  white-space: nowrap;
}

.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(12px);
}

/* ===== 移动端：单列 + 左侧轴 ===== */
@media (max-width: 719px) {
  .timeline {
    padding: 8px 16px 80px;
  }

  .axis {
    left: 26px;
    transform: none;
  }

  .node {
    grid-template-columns: 1fr;
    padding: 40px 0 40px 56px;
  }

  .node--left .node-card,
  .node--right .node-card {
    grid-column: 1;
  }

  .node-marker {
    left: 26px;
    top: 44px;
    transform: none;
  }

  .marker-ring {
    width: 34px;
    height: 34px;
    font-size: 13px;
  }

  .node-card {
    padding: 24px 22px;
  }

  .node-card::before {
    left: 22px;
    right: 22px;
  }

  .node-title {
    font-size: 24px;
  }

  .node-body {
    font-size: 16px;
  }

  .hero-side {
    display: none;
  }

  .progress-head {
    padding: 12px 16px;
  }
}

/* ===== 减少动态 ===== */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
