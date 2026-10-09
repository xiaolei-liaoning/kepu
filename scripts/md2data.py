# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
#
# How to run (from the project root /Users/Admin/orca/workspaces/vtr-class/kepu):
#   python3 scripts/md2data.py            # regenerate src/data/*.ts, then verify
#   python3 scripts/md2data.py --verify   # verify existing src/data/*.ts only
# Stdlib only. The runtime-import checks additionally need Node with native
# type stripping (node --version >= 22.6).
#
# allow: SIZE_OK — the task mandates the converter AND its full verification
# suite as one deliverable file and forbids touching any other file, so the
# 250-pure-LOC split is not available here.

"""Deterministic Markdown -> TypeScript converter for the kepu data files.

Parses the two reviewed scripts under docs/脚本/, emits strictly-typed
src/data/timeline.ts and src/data/culture.ts (stable JSON bodies, no
timestamps), then proves text fidelity with an independent re-extraction
pass, structure checks, and Node runtime imports. Exits non-zero on any FAIL.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypedDict, assert_never

JsonValue = str | int | list["JsonValue"] | dict[str, "JsonValue"]

ROOT: Final = Path(__file__).resolve().parent.parent
TIMELINE_MD: Final = ROOT / "docs" / "脚本" / "01-时间线脚本.md"
CULTURE_MD: Final = ROOT / "docs" / "脚本" / "02-传统文化脚本.md"
TIMELINE_TS: Final = ROOT / "src" / "data" / "timeline.ts"
CULTURE_TS: Final = ROOT / "src" / "data" / "culture.ts"

FIELD_LINE_RE: Final = re.compile(r"^- \*\*(.+?)\*\*:(.*)$")
NUMBERED_LINE_RE: Final = re.compile(r"^\s+\d+\.\s*(.+)$")
HORIZONTAL_RULE_RE: Final = re.compile(r"^-{3,}$")
NODE_SPLIT_RE: Final = re.compile(r"(?m)^## 节点 ")
SCROLL_SPLIT_RE: Final = re.compile(r"(?m)^## 画卷 ")
SCENE_SPLIT_RE: Final = re.compile(r"(?m)^#### ")
H1_RE: Final = re.compile(r"^# (.+)$", re.MULTILINE)
SCENE_ACT_SEPARATOR: Final = " · "
ARROW: Final = "→"

# Fields compared after removing ALL whitespace (spec fidelity rule).
WS_COMPARED_FIELDS: Final = frozenset({"body", "visual", "story"})

# Independent verification pass: anchored whole-block regexes over the actual
# source formatting (single-line field values, fixed field order per block).
INDEP_TIMELINE_BLOCK_RE: Final = re.compile(
    r"^## 节点 (\d+) \| (.+)$\n"
    r"- \*\*年代\*\*: (.*)\n"
    r"- \*\*标题\*\*: (.*)\n"
    r"- \*\*正文\*\*: (.*)\n"
    r"- \*\*线索\*\*:\n"
    r"((?:[ \t]+\d+\..*\n)+)"
    r"- \*\*画面建议\*\*: (.*)$",
    re.MULTILINE,
)
INDEP_SCROLL_HEADER_RE: Final = re.compile(
    r"^## 画卷 (\d+) \| (.+)$\n"
    r"- \*\*主题\*\*: (.*)\n"
    r"- \*\*总体画面风格\*\*: (.*)$",
    re.MULTILINE,
)
INDEP_SCENE_RE: Final = re.compile(
    r"^#### (.+?) · (.+)$\n"
    r"- \*\*画面\*\*: (.*)\n"
    r"- \*\*故事\*\*: (.*)\n"
    r"- \*\*线索\*\*: (.*)$",
    re.MULTILINE,
)
INDEP_CARDS_RE: Final = re.compile(
    r"^- \*\*收尾知识点卡\*\*:\n((?:[ \t]+\d+\..*\n?)+)",
    re.MULTILINE,
)

NODE_COUNT: Final = 16
SCROLL_COUNT: Final = 5
SCENES_PER_SCROLL: Final = 4


class ScriptParseError(ValueError):
    """Raised when a Markdown source or generated TS file violates the contract."""


# --- data contract mirrors (see src/types.ts) ---------------------------------


class TimelineClue(TypedDict):
    title: str
    text: str


class TimelineNode(TypedDict):
    id: int
    era: str
    dateLabel: str
    title: str
    body: str
    clues: list[TimelineClue]
    artNote: str


class TimelineData(TypedDict):
    title: str
    nodes: list[TimelineNode]


class CultureClue(TypedDict):
    text: str
    pointsTo: str


class CultureScene(TypedDict):
    act: str
    name: str
    visual: str
    story: str
    clue: CultureClue


class KnowledgeCard(TypedDict):
    title: str
    fact: str


class Scroll(TypedDict):
    id: int
    name: str
    theme: str
    artStyle: str
    scenes: list[CultureScene]
    cards: list[KnowledgeCard]


class CultureData(TypedDict):
    title: str
    scrolls: list[Scroll]


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One verification gate outcome."""

    name: str
    ok: bool
    detail: str


# --- generation-pass parsing (regex block split + field grouping) -------------


def split_fields(lines: list[str]) -> dict[str, list[str]]:
    """Group a block's lines into named fields; continuation lines accumulate.

    A line matching ``- **NAME**:`` starts field NAME with the on-line value;
    later lines append until the next field line. Blank lines and ``---``
    document separators are not field content.
    """
    fields: dict[str, list[str]] = {}
    current: str | None = None
    for raw in lines:
        field_match = FIELD_LINE_RE.match(raw)
        if field_match is not None:
            current = field_match.group(1)
            fields[current] = [field_match.group(2)]
        elif current is not None and not HORIZONTAL_RULE_RE.match(raw):
            fields[current].append(raw)
    return fields


def joined_value(lines: list[str]) -> str:
    """Join continuation lines with '' (no separator), then strip (spec rule)."""
    return "".join(part.strip() for part in lines).strip()


def require_value(fields: dict[str, list[str]], name: str) -> str:
    """Return the joined scalar value of a required field or raise."""
    lines = fields.get(name)
    if lines is None:
        raise ScriptParseError(f"missing required field {name!r}")
    return joined_value(lines)


def numbered_items(lines: list[str]) -> list[str]:
    """Extract the payload of indented ``N. item`` lines from a list field."""
    return [match.group(1) for line in lines if (match := NUMBERED_LINE_RE.match(line))]


def split_arrow(text: str) -> tuple[str, str]:
    """Split on the FIRST '→'; both sides stripped (spec rule)."""
    left, separator, right = text.partition(ARROW)
    if not separator:
        raise ScriptParseError(f"missing arrow separator: {text!r}")
    return left.strip(), right.strip()


def parse_timeline_md(md_text: str) -> TimelineData:
    """Generation pass: split docs/脚本/01 into TimelineData."""
    h1 = next((line for line in md_text.splitlines() if line.startswith("# ")), None)
    if h1 is None:
        raise ScriptParseError("timeline markdown: missing H1 line")
    title = h1.removeprefix("# ").split("：", 1)[1].strip()
    nodes: list[TimelineNode] = []
    for block in NODE_SPLIT_RE.split(md_text)[1:]:
        block_lines = block.splitlines()
        id_str, era = (part.strip() for part in block_lines[0].split("|", 1))
        fields = split_fields(block_lines[1:])
        clues: list[TimelineClue] = []
        for item in numbered_items(fields.get("线索", [])):
            left, right = split_arrow(item)
            clues.append(TimelineClue(title=left, text=right))
        nodes.append(
            TimelineNode(
                id=int(id_str),
                era=era,
                dateLabel=require_value(fields, "年代"),
                title=require_value(fields, "标题"),
                body=require_value(fields, "正文"),
                clues=clues,
                artNote=require_value(fields, "画面建议"),
            )
        )
    return TimelineData(title=title, nodes=nodes)


def parse_culture_md(md_text: str) -> CultureData:
    """Generation pass: split docs/脚本/02 into CultureData."""
    h1 = next((line for line in md_text.splitlines() if line.startswith("# ")), None)
    if h1 is None:
        raise ScriptParseError("culture markdown: missing H1 line")
    title = h1.removeprefix("# ").removesuffix("科普脚本").strip()
    scrolls: list[Scroll] = []
    for block in SCROLL_SPLIT_RE.split(md_text)[1:]:
        meta_chunk, *scene_chunks = SCENE_SPLIT_RE.split(block)
        meta_lines = meta_chunk.splitlines()
        id_str, scroll_name = (part.strip() for part in meta_lines[0].split("|", 1))
        meta = split_fields(meta_lines[1:])
        scenes: list[CultureScene] = []
        cards: list[KnowledgeCard] = []
        for scene_chunk in scene_chunks:
            scene_lines = scene_chunk.splitlines()
            act, scene_name = (part.strip() for part in scene_lines[0].split(SCENE_ACT_SEPARATOR, 1))
            fields = split_fields(scene_lines[1:])
            clue_text, points_to = split_arrow(require_value(fields, "线索"))
            scenes.append(
                CultureScene(
                    act=act,
                    name=scene_name,
                    visual=require_value(fields, "画面"),
                    story=require_value(fields, "故事"),
                    clue=CultureClue(text=clue_text, pointsTo=points_to),
                )
            )
            for item in numbered_items(fields.get("收尾知识点卡", [])):
                card_title, fact = split_arrow(item)
                cards.append(KnowledgeCard(title=card_title, fact=fact))
        scrolls.append(
            Scroll(
                id=int(id_str),
                name=scroll_name,
                theme=require_value(meta, "主题"),
                artStyle=require_value(meta, "总体画面风格"),
                scenes=scenes,
                cards=cards,
            )
        )
    return CultureData(title=title, scrolls=scrolls)


# --- TypeScript emission ------------------------------------------------------


def emit_ts(type_name: str, const_name: str, payload: TimelineData | CultureData) -> str:
    """Render the TS module: type-only import + json.dumps object literal."""
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"import type {{ {type_name} }} from '@/types'\n\nexport const {const_name}: {type_name} = {body}\n"


def load_ts_payload(path: Path, const_name: str) -> dict[str, JsonValue]:
    """Recover the emitted JSON structure from a generated TS module."""
    text = path.read_text(encoding="utf-8")
    marker = f"export const {const_name}:"
    marker_index = text.find(marker)
    if marker_index < 0:
        raise ScriptParseError(f"{path.name}: export {const_name} not found")
    eq_index = text.find("=", marker_index)
    if eq_index < 0:
        raise ScriptParseError(f"{path.name}: assignment for {const_name} not found")
    payload: object = json.loads(text[eq_index + 1 :])
    if not isinstance(payload, dict):
        raise ScriptParseError(f"{path.name}: payload is not an object")
    return payload


# --- independent verification extraction pass --------------------------------


def extract_timeline_independent(md_text: str) -> TimelineData:
    """Second extraction pass: anchored whole-block regexes, no field grouping."""
    h1 = H1_RE.search(md_text)
    if h1 is None:
        raise ScriptParseError("independent pass: timeline H1 not found")
    nodes: list[TimelineNode] = []
    for match in INDEP_TIMELINE_BLOCK_RE.finditer(md_text):
        num, era, date_label, node_title, body, clues_block, art_note = match.groups()
        clues: list[TimelineClue] = []
        for line in clues_block.splitlines():
            item = line.strip()
            if not item:
                continue
            _num, sep, rest = item.partition(". ")
            if not sep:
                raise ScriptParseError(f"independent pass: bad clue line {item!r}")
            left, arrow, right = rest.partition(ARROW)
            if not arrow:
                raise ScriptParseError(f"independent pass: clue missing arrow {item!r}")
            clues.append(TimelineClue(title=left.strip(), text=right.strip()))
        nodes.append(
            TimelineNode(
                id=int(num),
                era=era.strip(),
                dateLabel=date_label.strip(),
                title=node_title.strip(),
                body=body.strip(),
                clues=clues,
                artNote=art_note.strip(),
            )
        )
    return TimelineData(title=h1.group(1).split("：", 1)[1].strip(), nodes=nodes)


def extract_culture_independent(md_text: str) -> CultureData:
    """Second extraction pass: per-scroll region slicing with anchored regexes."""
    h1 = H1_RE.search(md_text)
    if h1 is None:
        raise ScriptParseError("independent pass: culture H1 not found")
    scroll_spans = list(INDEP_SCROLL_HEADER_RE.finditer(md_text))
    scrolls: list[Scroll] = []
    for index, header_match in enumerate(scroll_spans):
        end = scroll_spans[index + 1].start() if index + 1 < len(scroll_spans) else len(md_text)
        region = md_text[header_match.start() : end]
        num, name, theme, art_style = header_match.groups()
        scenes: list[CultureScene] = []
        for scene_match in INDEP_SCENE_RE.finditer(region):
            act, scene_name, visual, story, clue_line = scene_match.groups()
            left, arrow, right = clue_line.partition(ARROW)
            if not arrow:
                raise ScriptParseError(f"independent pass: scene clue missing arrow {clue_line!r}")
            scenes.append(
                CultureScene(
                    act=act.strip(),
                    name=scene_name.strip(),
                    visual=visual.strip(),
                    story=story.strip(),
                    clue=CultureClue(text=left.strip(), pointsTo=right.strip()),
                )
            )
        cards: list[KnowledgeCard] = []
        cards_match = INDEP_CARDS_RE.search(region)
        if cards_match is not None:
            for line in cards_match.group(1).splitlines():
                item = line.strip()
                if not item:
                    continue
                _num, sep, rest = item.partition(". ")
                if not sep:
                    raise ScriptParseError(f"independent pass: bad card line {item!r}")
                left, arrow, right = rest.partition(ARROW)
                if not arrow:
                    raise ScriptParseError(f"independent pass: card missing arrow {item!r}")
                cards.append(KnowledgeCard(title=left.strip(), fact=right.strip()))
        scrolls.append(
            Scroll(
                id=int(num),
                name=name.strip(),
                theme=theme.strip(),
                artStyle=art_style.strip(),
                scenes=scenes,
                cards=cards,
            )
        )
    return CultureData(title=h1.group(1).removesuffix("科普脚本").strip(), scrolls=scrolls)


# --- fidelity comparison ------------------------------------------------------


def drop_ws(text: str) -> str:
    """Remove every whitespace character (fidelity rule for body/visual/story)."""
    return re.sub(r"\s+", "", text)


def compare_values(expected: JsonValue, actual: JsonValue, path: str, errors: list[str]) -> None:
    """Recursively diff two payloads; body/visual/story compare whitespace-free."""
    match expected, actual:
        case str() as expected_str, str() as actual_str:
            key = path.rsplit(".", 1)[-1]
            if key in WS_COMPARED_FIELDS:
                equal = drop_ws(expected_str) == drop_ws(actual_str)
            else:
                equal = expected_str.strip() == actual_str.strip()
            if not equal:
                errors.append(f"{path}: text mismatch")
        case int() as expected_int, int() as actual_int:
            if expected_int != actual_int:
                errors.append(f"{path}: {expected_int!r} != {actual_int!r}")
        case list() as expected_list, list() as actual_list:
            if len(expected_list) != len(actual_list):
                errors.append(f"{path}: length {len(expected_list)} != {len(actual_list)}")
            else:
                for index, (expected_item, actual_item) in enumerate(zip(expected_list, actual_list)):
                    compare_values(expected_item, actual_item, f"{path}[{index}]", errors)
        case dict() as expected_map, dict() as actual_map:
            if expected_map.keys() != actual_map.keys():
                errors.append(f"{path}: keys {sorted(expected_map)} != {sorted(actual_map)}")
            else:
                for key in expected_map:
                    compare_values(expected_map[key], actual_map[key], f"{path}.{key}", errors)
        case unreachable:
            assert_never(unreachable)


# --- structure checks ---------------------------------------------------------


def require_nonempty_str(obj: dict[str, JsonValue], key: str, path: str, errors: list[str]) -> None:
    """Append an error unless obj[key] is a non-blank string."""
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key}: empty or missing")


def check_timeline_structure(payload: dict[str, JsonValue]) -> list[str]:
    """Assert 16 nodes, ids 1..16 in order, non-empty fields, 2-3 clues each."""
    errors: list[str] = []
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        return ["timelineData.nodes: missing or not a list"]
    if len(nodes) != NODE_COUNT:
        errors.append(f"timelineData.nodes: expected {NODE_COUNT}, got {len(nodes)}")
    ids: list[JsonValue] = []
    for index, node in enumerate(nodes):
        path = f"timelineData.nodes[{index}]"
        if not isinstance(node, dict):
            errors.append(f"{path}: not an object")
            continue
        ids.append(node.get("id", -1))
        for key in ("era", "dateLabel", "title", "body", "artNote"):
            require_nonempty_str(node, key, path, errors)
        clues = node.get("clues")
        if not isinstance(clues, list):
            errors.append(f"{path}.clues: missing")
            continue
        if not 2 <= len(clues) <= 3:
            errors.append(f"{path}.clues: expected 2..3, got {len(clues)}")
        for clue_index, clue in enumerate(clues):
            clue_path = f"{path}.clues[{clue_index}]"
            if not isinstance(clue, dict):
                errors.append(f"{clue_path}: not an object")
                continue
            for key in ("title", "text"):
                require_nonempty_str(clue, key, clue_path, errors)
    if ids != list(range(1, NODE_COUNT + 1)):
        errors.append(f"timelineData node ids: expected 1..{NODE_COUNT} in order, got {ids!r}")
    return errors


def check_culture_structure(payload: dict[str, JsonValue]) -> list[str]:
    """Assert 5 scrolls, ids 1..5 in order, 4 scenes each, cards 2-3, fields non-empty."""
    errors: list[str] = []
    scrolls = payload.get("scrolls")
    if not isinstance(scrolls, list):
        return ["cultureData.scrolls: missing or not a list"]
    if len(scrolls) != SCROLL_COUNT:
        errors.append(f"cultureData.scrolls: expected {SCROLL_COUNT}, got {len(scrolls)}")
    ids: list[JsonValue] = []
    for index, scroll in enumerate(scrolls):
        path = f"cultureData.scrolls[{index}]"
        if not isinstance(scroll, dict):
            errors.append(f"{path}: not an object")
            continue
        ids.append(scroll.get("id", -1))
        for key in ("name", "theme", "artStyle"):
            require_nonempty_str(scroll, key, path, errors)
        scenes = scroll.get("scenes")
        if isinstance(scenes, list) and len(scenes) == SCENES_PER_SCROLL:
            for scene_index, scene in enumerate(scenes):
                scene_path = f"{path}.scenes[{scene_index}]"
                if not isinstance(scene, dict):
                    errors.append(f"{scene_path}: not an object")
                    continue
                for key in ("act", "name", "visual", "story"):
                    require_nonempty_str(scene, key, scene_path, errors)
                clue = scene.get("clue")
                if isinstance(clue, dict):
                    for key in ("text", "pointsTo"):
                        require_nonempty_str(clue, key, f"{scene_path}.clue", errors)
                else:
                    errors.append(f"{scene_path}.clue: missing")
        else:
            got = len(scenes) if isinstance(scenes, list) else "missing"
            errors.append(f"{path}.scenes: expected {SCENES_PER_SCROLL}, got {got}")
        cards = scroll.get("cards")
        if not isinstance(cards, list):
            errors.append(f"{path}.cards: missing")
        else:
            if not 2 <= len(cards) <= 3:
                errors.append(f"{path}.cards: expected 2..3, got {len(cards)}")
            for card_index, card in enumerate(cards):
                card_path = f"{path}.cards[{card_index}]"
                if not isinstance(card, dict):
                    errors.append(f"{card_path}: not an object")
                    continue
                for key in ("title", "fact"):
                    require_nonempty_str(card, key, card_path, errors)
    if ids != list(range(1, SCROLL_COUNT + 1)):
        errors.append(f"cultureData scroll ids: expected 1..{SCROLL_COUNT} in order, got {ids!r}")
    return errors


# --- Node runtime import checks -----------------------------------------------


def node_runtime_check(name: str, snippet: str) -> CheckResult:
    """Run a Node ESM one-liner importing a generated .ts file (types stripped)."""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", snippet],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    output = (proc.stdout or proc.stderr).strip()
    if proc.returncode != 0:
        return CheckResult(name, False, output or f"exit code {proc.returncode}")
    return CheckResult(name, True, output or "ok")


# --- reporting ----------------------------------------------------------------


def string_stats(value: JsonValue) -> tuple[int, int]:
    """Return (string-field count, total characters) across a payload."""
    match value:
        case str():
            return 1, len(value)
        case int():
            return 0, 0
        case list():
            stats = [string_stats(item) for item in value]
            return sum(count for count, _ in stats), sum(chars for _, chars in stats)
        case dict():
            stats = [string_stats(item) for item in value.values()]
            return sum(count for count, _ in stats), sum(chars for _, chars in stats)
        case unreachable:
            assert_never(unreachable)


def report(results: list[CheckResult]) -> int:
    """Print one PASS/FAIL line per check; return the number of passing checks."""
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"{status}  {result.name}: {result.detail}")
    return sum(1 for result in results if result.ok)


def print_summary(timeline_payload: TimelineData, culture_payload: CultureData) -> None:
    """Print field counts and total characters per generated file."""
    timeline_strings, timeline_chars = string_stats(timeline_payload)
    culture_strings, culture_chars = string_stats(culture_payload)
    clue_count = sum(len(node["clues"]) for node in timeline_payload["nodes"])
    scene_count = sum(len(scroll["scenes"]) for scroll in culture_payload["scrolls"])
    card_count = sum(len(scroll["cards"]) for scroll in culture_payload["scrolls"])
    print("--- summary ---")
    print(
        f"timeline.ts: nodes={len(timeline_payload['nodes'])} clues={clue_count} "
        f"strings={timeline_strings} chars={timeline_chars}"
    )
    print(
        f"culture.ts:  scrolls={len(culture_payload['scrolls'])} scenes={scene_count} "
        f"cards={card_count} strings={culture_strings} chars={culture_chars}"
    )


# --- main ---------------------------------------------------------------------


def run(argv: list[str]) -> int:
    """Convert both scripts (unless --verify), then run every verification gate."""
    verify_only = "--verify" in argv
    timeline_md = TIMELINE_MD.read_text(encoding="utf-8")
    culture_md = CULTURE_MD.read_text(encoding="utf-8")

    timeline_payload = parse_timeline_md(timeline_md)
    culture_payload = parse_culture_md(culture_md)
    if verify_only:
        print("md2data: --verify given, not writing src/data/*.ts")
    else:
        TIMELINE_TS.write_text(
            emit_ts("TimelineData", "timelineData", timeline_payload),
            encoding="utf-8",
            newline="\n",
        )
        CULTURE_TS.write_text(
            emit_ts("CultureData", "cultureData", culture_payload),
            encoding="utf-8",
            newline="\n",
        )
        print(f"md2data: wrote src/data/timeline.ts ({TIMELINE_TS.stat().st_size} bytes)")
        print(f"md2data: wrote src/data/culture.ts ({CULTURE_TS.stat().st_size} bytes)")

    timeline_expected = extract_timeline_independent(timeline_md)
    culture_expected = extract_culture_independent(culture_md)
    timeline_actual = load_ts_payload(TIMELINE_TS, "timelineData")
    culture_actual = load_ts_payload(CULTURE_TS, "cultureData")

    results: list[CheckResult] = []
    errors: list[str] = []
    compare_values(timeline_expected, timeline_actual, "timelineData", errors)
    results.append(
        CheckResult(
            "fidelity timeline (independent MD pass == emitted TS JSON)",
            not errors,
            f"{len(timeline_expected['nodes'])} nodes, all fields equal" if not errors else "; ".join(errors[:10]),
        )
    )
    errors = []
    compare_values(culture_expected, culture_actual, "cultureData", errors)
    results.append(
        CheckResult(
            "fidelity culture (independent MD pass == emitted TS JSON)",
            not errors,
            f"{len(culture_expected['scrolls'])} scrolls, all fields equal" if not errors else "; ".join(errors[:10]),
        )
    )
    structure_errors = check_timeline_structure(timeline_actual)
    results.append(
        CheckResult(
            "timeline structure (16 nodes, ids 1..16, fields non-empty, clues 2-3)",
            not structure_errors,
            "ok" if not structure_errors else "; ".join(structure_errors[:10]),
        )
    )
    structure_errors = check_culture_structure(culture_actual)
    results.append(
        CheckResult(
            "culture structure (5 scrolls, ids 1..5, 4 scenes each, cards 2-3, fields non-empty)",
            not structure_errors,
            "ok" if not structure_errors else "; ".join(structure_errors[:10]),
        )
    )
    results.append(
        node_runtime_check(
            "timeline runtime import (node type stripping)",
            "const m = await import('./src/data/timeline.ts');"
            "if (m.timelineData.nodes.length !== 16) process.exit(1);"
            "console.log('timeline OK', m.timelineData.nodes.length);",
        )
    )
    results.append(
        node_runtime_check(
            "culture runtime import (node type stripping)",
            "const m = await import('./src/data/culture.ts');"
            "if (m.cultureData.scrolls.length !== 5) process.exit(1);"
            "if (!m.cultureData.scrolls.every((s) => s.scenes.length === 4)) process.exit(1);"
            "console.log('culture OK', m.cultureData.scrolls.length);",
        )
    )

    print("--- verification ---")
    passed = report(results)
    print_summary(timeline_payload, culture_payload)
    total = len(results)
    if passed == total:
        print(f"ALL CHECKS PASS ({passed}/{total})")
        return 0
    print(f"CHECKS FAILED ({passed}/{total} passed)")
    return 1


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
