#!/usr/bin/env node
/**
 * 批量生成 Agnes 免费视频（agnes-video-2.5-flash）并回写 src/data/videos.ts。
 *
 * 幂等可重跑：启动时解析 videos.ts 现有条目，已完成的 key 自动跳过。
 * 免费档限制：提交间隔 >=70s（1 RPM）；429/503（video_queue_full）退避 180s。
 * 并发 2；单任务轮询上限 50 分钟；单任务最多尝试 2 次。
 *
 * 运行：nohup node scripts/batch-gen-videos.mjs >> /tmp/batch-video.log 2>&1 &
 */
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const BASE = 'https://apihub.agnes-ai.com/v1'
const MODEL = 'agnes-video-2.5-flash'
const VIDEOS_TS = path.join(ROOT, 'src/data/videos.ts')
const PUBLIC_DIR = path.join(ROOT, 'public/videos')
const SUBMIT_GAP_MS = 70_000       // 免费档 1 RPM
const RETRY_BACKOFF_MS = 180_000   // 429/503 退避
const MAX_SUBMIT_TRIES = 20          // 队列拥堵常持续 30+ 分钟，按 180s 退避撑 ~1 小时
const POLL_INTERVAL_MS = 40_000
const MAX_POLLS = 75               // ~50 分钟
const CONCURRENCY = 2
const MAX_JOB_ATTEMPTS = 2

function log(...args) {
  console.log(`[${new Date().toISOString().slice(11, 19)}]`, ...args)
}

function loadApiKey() {
  if (process.env.AGNES_API_KEY) return process.env.AGNES_API_KEY
  const cfgPath = path.join(os.homedir(), '.config/opencode/opencode.json')
  try {
    const raw = JSON.parse(fs.readFileSync(cfgPath, 'utf8'))
    const hit = JSON.stringify(raw).match(/"[^"]*[Aa][Gg][Nn][Ee][Ss][^"]*"\s*:\s*"([^"]+)"/)
    if (hit) return hit[1]
  } catch { /* fallthrough */ }
  throw new Error('AGNES_API_KEY not found in env or opencode config')
}

function parseExistingVideos() {
  const src = fs.readFileSync(VIDEOS_TS, 'utf8')
  const map = new Map()
  for (const [, key, val] of src.matchAll(/'([^']+)':\s*'([^']+)'/g)) map.set(key, val)
  return map
}

function rewriteVideosTs(map) {
  const entries = [...map.entries()].map(([k, v]) => `  '${k}': '${v}',`).join('\n')
  const content = `/**
 * 幕级配视频表（含时间线视频表）。
 * 本文件由 scripts/batch-gen-videos.mjs 自动维护，手工条目会被正则解析保留。
 * 文化画卷 key: \`\${scrollId}-\${sceneIndex}\`（sceneIndex 从 0 起）；时间线 key: \`t-\${nodeId}\`。
 * 视频文件放 public/videos/，路径以 / 开头（构建后原样拷到 dist 根）。
 */
export const sceneVideos: Record<string, string> = {
${entries}
}

export function sceneVideoKey(scrollId: number, sceneIndex: number): string {
  return \`\${scrollId}-\${sceneIndex}\`
}

export function timelineVideoKey(nodeId: number): string {
  return \`t-\${nodeId}\`
}
`
  const tmp = VIDEOS_TS + '.tmp'
  fs.writeFileSync(tmp, content)
  fs.renameSync(tmp, VIDEOS_TS)   // 原子替换，避免并发读到半截
}

function findHttpUrl(obj, wantKey = 'url') {
  if (obj && typeof obj === 'object') {
    if (typeof obj[wantKey] === 'string' && obj[wantKey].startsWith('http')) return obj[wantKey]
    for (const v of Object.values(obj)) {
      const r = findHttpUrl(v, wantKey)
      if (r) return r
    }
  }
  return null
}

function findString(obj, wantKey) {
  if (obj && typeof obj === 'object') {
    if (typeof obj[wantKey] === 'string' && obj[wantKey]) return obj[wantKey]
    for (const v of Object.values(obj)) {
      const r = findString(v, wantKey)
      if (r) return r
    }
  }
  return null
}

async function api(pathname, opts = {}) {
  const res = await fetch(`${BASE}${pathname}`, {
    ...opts,
    headers: {
      Authorization: `Bearer ${KEY}`,
      'Content-Type': 'application/json',
      ...(opts.headers || {}),
    },
  })
  const text = await res.text()
  let body = null
  try { body = JSON.parse(text) } catch { body = { raw: text.slice(0, 400) } }
  return { status: res.status, body }
}

// 全局提交闸门：保证任意两次提交间隔 >= SUBMIT_GAP_MS
let nextSubmitAt = 0
async function submitGate() {
  const now = Date.now()
  const wait = nextSubmitAt - now
  if (wait > 0) await new Promise((r) => setTimeout(r, wait))
  nextSubmitAt = Date.now() + SUBMIT_GAP_MS
}

async function submitVideo(prompt) {
  const payload = {
    model: MODEL,
    mode: 'text',
    prompt,
    seconds: '4',
    size: '720P',
    aspect_ratio: '16:9',
  }
  for (let i = 1; i <= MAX_SUBMIT_TRIES; i++) {
    await submitGate()
    let { status, body } = { status: 0, body: null }
    try {
      ;({ status, body } = await api('/videos', { method: 'POST', body: JSON.stringify(payload) }))
    } catch (e) {
      log(`submit网络错误 try#${i}:`, e.message)
    }
    if (status >= 200 && status < 300) {
      const videoId = findString(body, 'video_id') || findString(body, 'id')
      if (videoId) return videoId
      log('submit 2xx 但无 video_id:', JSON.stringify(body).slice(0, 300))
    } else if (status === 429 || status === 503) {
      log(`submit ${status}（限流/队列满），退避 ${RETRY_BACKOFF_MS / 1000}s  try#${i}/${MAX_SUBMIT_TRIES}`)
    } else {
      log(`submit HTTP ${status} try#${i}:`, JSON.stringify(body).slice(0, 300))
    }
    if (i < MAX_SUBMIT_TRIES) await new Promise((r) => setTimeout(r, RETRY_BACKOFF_MS))
  }
  throw new Error('submit failed after retries')
}

async function pollUntilDone(videoId) {
  for (let i = 1; i <= MAX_POLLS; i++) {
    let status = 0, body = null
    try {
      ;({ status, body } = await api(`/agnesapi?video_id=${videoId}&model_name=${MODEL}`))
    } catch (e) {
      log(`poll#${i} 网络错误:`, e.message)
    }
    if (status === 429) {
      log(`poll#${i} 429，等 65s`)
      await new Promise((r) => setTimeout(r, 65_000))
      continue
    }
    const st = findString(body, 'status') || 'unknown'
    if (i % 4 === 1) log(`poll#${i} HTTP ${status} status=${st}`)
    if (st === 'completed') {
      const url = findHttpUrl(body)
      if (url) return url
      log('completed 但无 url:', JSON.stringify(body).slice(0, 300))
    }
    if (st === 'failed') throw new Error(`job failed: ${JSON.stringify(body).slice(0, 300)}`)
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS))
  }
  throw new Error('poll timeout (50min)')
}

async function downloadTo(url, absPath) {
  const res = await fetch(url, { redirect: 'follow' })
  if (!res.ok) throw new Error(`download HTTP ${res.status}`)
  const buf = Buffer.from(await res.arrayBuffer())
  if (buf.length < 100_000) throw new Error(`download too small: ${buf.length}B`)
  const tmp = absPath + '.tmp'
  fs.writeFileSync(tmp, buf)
  fs.renameSync(tmp, absPath)
  return buf.length
}

async function runTask(task) {
  for (let attempt = 1; attempt <= MAX_JOB_ATTEMPTS; attempt++) {
    try {
      log(`▶ ${task.key} 开始（attempt ${attempt}）prompt: ${task.prompt.slice(0, 60)}…`)
      const videoId = await submitVideo(task.prompt)
      log(`  ${task.key} video_id=${videoId}`)
      const url = await pollUntilDone(videoId)
      const abs = path.join(ROOT, 'public', task.file)   // task.file = 'videos/xxx.mp4'
      const bytes = await downloadTo(url, abs)
      const map = parseExistingVideos()
      map.set(task.key, `/${task.file}`)
      rewriteVideosTs(map)
      log(`✔ ${task.key} 完成 → /${task.file} (${(bytes / 1024 / 1024).toFixed(1)}MB)`)
      return
    } catch (e) {
      log(`✘ ${task.key} attempt ${attempt} 失败:`, e.message)
      if (attempt < MAX_JOB_ATTEMPTS) await new Promise((r) => setTimeout(r, RETRY_BACKOFF_MS))
      else log(`✘ ${task.key} 放弃（稍后重跑本脚本可自动重试）`)
    }
  }
}

async function buildTasks() {
  const { cultureData } = await import('../src/data/culture.ts')
  const { timelineData } = await import('../src/data/timeline.ts')
  const existing = parseExistingVideos()
  const tasks = []

  for (const scroll of cultureData.scrolls) {
    scroll.scenes.forEach((scene, idx) => {
      const key = `${scroll.id}-${idx}`
      if (existing.has(key)) { log(`跳过已有: ${key}`); return }
      tasks.push({
        key,
        file: `videos/scroll${scroll.id}-scene${idx}.mp4`,
        prompt: String(scene.visual || '').replace(/\s+/g, ' ').trim().slice(0, 900),
      })
    })
  }
  for (const node of timelineData.nodes) {
    const key = `t-${node.id}`
    if (existing.has(key)) { log(`跳过已有: ${key}`); return }
    const art = String(node.artNote || '').replace(/\s+/g, ' ').trim()
    tasks.push({
      key,
      file: `videos/timeline-${node.id}.mp4`,
      prompt: `【${node.era}】${art}。水墨动画风格，纪录片质感，缓慢运镜`.slice(0, 900),
    })
  }
  return tasks.filter((t) => t.prompt.length > 10)
}

const KEY = loadApiKey()

async function main() {
  // 单实例守卫
  const pidFile = '/tmp/batch-gen-videos.pid'
  if (fs.existsSync(pidFile)) {
    const old = Number(fs.readFileSync(pidFile, 'utf8').trim())
    try {
      process.kill(old, 0)
      throw new Error(`already running (pid ${old})`)
    } catch (e) {
      if (e.message.startsWith('already running')) throw e
      // 旧进程已死，继续
    }
  }
  fs.writeFileSync(pidFile, String(process.pid))

  fs.mkdirSync(PUBLIC_DIR, { recursive: true })
  const tasks = await buildTasks()
  log(`共 ${tasks.length} 条待生成，并发 ${CONCURRENCY}，预计 ${Math.ceil(tasks.length / CONCURRENCY) * 6}~${Math.ceil(tasks.length / CONCURRENCY) * 40} 分钟`)

  const queue = [...tasks]
  let active = 0
  await new Promise((resolve) => {
    const kick = () => {
      while (active < CONCURRENCY && queue.length) {
        const task = queue.shift()
        active++
        runTask(task)
          .catch((e) => log(`未捕获异常 ${task.key}:`, e.message))
          .finally(() => {
            active--
            if (!active && !queue.length) resolve()
            else kick()
          })
      }
      if (!active && !queue.length) resolve()
    }
    kick()
  })

  const final = parseExistingVideos()
  log(`全部结束：videos.ts 现有 ${final.size} 条映射`)
  try { fs.unlinkSync(pidFile) } catch { /* noop */ }
}

main().catch((e) => {
  log('FATAL:', e.message)
  process.exit(1)
})
