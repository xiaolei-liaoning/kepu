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
  '1-2': '/videos/scroll1-scene2.mp4',
  '2-0': '/videos/scroll2-scene0.mp4',
  '2-1': '/videos/scroll2-scene1.mp4',
  '2-2': '/videos/scroll2-scene2.mp4',
  '2-3': '/videos/scroll2-scene3.mp4',
  '3-0': '/videos/scroll3-scene0.mp4',
  '3-1': '/videos/scroll3-scene1.mp4',
  '3-2': '/videos/scroll3-scene2.mp4',
  '3-3': '/videos/scroll3-scene3.mp4',
  '4-0': '/videos/scroll4-scene0.mp4',
  '4-1': '/videos/scroll4-scene1.mp4',
  '4-2': '/videos/scroll4-scene2.mp4',
  '4-3': '/videos/scroll4-scene3.mp4',
  '5-0': '/videos/scroll5-scene0.mp4',
  '5-2': '/videos/scroll5-scene2.mp4',
  '5-3': '/videos/scroll5-scene3.mp4',
}

export function sceneVideoKey(scrollId: number, sceneIndex: number): string {
  return `${scrollId}-${sceneIndex}`
}

export function timelineVideoKey(nodeId: number): string {
  return `t-${nodeId}`
}
