/**
 * 幕级配视频表（含时间线视频表）。
 * 本文件由 scripts/batch-gen-videos.mjs 自动维护，手工条目会被正则解析保留。
 * 文化画卷 key: `${scrollId}-${sceneIndex}`（sceneIndex 从 0 起）；时间线 key: `t-${nodeId}`。
 * 视频文件放 public/videos/，路径以 / 开头（构建后原样拷到 dist 根）。
 */
export const sceneVideos: Record<string, string> = {
  '5-1': '/videos/celadon-porcelain.mp4',
  '1-0': '/videos/scroll1-scene0.mp4',
  '1-1': '/videos/scroll1-scene1.mp4',
  '1-3': '/videos/scroll1-scene3.mp4',
}

export function sceneVideoKey(scrollId: number, sceneIndex: number): string {
  return `${scrollId}-${sceneIndex}`
}

export function timelineVideoKey(nodeId: number): string {
  return `t-${nodeId}`
}
