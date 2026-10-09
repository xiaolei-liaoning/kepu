<script setup lang="ts">
/**
 * 传统文化画卷：选卷 → 阅卷（幕间线索解锁）→ 收尾知识点卡。
 * 进度按画卷 id 保存在 reactive Map 中，离开画卷再返回不丢失。
 */
import { computed, reactive, ref } from 'vue'
import type { CSSProperties } from 'vue'
import { cultureData } from '@/data/culture'
import { sceneVideos, sceneVideoKey } from '@/data/videos'
import type { Scroll } from '@/types'
import SceneVideo from '@/components/SceneVideo.vue'

/* ============================== 类型 ============================== */

/** 一幅画卷的阅读进度 */
interface ScrollProgress {
  /** 已展开到的最高幕下标（幕 i 可读 ⟺ i ≤ unlocked） */
  unlocked: number
  /** 各幕线索是否已揭开 */
  revealed: boolean[]
  /** 各知识点卡是否已盖章 */
  stamped: boolean[]
  /** 收尾知识点卡面板是否已呈现 */
  cardsOpen: boolean
}

/** 画卷配色：在共享宣纸 / 水墨体系内按画卷 id 变化 */
interface ScrollPalette {
  accent: string
  accentDeep: string
  wash: string
  paper: string
  ink: string
}

/* ============================== 配色 ============================== */

/** 按画卷 id 取主题色（节气暖土黄 · 端午青绿 · 书法墨色 · 丝路赭黄 · 瓷器青白） */
const SCROLL_PALETTES: Record<number, ScrollPalette> = {
  1: { accent: '#8a6d2f', accentDeep: '#6b5420', wash: 'rgba(138, 109, 47, 0.10)', paper: '#f3ead3', ink: '#3a2f1a' },
  2: { accent: '#2f5d62', accentDeep: '#1f4245', wash: 'rgba(47, 93, 98, 0.10)', paper: '#edf4ef', ink: '#1e3436' },
  3: { accent: '#2a2521', accentDeep: '#100d0a', wash: 'rgba(31, 27, 22, 0.08)', paper: '#fbf8f0', ink: '#1f1b16' },
  4: { accent: '#9a5b2d', accentDeep: '#7a4520', wash: 'rgba(154, 91, 45, 0.10)', paper: '#f0e2c8', ink: '#4a3018' },
  5: { accent: '#6f9a97', accentDeep: '#527a77', wash: 'rgba(127, 163, 160, 0.12)', paper: '#edf3f0', ink: '#2a3d3b' },
}

/** 未知画卷 id 的兜底配色（共享描金） */
const DEFAULT_PALETTE: ScrollPalette = {
  accent: '#a6802d',
  accentDeep: '#7d5f1f',
  wash: 'rgba(166, 128, 45, 0.10)',
  paper: '#f6f1e5',
  ink: '#1f1b16',
}

const CN_NUMERALS = ['壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖', '拾']

/* ============================== 状态 ============================== */

/** 选卷阶段为 null；阅卷阶段为画卷 id */
const activeScrollId = ref<number | null>(null)

/** 各画卷阅读进度：离开画卷后保留 */
const progress = reactive(new Map<number, ScrollProgress>())
for (const scroll of cultureData.scrolls) {
  progress.set(scroll.id, {
    unlocked: 0,
    revealed: scroll.scenes.map(() => false),
    stamped: scroll.cards.map(() => false),
    cardsOpen: false,
  })
}

/** 「镜头」说明的展开状态（按幕下标） */
const lensOpen = reactive(new Set<number>())

/* ============================== 派生 ============================== */

const activeScroll = computed<Scroll | null>(() =>
  activeScrollId.value === null ? null : (cultureData.scrolls.find((s) => s.id === activeScrollId.value) ?? null),
)

const activeProgress = computed<ScrollProgress | null>(() =>
  activeScrollId.value === null ? null : (progress.get(activeScrollId.value) ?? null),
)

const totalScenes = computed(() => activeScroll.value?.scenes.length ?? 0)

const currentSceneNo = computed(() => {
  if (!activeProgress.value || totalScenes.value === 0) return 0
  return Math.min(activeProgress.value.unlocked + 1, totalScenes.value)
})

const stampedCount = computed(() => activeProgress.value?.stamped.filter(Boolean).length ?? 0)

/* ============================== 方法 ============================== */

function paletteStyle(scroll: Scroll): CSSProperties {
  const p = SCROLL_PALETTES[scroll.id] ?? DEFAULT_PALETTE
  return {
    '--scroll-accent': p.accent,
    '--scroll-accent-deep': p.accentDeep,
    '--scroll-wash': p.wash,
    '--scroll-paper': p.paper,
    '--scroll-ink': p.ink,
  } as CSSProperties
}

function sceneDelay(sceneIndex: number): CSSProperties {
  return { animationDelay: `${Math.min(sceneIndex, 6) * 70}ms` } as CSSProperties
}

/** 当前幕的配视频路径（无则 undefined，镜头区由 SceneVideo 安静占位） */
function sceneVideoSrc(sceneIndex: number): string | undefined {
  if (activeScrollId.value === null) return undefined
  return sceneVideos[sceneVideoKey(activeScrollId.value, sceneIndex)]
}

function coverIndexLabel(id: number): string {
  return CN_NUMERALS[id - 1] ?? String(id)
}

function enterScroll(id: number): void {
  activeScrollId.value = id
}

function exitToPicker(): void {
  activeScrollId.value = null
}

function toggleLens(sceneIndex: number): void {
  if (lensOpen.has(sceneIndex)) {
    lensOpen.delete(sceneIndex)
  } else {
    lensOpen.add(sceneIndex)
  }
}

/** 揭开幕间线索：非末幕解锁下一幕，末幕呈现收尾知识点卡 */
function revealClue(sceneIndex: number): void {
  if (activeScrollId.value === null || !activeScroll.value) return
  const p = progress.get(activeScrollId.value)
  if (!p || sceneIndex < 0 || sceneIndex >= p.revealed.length || p.revealed[sceneIndex]) return
  p.revealed[sceneIndex] = true
  if (sceneIndex < activeScroll.value.scenes.length - 1) {
    p.unlocked = Math.max(p.unlocked, sceneIndex + 1)
  } else {
    p.cardsOpen = true
  }
}

function toggleStamp(cardIndex: number): void {
  if (activeScrollId.value === null) return
  const p = progress.get(activeScrollId.value)
  if (!p || !p.stamped[cardIndex]) return
  p.stamped[cardIndex] = !p.stamped[cardIndex]
}

function isLastScene(sceneIndex: number): boolean {
  return activeScroll.value !== null && sceneIndex === activeScroll.value.scenes.length - 1
}
</script>

<template>
  <main class="culture">
    <!-- ═══════ 第一阶段 · 选卷 ═══════ -->
    <section v-if="activeScroll === null" class="picker" aria-label="选择画卷">
      <header class="picker-head">
        <p class="eyebrow">科普互动体验 · 贰</p>
        <h1>{{ cultureData.title }}</h1>
        <p class="sub">读一幕，寻一线，幕幕相扣，直至收尾知识点卡。</p>
      </header>

      <div class="scroll-grid">
        <button
          v-for="scroll in cultureData.scrolls"
          :key="scroll.id"
          type="button"
          class="cover"
          :style="paletteStyle(scroll)"
          @click="enterScroll(scroll.id)"
        >
          <span class="cover-roller cover-roller--top" aria-hidden="true"></span>
          <span class="cover-seal">{{ coverIndexLabel(scroll.id) }}</span>
          <span class="cover-title">{{ scroll.name }}</span>
          <span class="cover-theme">{{ scroll.theme }}</span>
          <span class="cover-style">{{ scroll.artStyle }}</span>
          <span class="cover-progress">
            幕 {{ Math.min((progress.get(scroll.id)?.unlocked ?? 0) + 1, scroll.scenes.length) }}/{{
              scroll.scenes.length
            }}
            · 知识卡 {{ progress.get(scroll.id)?.stamped.filter(Boolean).length ?? 0 }}/{{ scroll.cards.length }}
          </span>
          <span class="cover-go">展卷 →</span>
          <span class="cover-roller cover-roller--bottom" aria-hidden="true"></span>
        </button>
      </div>

      <router-link class="home-link" to="/">← 返回首页</router-link>
    </section>

    <!-- ═══════ 第二阶段 · 阅卷 ═══════ -->
    <section
      v-else-if="activeScroll && activeProgress"
      class="reading"
      :style="paletteStyle(activeScroll)"
      aria-label="阅读画卷"
    >
      <header class="reader-bar">
        <button type="button" class="bar-btn" @click="exitToPicker">← 选卷</button>
        <div class="bar-title">
          <h2>{{ activeScroll.name }}</h2>
          <p>幕 {{ currentSceneNo }}/{{ totalScenes }} · 知识卡 {{ stampedCount }}/{{ activeScroll.cards.length }}</p>
        </div>
        <router-link class="bar-btn" to="/">首页</router-link>
      </header>

      <div class="scroll-paper">
        <header class="scroll-head">
          <p class="scroll-theme">{{ activeScroll.theme }}</p>
          <h3 class="scroll-name">{{ activeScroll.name }}</h3>
          <p class="scroll-style">{{ activeScroll.artStyle }}</p>
        </header>

        <article v-for="(scene, sceneIndex) in activeScroll.scenes" :key="scene.act" class="scene">
          <!-- 已展开的幕 -->
          <div v-if="sceneIndex <= activeProgress.unlocked" class="scene-open scene-unroll" :style="sceneDelay(sceneIndex)">
            <header class="scene-head">
              <span class="scene-act">{{ scene.act }}</span>
              <h4 class="scene-name">{{ scene.name }}</h4>
            </header>

            <p class="scene-story">{{ scene.story }}</p>

            <button
              type="button"
              class="lens-toggle"
              :aria-expanded="lensOpen.has(sceneIndex)"
              @click="toggleLens(sceneIndex)"
            >
              {{ lensOpen.has(sceneIndex) ? '收起镜头' : '镜头' }}
            </button>
            <p v-if="lensOpen.has(sceneIndex)" class="scene-lens">{{ scene.visual }}</p>
            <!-- 镜头区：无配视频 → 卡片内安静占位；有配视频 → 封面卡（点按在位播放） -->
            <SceneVideo
              v-if="lensOpen.has(sceneIndex)"
              class="lens-video"
              :src="sceneVideoSrc(sceneIndex)"
              :label="`${activeScroll.name} · ${scene.name}`"
            />

            <div class="clue">
              <button
                v-if="!activeProgress.revealed[sceneIndex]"
                type="button"
                class="clue-btn"
                :aria-expanded="activeProgress.revealed[sceneIndex]"
                @click="revealClue(sceneIndex)"
              >
                寻一线索
              </button>
              <div v-else class="clue-revealed">
                <p class="clue-text">{{ scene.clue.text }}</p>
                <p class="clue-points">→ {{ scene.clue.pointsTo }}</p>
              </div>
            </div>

            <p v-if="activeProgress.revealed[sceneIndex] && !isLastScene(sceneIndex)" class="next-hint">
              下一幕已展开
            </p>
          </div>

          <!-- 未展开的幕 -->
          <div v-else class="scene-sealed">
            <span class="sealed-act">{{ scene.act }}</span>
            <span class="sealed-label">此幕未展</span>
          </div>
        </article>

        <!-- 收尾知识点卡 -->
        <section v-if="activeProgress.cardsOpen" class="cards" aria-label="收尾知识点卡">
          <h4 class="cards-title">收尾知识点卡</h4>
          <div class="cards-grid">
            <article
              v-for="(card, cardIndex) in activeScroll.cards"
              :key="card.title"
              class="kcard"
              :class="{ 'kcard--stamped': activeProgress.stamped[cardIndex] }"
              role="button"
              tabindex="0"
              :aria-pressed="activeProgress.stamped[cardIndex]"
              @click="toggleStamp(cardIndex)"
              @keydown.enter.prevent="toggleStamp(cardIndex)"
              @keydown.space.prevent="toggleStamp(cardIndex)"
            >
              <span class="kcard-seal">{{ activeProgress.stamped[cardIndex] ? '已阅' : '待阅' }}</span>
              <h5 class="kcard-title">{{ card.title }}</h5>
              <p class="kcard-fact">{{ card.fact }}</p>
            </article>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>

<style scoped>
/* ============================== 基底 ============================== */

.culture {
  min-height: 100vh;
  background:
    radial-gradient(1000px 420px at 50% -8%, rgba(166, 128, 45, 0.1), transparent 70%),
    var(--paper);
}

/* ============================== 选卷 ============================== */

.picker {
  max-width: 1060px;
  margin: 0 auto;
  padding: 72px 24px 56px;
}

.picker-head {
  text-align: center;
}

.eyebrow {
  margin: 0 0 14px;
  font-size: 13px;
  letter-spacing: 0.5em;
  text-indent: 0.5em;
  color: var(--gold);
}

.picker-head h1 {
  margin: 0;
  font-size: clamp(34px, 6vw, 54px);
  font-weight: 600;
  letter-spacing: 0.18em;
  text-indent: 0.18em;
}

.sub {
  margin: 16px 0 0;
  font-size: 15px;
  line-height: 1.9;
  color: var(--ink-soft);
}

.scroll-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
  gap: 28px;
  margin-top: 52px;
}

/* ---- 卷封面（挂轴式） ---- */

.cover {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 58px 26px 50px;
  background: var(--scroll-paper);
  border: 1px solid var(--line);
  border-radius: 6px;
  box-shadow: var(--shadow-soft);
  cursor: pointer;
  text-align: center;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.cover:hover {
  transform: translateY(-6px);
  box-shadow: 0 20px 48px rgba(31, 27, 22, 0.2);
}

.cover-roller {
  position: absolute;
  left: 10px;
  right: 10px;
  height: 9px;
  border-radius: 5px;
  background: linear-gradient(180deg, #7a5a30 0%, #4a3018 100%);
  box-shadow: 0 1px 2px rgba(31, 27, 22, 0.25);
}

.cover-roller--top {
  top: -4px;
}

.cover-roller--bottom {
  bottom: -4px;
}

.cover-seal {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border: 1.5px solid var(--seal);
  border-radius: 50%;
  color: var(--seal);
  font-size: 20px;
  transform: rotate(-4deg);
}

.cover-title {
  writing-mode: vertical-rl;
  font-size: 30px;
  font-weight: 600;
  letter-spacing: 0.28em;
  color: var(--scroll-ink);
}

.cover-theme {
  font-size: 14px;
  letter-spacing: 0.2em;
  text-indent: 0.2em;
  color: var(--scroll-accent-deep);
}

.cover-style {
  font-size: 12px;
  line-height: 1.8;
  color: var(--ink-faint);
  max-width: 26em;
}

.cover-progress {
  width: 100%;
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
  font-size: 12px;
  letter-spacing: 0.12em;
  color: var(--ink-soft);
}

.cover-go {
  font-size: 13px;
  letter-spacing: 0.2em;
  color: var(--seal);
}

.home-link {
  display: block;
  width: fit-content;
  margin: 44px auto 0;
  font-size: 13px;
  letter-spacing: 0.2em;
  color: var(--ink-faint);
  transition: color 0.25s ease;
}

.home-link:hover {
  color: var(--seal);
}

/* ============================== 阅卷 ============================== */

.reading {
  min-height: 100vh;
  padding-bottom: 96px;
}

.reader-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  max-width: 880px;
  margin: 0 auto;
  padding: 14px 8px;
  background: rgba(246, 241, 229, 0.88);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line);
}

.bar-btn {
  flex: none;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  background: transparent;
  padding: 7px 14px;
  font-size: 13px;
  letter-spacing: 0.1em;
  color: var(--ink-soft);
  transition: border-color 0.25s ease, color 0.25s ease;
}

.bar-btn:hover {
  border-color: var(--seal);
  color: var(--seal);
}

.bar-title {
  min-width: 0;
  text-align: center;
}

.bar-title h2 {
  margin: 0;
  font-size: 18px;
  letter-spacing: 0.2em;
  text-indent: 0.2em;
  white-space: nowrap;
}

.bar-title p {
  margin: 4px 0 0;
  font-size: 12px;
  letter-spacing: 0.14em;
  color: var(--ink-faint);
}

/* ---- 卷轴纸面 ---- */

.scroll-paper {
  position: relative;
  max-width: 780px;
  margin: 40px auto 0;
  padding: 60px 64px 72px;
  overflow: hidden;
  background:
    repeating-linear-gradient(0deg, transparent 0 3px, rgba(31, 27, 22, 0.012) 3px 4px),
    linear-gradient(180deg, var(--scroll-wash), transparent 180px),
    var(--scroll-paper);
  border: 1px solid var(--line);
  border-radius: 6px;
  box-shadow: var(--shadow-soft);
  animation: unroll 0.4s cubic-bezier(0.22, 0.8, 0.36, 1) both;
}

/* 装裱边线 */
.scroll-paper::before,
.scroll-paper::after {
  content: '';
  position: absolute;
  top: 14px;
  bottom: 14px;
  width: 1px;
  background: var(--line);
}

.scroll-paper::before {
  left: 14px;
}

.scroll-paper::after {
  right: 14px;
}

@keyframes unroll {
  from {
    clip-path: inset(0 100% 0 0);
    opacity: 0.3;
  }
  to {
    clip-path: inset(0 0 0 0);
    opacity: 1;
  }
}

.scroll-head {
  margin-bottom: 12px;
  text-align: center;
}

.scroll-theme {
  margin: 0 0 10px;
  font-size: 13px;
  letter-spacing: 0.4em;
  text-indent: 0.4em;
  color: var(--scroll-accent-deep);
}

.scroll-name {
  margin: 0;
  font-size: clamp(28px, 5vw, 40px);
  letter-spacing: 0.22em;
  text-indent: 0.22em;
  color: var(--scroll-ink);
}

.scroll-style {
  margin: 12px 0 0;
  font-size: 12px;
  letter-spacing: 0.1em;
  color: var(--ink-faint);
}

/* ---- 幕 ---- */

.scene {
  padding: 40px 0 8px;
  border-top: 1px solid var(--line);
}

.scene:first-of-type {
  border-top: none;
}

.scene-unroll {
  animation: scene-in 0.4s cubic-bezier(0.22, 0.8, 0.36, 1) both;
}

@keyframes scene-in {
  from {
    clip-path: inset(0 0 0 100%);
    opacity: 0;
    transform: translateX(14px);
  }
  to {
    clip-path: inset(0 0 0 0);
    opacity: 1;
    transform: translateX(0);
  }
}

.scene-head {
  display: flex;
  align-items: baseline;
  gap: 16px;
}

.scene-act {
  flex: none;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: var(--scroll-accent);
}

.scene-name {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: var(--scroll-ink);
}

.scene-story {
  margin: 20px 0 0;
  max-width: 34em;
  font-size: 17px;
  line-height: 2.1;
  color: var(--scroll-ink);
  text-align: justify;
}

/* 「镜头」说明：从属、可收起 */
.lens-toggle {
  margin-top: 18px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: transparent;
  padding: 5px 16px;
  font-size: 12px;
  letter-spacing: 0.24em;
  text-indent: 0.24em;
  color: var(--ink-faint);
  transition: color 0.25s ease, border-color 0.25s ease;
}

.lens-toggle:hover {
  color: var(--scroll-accent);
  border-color: var(--scroll-accent);
}

.scene-lens {
  margin: 12px 0 0;
  padding: 10px 14px;
  border-left: 2px solid var(--scroll-accent);
  border-radius: 0 4px 4px 0;
  background: var(--scroll-wash);
  font-size: 13px;
  line-height: 1.9;
  color: var(--ink-faint);
  animation: fade-in 0.3s ease both;
}

/* 镜头配视频卡：卡片本体样式在 SceneVideo 内，此处保留顶距与展开动画 */
.lens-video {
  margin-top: 12px;
  animation: fade-in 0.3s ease both;
}

/* ---- 幕间线索 ---- */

.clue {
  margin-top: 26px;
}

.clue-btn {
  border: 1.5px solid var(--scroll-accent);
  border-radius: 4px;
  background: var(--scroll-wash);
  padding: 11px 26px;
  font-size: 14px;
  letter-spacing: 0.28em;
  text-indent: 0.28em;
  color: var(--scroll-accent-deep);
  transition: background 0.25s ease, color 0.25s ease, transform 0.25s ease;
}

.clue-btn:hover {
  background: var(--scroll-accent);
  color: var(--scroll-paper);
}

.clue-btn:active {
  transform: scale(0.97);
}

.clue-revealed {
  border: 1px dashed var(--line-strong);
  border-radius: 4px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.45);
  animation: fade-in 0.35s ease both;
}

.clue-text {
  margin: 0;
  font-size: 15px;
  line-height: 1.9;
  color: var(--ink-soft);
}

.clue-points {
  margin: 8px 0 0;
  font-size: 13px;
  letter-spacing: 0.12em;
  color: var(--scroll-accent);
}

.next-hint {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 26px 0 0;
  font-size: 12px;
  letter-spacing: 0.3em;
  text-indent: 0.3em;
  color: var(--scroll-accent);
}

.next-hint::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--scroll-accent), transparent);
  opacity: 0.5;
}

/* ---- 未展开的幕 ---- */

.scene-sealed {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 26px 0;
}

.sealed-act {
  flex: none;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: var(--ink-faint);
}

.sealed-label {
  flex: none;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 4px 14px;
  font-size: 12px;
  letter-spacing: 0.2em;
  text-indent: 0.2em;
  color: var(--ink-faint);
}

.scene-sealed::after {
  content: '';
  flex: 1;
  height: 1px;
  background: repeating-linear-gradient(90deg, var(--line) 0 6px, transparent 6px 12px);
}

/* ---- 收尾知识点卡 ---- */

.cards {
  margin-top: 44px;
  padding-top: 30px;
  border-top: 2px solid var(--scroll-accent);
  animation: fade-in 0.4s ease both;
}

.cards-title {
  margin: 0;
  font-size: 15px;
  letter-spacing: 0.34em;
  text-indent: 0.34em;
  text-align: center;
  color: var(--scroll-accent-deep);
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 18px;
  margin-top: 26px;
}

.kcard {
  position: relative;
  display: block;
  width: 100%;
  padding: 26px 20px 18px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  cursor: pointer;
  text-align: left;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.kcard:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-soft);
}

.kcard-seal {
  position: absolute;
  top: -12px;
  right: -8px;
  min-width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  padding: 0 6px;
  border: 2px solid var(--seal);
  border-radius: 6px;
  background: var(--paper);
  color: var(--seal);
  font-size: 11px;
  letter-spacing: 0.08em;
  transform: rotate(8deg);
  opacity: 0.3;
  transition: opacity 0.3s ease, background 0.3s ease, color 0.3s ease, transform 0.3s ease;
}

.kcard--stamped .kcard-seal {
  opacity: 1;
  background: var(--seal);
  color: var(--paper);
  transform: rotate(8deg) scale(1.06);
}

.kcard-title {
  margin: 0 0 10px;
  font-size: 16px;
  letter-spacing: 0.12em;
  color: var(--scroll-ink);
}

.kcard-fact {
  margin: 0;
  font-size: 13px;
  line-height: 1.9;
  color: var(--ink-soft);
}

@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ============================== 响应式 ============================== */

@media (max-width: 640px) {
  .picker {
    padding: 48px 16px 40px;
  }

  .scroll-grid {
    grid-template-columns: 1fr;
    gap: 20px;
    margin-top: 36px;
  }

  .cover {
    padding: 48px 20px 44px;
  }

  .cover-title {
    font-size: 26px;
  }

  .reader-bar {
    padding: 10px 4px;
  }

  .bar-title h2 {
    font-size: 15px;
  }

  .bar-title p {
    font-size: 11px;
  }

  .bar-btn {
    padding: 6px 10px;
    font-size: 12px;
  }

  .scroll-paper {
    margin-top: 24px;
    padding: 40px 22px 56px;
  }

  .scroll-paper::before {
    left: 8px;
  }

  .scroll-paper::after {
    right: 8px;
  }

  .scene {
    padding: 30px 0 4px;
  }

  .scene-name {
    font-size: 20px;
  }

  .scene-story {
    font-size: 16px;
  }

  .cards-grid {
    grid-template-columns: 1fr;
  }
}

/* ============================== 减弱动效 ============================== */

@media (prefers-reduced-motion: reduce) {
  .scroll-paper,
  .scene-unroll,
  .scene-lens,
  .lens-video,
  .clue-revealed,
  .cards {
    animation: none;
  }

  .cover,
  .kcard,
  .clue-btn,
  .bar-btn,
  .home-link {
    transition: none;
  }
}
</style>
