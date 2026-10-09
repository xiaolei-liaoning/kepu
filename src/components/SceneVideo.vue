<script setup lang="ts">
/**
 * 镜头视频卡：封面卡 + 点按在位播放，无源/加载失败时安静降级。
 *
 * 状态机（同实例，无重新挂载）：
 *   idle（封面）→ @loadedmetadata 首帧入位（preload="auto" 保证渲染）
 *                → 点按 play() 进 playing（原生 controls）
 *   failed（视频 404 等 @error / 无 src）→ 安静占位，绝不露黑框假播放器。
 *
 * 用法：
 *   <SceneVideo :src="sceneVideoSrc(i) ? src : undefined" />
 * src 缺省时直接渲染占位（culture 无视频幕）；
 * src 有值但文件加载失败时 @error 自动降级到同一占位（批量出片未完成）。
 */
import { ref } from 'vue'

const props = defineProps<{
  /** 视频路径；undefined 表示此幕/节点无配视频，直接渲染安静占位 */
  src?: string
  /** 无障碍标签，如「节气卷·第一幕」 */
  label?: string
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
/** 首帧是否已入位（loadedmetadata 后）；未入位时封面盖层保持可见 */
const ready = ref(false)
/** 是否已进入播放态（原生 controls 接管） */
const playing = ref(false)
/** 加载失败（404 等）→ 卡片内降级到静候占位，绝不露黑框假播放器 */
const failed = ref(false)

function start(): void {
  const el = videoRef.value
  if (!el || !ready.value) return
  void el.play()
  playing.value = true
}

function onMeta(): void {
  ready.value = true
  failed.value = false
}

function onError(): void {
  failed.value = true
  ready.value = false
  playing.value = false
}
</script>

<template>
  <!-- 安静占位：无源或加载失败 -->
  <div v-if="!src || failed" class="vcard vcard--placeholder">
    <p class="vcard-note">本段影像 · 筹备中</p>
    <span class="vcard-mark" aria-hidden="true">影</span>
  </div>

  <!-- 封面卡 + 在位播放 -->
  <div v-else class="vcard">
    <video
      ref="videoRef"
      class="vcard-video"
      :src="src"
      :aria-label="label"
      controls
      muted
      loop
      playsinline
      preload="auto"
      @loadedmetadata="onMeta"
      @error="onError"
      @play="playing = true"
      @pause="playing = false"
    ></video>

    <!-- 封面盖层：未进播放态且首帧已入位时呈现（含首帧缩略） -->
    <div
      v-if="!playing"
      class="vcard-cover"
      :class="{ 'vcard-cover--idle': !ready }"
      role="button"
      tabindex="0"
      :aria-label="`播放${label ?? '视频'}`"
      @click="start"
      @keydown.enter.prevent="start"
      @keydown.space.prevent="start"
    >
      <span class="vcard-seal" aria-hidden="true">映</span>
      <span class="vcard-hint">点按 · 观影像</span>
      <!-- 播放暗示：极简三角（44px 起，触屏友好） -->
      <span class="vcard-play" aria-hidden="true">
        <svg viewBox="0 0 24 24" class="vcard-play-svg">
          <path d="M8 5.5v13l11-6.5z" fill="currentColor" />
        </svg>
      </span>
    </div>
  </div>
</template>

<style scoped>
/* 宣纸卡框：与 lens-video 既有装裱一致（描边 + 衬纸）；顶距交给使用方（.lens-video / .node-video 定位） */
.vcard {
  position: relative;
  padding: 8px;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  background: rgba(255, 253, 247, 0.75);
  overflow: hidden;
}

/* ---- 占位（加载失败）：卡框内静候面 + 角落「影」字静印 ---- */

.vcard--placeholder {
  display: grid;
  place-items: center;
  min-height: 116px;
  background:
    repeating-linear-gradient(0deg, transparent 0 3px, rgba(31, 27, 22, 0.014) 3px 4px),
    rgba(255, 253, 247, 0.75);
}

.vcard-note {
  margin: 0;
  font-size: 14px;
  letter-spacing: 0.3em;
  text-indent: 0.3em;
  color: var(--ink-faint);
}

/* 「影」字静印，呼应卷面的「封」印语言 */
.vcard-mark {
  position: absolute;
  right: 14px;
  bottom: 4px;
  font-size: 54px;
  line-height: 1;
  color: rgba(31, 27, 22, 0.06);
  pointer-events: none;
}

/* ---- 封面卡 + 播放 ---- */

.vcard-video {
  display: block;
  width: 100%;
  height: auto;
  max-height: 360px;
  border-radius: 2px;
  background: #14110c;
}

/* 封面盖层：未播放时覆盖原生控件，避免双击/误触露控件条 */
.vcard-cover {
  position: absolute;
  inset: 8px;
  display: grid;
  place-items: center;
  background: rgba(20, 17, 12, 0.28);
  cursor: pointer;
  border-radius: 2px;
  transition: background 0.3s ease;
}

/* 首帧尚未入位：盖一层宣纸底的静候面，绝不露黑框 */
.vcard-cover--idle {
  background:
    repeating-linear-gradient(0deg, transparent 0 3px, rgba(31, 27, 22, 0.02) 3px 4px),
    rgba(246, 241, 229, 0.96);
}

.vcard-cover:hover {
  background: rgba(20, 17, 12, 0.18);
}

.vcard-cover--idle:hover {
  background:
    repeating-linear-gradient(0deg, transparent 0 3px, rgba(31, 27, 22, 0.02) 3px 4px),
    rgba(246, 241, 229, 0.92);
}

.vcard-cover:focus-visible {
  outline: 2px solid var(--seal);
  outline-offset: -2px;
}

/* 角落「映」字小印 */
.vcard-seal {
  position: absolute;
  top: 10px;
  right: 10px;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid rgba(176, 58, 46, 0.55);
  border-radius: 3px;
  background: rgba(246, 241, 229, 0.82);
  color: var(--seal);
  font-size: 14px;
  transform: rotate(-4deg);
}

.vcard-cover--idle .vcard-seal {
  opacity: 0.55;
}

/* 中央播放暗示：极简三角（≥44px 触屏目标） */
.vcard-play {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border: 1px solid var(--line-strong);
  border-radius: 50%;
  background: rgba(246, 241, 229, 0.9);
  color: var(--ink);
  box-shadow: var(--shadow-soft);
  transition: transform 0.25s ease, background 0.25s ease;
}

.vcard-play-svg {
  width: 22px;
  height: 22px;
}

.vcard-cover:hover .vcard-play {
  transform: scale(1.06);
  background: var(--paper);
}

.vcard-hint {
  position: absolute;
  bottom: 10px;
  left: 14px;
  font-size: 12px;
  letter-spacing: 0.28em;
  text-indent: 0.28em;
  color: rgba(246, 241, 229, 0.92);
  text-shadow: 0 1px 3px rgba(31, 27, 22, 0.6);
}

.vcard-cover--idle .vcard-hint {
  color: var(--ink-faint);
  text-shadow: none;
}

/* 减弱动效 */
@media (prefers-reduced-motion: reduce) {
  .vcard-cover,
  .vcard-play {
    transition: none;
  }
}
</style>
