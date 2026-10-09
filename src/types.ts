/**
 * 数据契约：docs/脚本/*.md 经转换生成 src/data/*.ts，
 * 视图只依赖本文件中的类型。
 *
 * 固定导出名：
 *   src/data/timeline.ts → export const timelineData: TimelineData
 *   src/data/culture.ts  → export const cultureData: CultureData
 */

/** 时间线的一条线索卡（点开查看后计为“已阅”） */
export interface TimelineClue {
  /** 线索卡标题，如「商鞅变法」 */
  title: string
  /** 线索正文（脚本中箭头右侧的一句话） */
  text: string
}

/** 时间线节点：尧舜 → 现代，共 16 个 */
export interface TimelineNode {
  /** 节点编号 1..16，同时决定解锁顺序 */
  id: number
  /** 所属时代（脚本节点头），如「尧舜禹·禅让时代」 */
  era: string
  /** 年代标注，如「约前2070年前·传说时代」 */
  dateLabel: string
  /** 节点标题（≤10 字） */
  title: string
  /** 科普正文，180–250 字 */
  body: string
  /** 2–3 条线索卡；全部阅毕解锁下一节点 */
  clues: TimelineClue[]
  /** 画面建议：给 UI 的美术/纹样提示，不作为正文展示 */
  artNote: string
}

export interface TimelineData {
  /** 时间线大标题 */
  title: string
  nodes: TimelineNode[]
}

/** 画卷中的一幕线索：文字 + 指向 */
export interface CultureClue {
  /** 线索文字（脚本中箭头左侧） */
  text: string
  /** 指向（脚本中箭头右侧），如「第二幕」或「收尾知识点卡」 */
  pointsTo: string
}

/** 画卷的一幕 */
export interface CultureScene {
  /** 幕序，如「第一幕」 */
  act: string
  /** 幕标题，如「圭表测影」 */
  name: string
  /** 画面描述：给 UI 的镜头/美术提示 */
  visual: string
  /** 旁白故事：观众阅读的正文 */
  story: string
  /** 本幕线索；点开后解锁下一幕，第四幕指向知识点卡 */
  clue: CultureClue
}

/** 收尾知识点卡 */
export interface KnowledgeCard {
  title: string
  fact: string
}

/** 一幅画卷（传统文化叙事），共 5 幅 */
export interface Scroll {
  id: number
  /** 画卷名（脚本标题栏），如「二十四节气」 */
  name: string
  /** 主题（≤12 字） */
  theme: string
  /** 总体画面风格：给 UI 的美术方向 */
  artStyle: string
  /** 固定 4 幕 */
  scenes: CultureScene[]
  /** 2–3 条收尾知识点卡 */
  cards: KnowledgeCard[]
}

export interface CultureData {
  title: string
  scrolls: Scroll[]
}
