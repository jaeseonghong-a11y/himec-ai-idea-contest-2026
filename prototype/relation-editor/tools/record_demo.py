"""시연 대본(시연_시나리오.md)을 실제 마우스·키보드 조작으로 진행하면서 영상으로 찍는다.

python tools/record_demo.py            # 1부·2부·3부 전체 → out/video/시연_영상.mp4
python tools/record_demo.py 1 3        # 일부만 (1, 2, 3)
python tools/record_demo.py --fast     # 기다리는 시간을 줄여 빨리 (점검용)

- Playwright로 Edge를 화면 없이 띄워 편집기를 조작한다. 클릭·입력은 브라우저의 실제 마우스·키보드 이벤트다
  (리허설처럼 이벤트를 요소에 직접 넣지 않는다). 커서와 클릭 표시는 영상에 보이도록 화면에 그린 것이다.
- 도면 반영(2_도면에_반영.bat 이 하는 일)과 PDF 지시 반영(7_… .bat)은 녹화 중에 실제로 실행하고, 그 출력을 터미널 모양 화면에 옮겨 보여 준다.
- 2부의 AutoCAD 출력 그림은 같은 계획안으로 미리 뽑아 둔 scenario/b*.png 를 쓴다(AutoCAD 실행은 녹화에 넣지 않음).
- 단계마다 상태를 확인하고, 어긋나면 멈춘다.

먼저: bash tools/setup_from_drawings.sh, python tools/rehearse.py, python tools/show_pdf_apply.py --no-open, python tools/make_scenario_images.py
필요: pip install playwright (Edge 설치본을 쓴다), ffmpeg(또는 imageio-ffmpeg)
"""
import html
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "video"
SLIDES = OUT / "slides"
W, H = 1600, 1000
FAST = "--fast" in sys.argv
PARTS = [a for a in sys.argv[1:] if a in ("1", "2", "3")] or ["1", "2", "3"]
K = 0.35 if FAST else 1.0            # 기다리는 시간 배율

CURSOR_JS = r"""
(() => {
  const make = () => {
    if (document.getElementById('__cursor')) return;
    const c = document.createElement('div'); c.id = '__cursor';
    c.innerHTML = '<svg width="30" height="30" viewBox="0 0 28 28"><path d="M4 2 L4 22 L9.5 17 L13 25 L16.5 23.5 L13 15.5 L20.5 15.5 Z" fill="#111" stroke="#fff" stroke-width="1.8" stroke-linejoin="round"/></svg>';
    c.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;transform:translate(-100px,-100px)';
    const ring = document.createElement('div'); ring.id = '__ring';
    ring.style.cssText = 'position:fixed;left:0;top:0;width:40px;height:40px;margin:-20px 0 0 -20px;border:3px solid #e53935;border-radius:50%;z-index:2147483646;pointer-events:none;opacity:0';
    document.documentElement.appendChild(ring); document.documentElement.appendChild(c);
    window.addEventListener('mousemove', e => { c.style.transform = `translate(${e.clientX - 4}px,${e.clientY - 2}px)`; }, true);
    window.addEventListener('mousedown', e => {
      ring.style.transition = 'none'; ring.style.transform = `translate(${e.clientX}px,${e.clientY}px) scale(.35)`; ring.style.opacity = '1';
      requestAnimationFrame(() => requestAnimationFrame(() => { ring.style.transition = 'opacity .5s, transform .5s'; ring.style.transform = `translate(${e.clientX}px,${e.clientY}px) scale(1.25)`; ring.style.opacity = '0'; }));
    }, true);
  };
  if (document.body) make(); else document.addEventListener('DOMContentLoaded', make);
})();
"""

CAPTION_JS = """(t) => { let c = document.getElementById('__cap');
  if (!c) { c = document.createElement('div'); c.id = '__cap';
    c.style.cssText = 'position:fixed;left:16px;bottom:52px;max-width:60%;background:#1a237e;color:#fff;padding:11px 18px;font:600 18px "Malgun Gothic",sans-serif;line-height:1.45;border-radius:8px;z-index:2147483000;white-space:pre-wrap;box-shadow:0 3px 12px rgba(0,0,0,.35);pointer-events:none';
    document.body.appendChild(c); }
  c.textContent = t; c.style.display = t ? 'block' : 'none'; }"""

# 요소 위에서 실제로 그 요소가 맞는(다른 것에 가리지 않은) 화면 점을 찾는다
HIT_JS = """([sel, scroll]) => { const el = document.querySelector(sel); if (!el) return null;
  if (scroll) el.scrollIntoView({ block: 'center' });
  const ok = (x, y) => { const t = document.elementFromPoint(x, y); return t === el || (t && el.contains(t)); };
  const r = el.getBoundingClientRect(), pts = [];
  if (el.tagName === 'line') { const m = el.getScreenCTM(), P = (x, y) => { const q = new DOMPoint(x, y).matrixTransform(m); return [q.x, q.y]; };
    const a = P(+el.getAttribute('x1'), +el.getAttribute('y1')), b = P(+el.getAttribute('x2'), +el.getAttribute('y2'));
    for (const t of [0.5, 0.4, 0.6, 0.3, 0.7, 0.22, 0.78, 0.15, 0.85, 0.1, 0.9, 0.06, 0.94]) pts.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]); }
  pts.push([r.left + r.width / 2, r.top + r.height / 2]);
  for (let i = 1; i < 8; i++) for (let j = 1; j < 8; j++) pts.push([r.left + r.width * i / 8, r.top + r.height * j / 8]);
  for (const p of pts) if (p[0] > 2 && p[1] > 2 && p[0] < innerWidth - 2 && p[1] < innerHeight - 2 && ok(p[0], p[1])) return p;
  return null; }"""

SLIDE_CSS = """<meta charset="utf-8"><style>
html,body{margin:0;height:100%;background:#fff;font-family:"Malgun Gothic",sans-serif;color:#1b1b1b;overflow:hidden}
.wrap{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:26px 40px;box-sizing:border-box}
h1{font-size:46px;margin:0 0 18px;color:#1a237e;text-align:center} h2{font-size:28px;margin:0 0 14px;color:#1a237e;align-self:flex-start}
p{font-size:24px;line-height:1.6;margin:6px 0;text-align:center} .sub{color:#555;font-size:20px}
.row{display:flex;gap:18px;flex:1;min-height:0;width:100%;align-items:center;justify-content:center}
.cell{flex:1;min-width:0;height:100%;display:flex;flex-direction:column;align-items:center}
.cell b{font-size:20px;margin-bottom:6px} .cell img{max-width:100%;max-height:calc(100% - 34px);object-fit:contain;border:1px solid #ccc}
.note{font-size:21px;margin-top:12px;color:#222;text-align:center;line-height:1.5}
.dark{background:#000} .dark .cell img{border-color:#333}
.term{background:#0c0c0c;color:#ddd;width:100%;flex:1;min-height:0;border-radius:8px;box-shadow:0 4px 18px rgba(0,0,0,.4);display:flex;flex-direction:column}
.term .bar{background:#2b2b2b;color:#ccc;padding:8px 14px;font-size:15px;border-radius:8px 8px 0 0}
.term pre{margin:0;padding:16px 20px;font:18px/1.6 Consolas,"Malgun Gothic",monospace;white-space:pre-wrap;word-break:break-all;overflow:hidden;flex:1}
.term .run{animation:blink 1s steps(2) infinite} @keyframes blink{50%{opacity:.25}}
.term .cmd{color:#fff} .term .ok{color:#7ee787} .term .warn{color:#f0c674} .term .dim{color:#8b949e}
ul{font-size:23px;line-height:1.7}
</style>"""


class Rec:
    def __init__(self, page):
        self.page, self.pos, self.n = page, (W * 0.55, H * 0.5), 0
        self.log = []

    # ----- 기본 동작 -----
    def hold(self, sec):
        time.sleep(sec * K)

    def goto(self, path, hashpart=""):
        self.page.goto(Path(path).as_uri() + (("#" + hashpart) if hashpart else ""))
        self.page.wait_for_load_state("load")
        self.page.mouse.move(*self.pos)

    def caption(self, text):
        self.page.evaluate(CAPTION_JS, text)
        if text:
            print("  ·", text.replace("\n", " / "))

    def move(self, x, y):
        x0, y0 = self.pos
        d = math.hypot(x - x0, y - y0)
        dur = min(0.85, max(0.22, d / 1500)) * (0.5 if FAST else 1)
        n = max(5, int(dur * 45))
        for i in range(1, n + 1):
            t = i / n; e = t * t * (3 - 2 * t)
            self.page.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e)
            time.sleep(dur / n)
        self.pos = (x, y)

    def click_at(self, x, y, pause=0.45):
        self.move(x, y); time.sleep(0.12 * K)
        self.page.mouse.down(); time.sleep(0.07); self.page.mouse.up()
        self.hold(pause)

    def point(self, sel, scroll=False):
        p = self.page.evaluate(HIT_JS, [sel, scroll])
        if not p:
            raise RuntimeError(f"화면에서 누를 수 있는 점을 찾지 못함: {sel}")
        return p

    def click(self, sel, scroll=False, pause=0.45):
        self.click_at(*self.point(sel, scroll), pause=pause)

    def panel(self, sel, pause=0.45):          # 오른쪽 칸의 요소 (필요하면 스크롤)
        self.click(sel, scroll=True, pause=pause)

    def type_in(self, sel, text, commit="Tab"):
        self.click(sel, scroll=True, pause=0.15)
        self.page.keyboard.press("Control+A")
        self.page.keyboard.type(str(text), delay=0 if FAST else 70)
        if commit:
            self.page.keyboard.press(commit)
        self.hold(0.35)

    def choose(self, sel, value):
        p = self.point(sel, True); self.move(*p); self.hold(0.25)
        self.page.select_option(sel, value); self.hold(0.6)

    def tool(self, mode):
        self.click(f'#tools button[data-mode="{mode}"]', pause=0.35)

    def svg(self, kind, ident=None, extra="", pause=0.45):
        sel = f'#svg [data-kind="{kind}"]' + (f'[data-id="{ident}"]' if ident is not None else "") + extra
        self.click(sel, pause=pause)

    def vid(self, expr, arg=None):
        return self.page.evaluate(f"(a) => window.__vid.{expr}", arg)

    def check(self, cond, what):
        self.log.append(("OK  " if cond else "FAIL") + " " + what)
        if not cond:
            raise RuntimeError("단계 확인 실패: " + what)

    def blank_click(self):
        for p in ((40, 150), (40, 400), (1250, 150), (1250, 880), (40, 700)):
            k = self.page.evaluate("([x, y]) => { const t = document.elementFromPoint(x, y); return t && t.closest('#svg') ? (t.dataset && t.dataset.kind) || '' : null; }", list(p))
            if k == "":
                self.click_at(*p, pause=0.3); return
        raise RuntimeError("빈 곳을 찾지 못함")

    # ----- 슬라이드 -----
    def slide(self, body, cls=""):
        self.n += 1
        f = SLIDES / f"s{self.n:02d}.html"
        f.write_text(f"<!doctype html>{SLIDE_CSS}<body class='{cls}'><div class='wrap'>{body}</div></body>", encoding="utf-8")
        self.pos = (W - 46, H - 40)                # 슬라이드에서는 커서를 구석에 둔다
        self.goto(f)

    def title(self, head, lines, sec=4):
        self.slide(f"<h1>{head}</h1>" + "".join(f"<p{' class=sub' if l.startswith('~') else ''}>{html.escape(l.lstrip('~'))}</p>" for l in lines))
        self.hold(sec)

    def images(self, head, cells, note="", sec=5):
        cs = "".join(f"<div class='cell'><b>{html.escape(lab)}</b><img src='{Path(p).as_uri()}'></div>" for lab, p in cells if Path(p).exists())
        self.slide(f"<h2>{html.escape(head)}</h2><div class='row'>{cs}</div>" + (f"<div class='note'>{html.escape(note)}</div>" if note else ""))
        self.hold(sec)

    def terminal(self, bar, cmd, args, pick, cwd=ROOT, tail=None):
        """명령을 실제로 실행하고 그 출력을 터미널 모양 화면에 옮긴다. pick(line) 이 참인 줄만 보여 준다."""
        self.slide(f"<h2>{html.escape(bar)}</h2><div class='term'><div class='bar'>명령 프롬프트</div><pre id='t'></pre></div>")
        add = "([s, c]) => { const t = document.getElementById('t'), d = document.createElement('div'); d.className = c; d.textContent = s; t.appendChild(d); while (t.scrollHeight > t.clientHeight && t.children.length > 2) t.removeChild(t.children[1]); }"
        self.page.evaluate(add, [f"> {cmd}", "cmd"]); self.hold(0.6)
        t0 = time.time()
        pr = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        self.page.evaluate(add, ["실행 중 …", "dim run"])
        out = pr.communicate()[0]
        sec = time.time() - t0
        self.page.evaluate("() => { const t = document.getElementById('t'); t.removeChild(t.lastChild); }")
        out = out.replace(str(ROOT) + "\\", "").replace(str(ROOT), ".")          # 화면에는 폴더 안 경로만
        lines = [l.rstrip() for l in out.splitlines() if l.strip() and pick(l)]
        for l in lines:
            cls = "ok" if ("일치" in l or "saved" in l or "반영:" in l) else "warn" if ("FAIL" in l or "오류" in l or "반영하지 않음" in l) else ""
            self.page.evaluate(add, [l.strip()[:140], cls]); time.sleep(0.13 * K)
        self.page.evaluate(add, [f"({sec:.0f}초 걸림)", "dim"])
        if tail:
            self.page.evaluate(add, [tail, "ok"])
        self.hold(3.5)
        if pr.returncode:
            raise RuntimeError(f"{cmd} 실패\n" + out[-800:])
        return out


def same_edits(a, b):
    key = lambda cs: sorted((c["action"], json.dumps(c.get("params", {}), sort_keys=True, ensure_ascii=False)) for c in cs)
    return key(a) == key(b)


def export(r, name):
    """검토자 이름을 쓰고 변경 내보내기를 눌러 내려받는다. 다시 읽어 대조할 요약도 함께 저장한다."""
    r.type_in("#reviewer", "시연", commit=None)
    with r.page.expect_download() as dl:
        r.panel("#btnExport")
    ch = OUT / f"changes_{name}.json"
    dl.value.save_as(ch)
    ex = OUT / f"expected_{name}.json"
    ex.write_text(json.dumps(r.vid("expected()"), ensure_ascii=False, indent=1), encoding="utf-8")
    r.hold(1.2)
    return ch, ex


# ===================== 1부 =====================
def part1(r):
    r.title("1부. 있는 도면을 고친다", ["근린생활시설 1층 평면도 · 설계 변경 지시 여섯 건",
                               "① 기둥열 X6을 500 이동  ② 화장실 창을 큰 것으로  ③ 화장실 문을 900으로",
                               "④ 문 하나 삭제  ⑤ 벽을 세우고 문을 냄  ⑥ 모서리 기둥 삭제 검토"], sec=6)
    r.goto(ROOT / "out" / "editor" / "relation_editor_A12M.html")
    for i in range(3):                                   # 설비는 끄고 시작
        r.page.evaluate("(i) => { const c = document.querySelectorAll('#discToggles input')[i]; if (c.checked) c.click(); }", i)
    r.caption("0. 이 화면은 캐드 도면을 읽어서 만든 관계도입니다\n동그라미 = 기둥, 실선 = 벽, 점선 = 보, 네모 = 창호, 세모 = 문"); r.hold(5)
    g0 = r.vid("grids()")

    r.caption("1. 세로 그리드 X6을 클릭하고, 이동량 500 → 적용")
    r.svg("grid", "X6"); r.type_in("#inDelta", 500, commit=None); r.panel("#btnApplyDelta")
    r.check(r.vid("grids()")["X6"] == g0["X6"] + 500, "X6 +500")
    r.caption("기둥 3개가 그리드를 따라가고, 치수가 빨갛게 바뀝니다 (5700 → 6200, 2900 → 2400, 5700 → 5200)"); r.hold(4)

    r.caption("2-1. 창 W2를 클릭하고 타입을 WT3(폭 900)으로 — 4층 도면에 있는 창호를 가져옵니다")
    r.svg("opening", "W2"); r.choose("#inOT", "WT3")
    r.check(r.vid("opening(a)", "W2")["otype"] == "WT3", "W2 → WT3")
    r.caption("2-2. 문 D1을 클릭하고 타입을 DT4(폭 900)로")
    r.svg("opening", "D1"); r.choose("#inOT", "DT4")
    r.check(r.vid("opening(a)", "D1")["otype"] == "DT4", "D1 → DT4")
    r.caption("2-3. 문 D3을 클릭하고 삭제 — 지운 자리는 벽으로 다시 이어집니다")
    r.svg("opening", "D3"); r.panel("#btnDel")
    r.check(r.vid("opening(a)", "D3") is None, "D3 삭제"); r.hold(1.5)

    r.caption("3-1. 전기·설비·소방을 켭니다 (이 도면 세트에 없어 시연용으로 가상 배치한 것)")
    for i in range(3):
        r.click(f"#discToggles label:nth-child({i + 1}) input", pause=0.3)
    r.caption("조명·헤드·디퓨저는 넓어진 구획에 맞춰 이미 다시 놓여 있습니다"); r.hold(3)
    r.caption("3-2. + 벽: X6 위의 Y2~Y4 구간을 클릭")
    r.tool("wall"); i = r.vid("segIndex(a[0], a[1])", [["X6", "Y2"], ["X6", "Y4"]])
    r.svg("cand-seg", extra=f'[data-i="{i}"]')
    w = r.vid("wallEdge(a[0], a[1])", [["X6", "Y2"], ["X6", "Y4"]]); r.check(bool(w and w["wall"]), "벽 X6 Y2~Y4")
    r.caption("3-3. + 문: 아래쪽 벽(Y1)의 콘센트가 있는 자리를 클릭")
    r.tool("door"); ow = r.vid("outletWall()")
    n0 = r.vid("state()")["openings"]
    x, y = r.vid("toClient(a[0], a[1])", [ow["x"], ow["y"]])
    hit = None
    for dy in (0, -3, 3, -6, 6, -9, 9):
        k = r.page.evaluate("([x, y]) => { const t = document.elementFromPoint(x, y); return t && t.dataset ? t.dataset.kind : null; }", [x, y + dy])
        if k == "cand-wall":
            hit = (x, y + dy); break
    r.check(hit is not None, "문을 놓을 벽 위의 점"); r.click_at(*hit)
    r.check(r.vid("state()")["openings"] == n0 + 1, "문 D8 추가")
    r.caption("경고: 콘센트가 새 문과 겹침 · 옮긴 기둥이 덕트와 간섭 · 헤드 간격 초과\n건축을 바꾸면 설비가 받는 영향을 바로 알려 줍니다")
    r.page.evaluate("() => document.getElementById('warnPanel').scrollIntoView({ block: 'center' })"); r.hold(6)

    r.caption("4. 기둥 X7-Y9를 클릭하고 삭제 — 받치던 보가 있다고 경고합니다. 판단은 사람이 합니다")
    r.tool("select"); c = r.vid("node(a[0], a[1])", ["X7", "Y9"])
    r.svg("column", c["id"]); r.panel("#btnDel")
    r.check((r.vid("node(a[0], a[1])", ["X7", "Y9"]) or {}).get("type") != "column", "기둥 X7-Y9 삭제")
    r.page.evaluate("() => document.getElementById('warnPanel').scrollIntoView({ block: 'center' })"); r.hold(3.5)

    r.caption("5. 검토자 이름을 쓰고 변경 내보내기 — 빨강은 바뀐 것, 초록은 새로 넣은 것")
    r.blank_click()
    ch, ex = export(r, "A12M")
    r.caption("")
    ref = ROOT / "out" / "rehearsal" / "changes_A12M.json"
    crops = ref.exists() and same_edits(json.loads(ch.read_text(encoding="utf-8")), json.loads(ref.read_text(encoding="utf-8")))
    r.terminal("실제 도면(DXF)에 반영 — 2_도면에_반영.bat", "2_도면에_반영.bat",
               [sys.executable, str(ROOT / "propagate" / "apply_edits.py"), "A12M", str(ch), str(ex), "--quick"],
               lambda l: l.strip().startswith(("CR-", "saved")) or ("일치" in l and "/" in l),
               tail="원본은 그대로 두고 복사본(out/real/A12M_edited.dxf)을 고쳤습니다")
    R = ROOT / "out" / "real"
    r.images("도면: 변경 전 → 변경 후", [("변경 전", R / "A12M_edit_before.png"), ("변경 후", R / "A12M_edit_after.png")], sec=6)
    if crops:                                            # 확대 그림은 같은 변경으로 미리 뽑아 둔 것(전체 실행은 1분 넘게 걸림)
        r.images("창을 바꾼 자리 (WT1 600 → WT3 900)", [("변경 전", R / "A12M_edit_before_W1.png"), ("변경 후", R / "A12M_edit_after_W1.png")], "4층 도면의 창호 기호를 복사해 놓고, 문틀 쪽 벽선을 옮겼습니다", sec=5)
        r.images("문을 새로 낸 자리 (D8)", [("변경 전", R / "A12M_edit_before_D8.png"), ("변경 후", R / "A12M_edit_after_D8.png")], "벽선을 잘라 내고 1층의 문 기호를 복사해 놓았습니다", sec=5)
    r.images("고친 도면을 다시 읽은 관계도", [("다시 읽은 관계도", R / "A12M_edited_graph.png")], "고친 도면을 처음처럼 다시 읽어 편집기의 관계도와 대조 — 17개 항목 모두 일치", sec=6)



# ===================== 2부 =====================
def part2(r):
    r.title("2부. 백지에서 새로 그린다", ["대지만 정해진 계획 초기", "관계도를 쌓아 치수와 일람표까지 있는 도면을 뽑습니다"], sec=5)
    r.goto(ROOT / "out" / "editor" / "relation_editor_NEW1.html")
    r.caption("아무것도 없는 새 프로젝트"); r.hold(2.5)

    r.caption("1-1. 사각형 대지 26000 × 19000")
    r.type_in("#inSW", 26000); r.type_in("#inSD", 19000); r.panel("#btnSiteRect"); r.hold(1)
    r.caption("1-2. 그리드: 세로 3000 + 6000,6000,6000 / 가로 3500 + 6000,6000 → 한 번에 만들기")
    r.type_in("#inGX0", 3000, commit=None); r.type_in("#inGXs", "6000,6000,6000", commit=None)
    r.type_in("#inGY0", 3500, commit=None); r.type_in("#inGYs", "6000,6000", commit=None); r.panel("#btnGridSeries")
    r.check(len(r.vid("grids()")) == 7, "그리드 7줄")
    r.caption("치수는 그리드를 놓는 순간 자동으로 생깁니다 (대지경계선 안쪽에 들어가도록)"); r.hold(3.5)

    xs, ys = ["X1", "X2", "X3", "X4"], ["Y1", "Y2", "Y3"]
    r.caption("2-1. + 기둥: 교점 12곳을 클릭")
    r.tool("column")
    for y in reversed(ys):
        for x in xs:
            r.svg("cand-pt", extra=f'[data-xi="{x}"][data-yj="{y}"]', pause=0.12)
    r.check(r.vid("state()")["cols"] == 12, "기둥 12개"); r.hold(1)

    r.caption("2-2. + 보: 기둥 사이 17구간을 클릭 — 기둥과 기둥 사이는 거더로 분류됩니다")
    r.tool("beam")
    segs = [([xs[i], y], [xs[i + 1], y]) for y in reversed(ys) for i in range(3)] + [([x, ys[j]], [x, ys[j + 1]]) for x in xs for j in (1, 0)]
    for a, b in segs:
        i = r.vid("segIndex(a[0], a[1])", [a, b])
        if i >= 0:
            r.svg("cand-seg", extra=f'[data-i="{i}"]', pause=0.1)
    r.check(r.vid("state()")["beams"] == 17, "보 17구간"); r.hold(1)

    r.caption("2-3. + 벽: 바깥 둘레 10구간을 클릭")
    r.tool("wall")
    ring = [([xs[i], "Y3"], [xs[i + 1], "Y3"]) for i in range(3)] + [(["X4", "Y3"], ["X4", "Y2"]), (["X4", "Y2"], ["X4", "Y1"])] + \
           [([xs[i + 1], "Y1"], [xs[i], "Y1"]) for i in (2, 1, 0)] + [(["X1", "Y1"], ["X1", "Y2"]), (["X1", "Y2"], ["X1", "Y3"])]
    for a, b in ring:
        i = r.vid("segIndex(a[0], a[1])", [a, b])
        r.svg("cand-seg", extra=f'[data-i="{i}"]', pause=0.12)
    r.check(r.vid("state()")["walls"] == 10, "벽 10구간")
    r.caption("오른쪽 위: 대지면적 494 ㎡, 개략 건축면적 216 ㎡, 건폐율 약 43.7%"); r.hold(3.5)

    ot = r.vid("otypes()")
    dt = next((t for t in ot if t["kind"] == "door" and t["leaves"] == 2), None) or next(t for t in ot if t["kind"] == "door")
    wt = sorted((t for t in ot if t["kind"] == "window" and not t["band"] and not t["check"] and t["width"] >= 1800), key=lambda t: t["width"])[0]

    def place(mode, a, b, t, typ):
        r.tool(mode)
        e = r.vid("wallEdge(a[0], a[1])", [a, b])
        px = e["from"][0] + (e["to"][0] - e["from"][0]) * t; py = e["from"][1] + (e["to"][1] - e["from"][1]) * t
        n0 = r.vid("state()")["openings"]
        r.click_at(*r.vid("toClient(a[0], a[1])", [px, py]), pause=0.3)
        r.check(r.vid("state()")["openings"] == n0 + 1, f"{mode} {a}~{b}")
        r.choose("#inOT", typ["id"])

    r.caption(f"3-1. + 문: 아래 벽 가운데에 놓고, 타입에서 {dt['id']}(폭 {dt['width']}, 두 짝)을 고릅니다")
    place("door", ["X2", "Y1"], ["X3", "Y1"], 0.5, dt)
    r.caption(f"+ 창호: 위 벽 세 곳과 왼쪽 벽 두 곳 — 놓은 뒤 타입 {wt['id']}(폭 {wt['width']})")
    for (a, b, t) in ((["X1", "Y3"], ["X2", "Y3"], 0.5), (["X2", "Y3"], ["X3", "Y3"], 0.5), (["X3", "Y3"], ["X4", "Y3"], 0.5), (["X1", "Y1"], ["X1", "Y2"], 0.5), (["X1", "Y2"], ["X1", "Y3"], 0.62)):
        place("window", a, b, t, wt)
    r.check(r.vid("state()")["openings"] == 6, "문 1, 창호 5"); r.hold(1)

    r.caption("3-2. + 코어: 승강기 EV1을 X1-Y2에 — 입구 방향을 오른쪽으로, 왼쪽 벽은 건물 벽이 대신하므로 끕니다")
    r.choose("#selCore", "EV1"); r.tool("core")
    r.svg("cand-core", extra='[data-xi="X1"][data-yj="Y2"]'); r.choose("#inCE", "E")
    if r.page.evaluate("() => { const b = document.querySelector('.inCW[data-side=\"W\"]'); return !!(b && b.checked); }"):
        r.panel('.inCW[data-side="W"]')
    r.hold(1.5)
    r.caption("3-3. + 코어: 계단 ST1을 X2-Y2에, 옆으로 뒤집기 — 층고 3400에서 20단, 단높이 170이 계산됩니다")
    r.choose("#selCore", "ST1"); r.tool("core")
    r.svg("cand-core", extra='[data-xi="X2"][data-yj="Y2"]'); r.panel("#btnCS")
    r.check(r.vid("state()")["cores"] == 2, "코어 2개"); r.hold(3)

    r.caption("4-1. 벽 두께: 기본값 250을 모든 벽에, 위·아래 외벽은 300으로")
    r.blank_click(); r.type_in("#inWT", 250); r.panel("#btnWTAll")
    for a, b in ((["X1", "Y3"], ["X2", "Y3"]), (["X1", "Y1"], ["X2", "Y1"])):
        e = r.vid("wallEdge(a[0], a[1])", [a, b])
        r.svg("edge", e["id"]); r.type_in("#inThick", 300); r.panel("#btnThickLine")
    r.blank_click(); r.hold(1.5)

    r.caption("4-2. 모서리를 자릅니다: 모서리의 벽 두 구간과 기둥을 지우고")
    for a, b in ((["X3", "Y1"], ["X4", "Y1"]), (["X4", "Y1"], ["X4", "Y2"])):
        e = r.vid("wallEdge(a[0], a[1])", [a, b])
        r.svg("edge", e["id"]); r.panel("#btnDel")
    c = r.vid("node(a[0], a[1])", ["X4", "Y1"])
    if c and c["type"] == "column":
        r.svg("column", c["id"]); r.panel("#btnDel")
    r.caption("+ 사선: 교점 X3-Y1과 X4-Y2를 차례로 클릭 — 그리드는 그대로 두고 사선 벽이 생깁니다. 보도 켭니다")
    r.tool("diag")
    r.svg("cand-diag", extra='[data-xi="X3"][data-yj="Y1"]'); r.svg("cand-diag", extra='[data-xi="X4"][data-yj="Y2"]')
    if not r.page.evaluate("() => document.getElementById('ckBeam').checked"):
        r.panel("#ckBeam")
    st = r.vid("state()"); r.check(st["cols"] == 11 and st["walls"] == 9 and st["beams"] == 16, f"끝 상태 {st}")
    r.caption("사선 길이 8485의 정렬 치수가 붙고, 긴 보(기준 7500 초과)라고 경고합니다"); r.hold(4)

    r.caption("5. 검토자 이름을 쓰고 변경 내보내기")
    r.blank_click()
    ch, ex = export(r, "NEW1")
    r.caption("")
    r.terminal("관계도에서 도면(DXF)을 그립니다 — 2_도면에_반영.bat", "2_도면에_반영.bat",
               [sys.executable, str(ROOT / "propagate" / "apply_edits.py"), "NEW1", str(ch), str(ex), "--quick"],
               lambda l: ("맞물림" in l or "겹침 피하기" in l or "일치" in l and "/" in l or l.strip().startswith("saved")
                          or any(k in l for k in ("대지경계선", "사선", "문 추가", "코어", "치수 3", "일람표"))),
               tail="다시 읽어 대조: 벽 두께와 코어까지 그대로")
    S = ROOT / "scenario"
    ref = ROOT / "out" / "rehearsal" / "changes_NEW1.json"
    if ref.exists() and same_edits(json.loads(ch.read_text(encoding="utf-8")), json.loads(ref.read_text(encoding="utf-8"))):
        r.images("AutoCAD 2024에서 출력한 도면 (A2, 1/100)", [("", S / "b4_sheet.png")], "치수 31개, 일람표 5개, 도면 틀 · AutoCAD 도면 검사(AUDIT) 오류 0건", sec=6)
        r.images("평면", [("", S / "b5_plan.png")], "벽선은 기둥 면에서 멈추고, 승강로 벽은 외벽과 한 덩어리로 이어집니다", sec=6)
        r.images("확대", [("벽과 기둥, 코어", S / "b6_walls.png"), ("사선 모서리", S / "b9_diagonal.png")], sec=5)
        r.images("일람표", [("", S / "b8_schedules.png")], "기둥 · 문·창호 · 벽 · 보 · 코어", sec=5)
    else:
        r.images("그린 도면", [("", ROOT / "out" / "real" / "NEW1_edit_after.png")], sec=6)


# ===================== 3부 =====================
def part3(r):
    pdfs = sorted((ROOT / "samples" / "instructions").glob("*.pdf"), key=lambda p: p.stat().st_mtime)
    pdf = pdfs[-1]
    import pymupdf
    png = SLIDES / "pdf_page.png"
    pymupdf.open(pdf)[0].get_pixmap(dpi=130).save(str(png))
    r.title("3부. 회의에서 나온 지시가 PDF로 오면", ["팀 플러그인이 회의 녹음에서 변경 지시를 뽑아 '설계 변경 지시 일람표' PDF로 냅니다",
                                       "그 PDF를 그대로 읽어 도면과 관계도에 반영합니다"], sec=5)
    r.images("플러그인이 낸 PDF", [("", png)], "[1] C1 #8E · Y +300 mm · 대상 확정   /   [2] 기둥 · Y -200 mm · 확인 필요   (#8E = 플러그인이 도면에서 고른 객체의 핸들)", sec=7)
    r.terminal("PDF의 확정 지시만 도면에 반영 — 7_지시_PDF로_도면_고치기.bat", "7_지시_PDF로_도면_고치기.bat",
               [sys.executable, str(ROOT / "tools" / "show_pdf_apply.py"), str(pdf), "--no-open"],
               lambda l: not l.lstrip().startswith(("C:\\", "fig.", "주기")) and "Warning" not in l)
    r.images("반영 전 → 반영 후 (PDF 그림과 같은 6기둥 시험 도면)", [("", ROOT / "out" / "real" / "pdf_apply_before_after.png")],
             "핸들로 찾은 기둥만 300 올라가고, 기둥 이름과 세로 치수(5000 → 5300)가 따라갑니다. 확인 필요인 [2]는 건드리지 않습니다", sec=7)

    j1 = ROOT / "out" / "real" / f"instructions_{pdf.stem}.json"
    j2 = ROOT / "out" / "real" / "instructions_A12M_handle_demo.json"
    r.goto(ROOT / "out" / "editor" / "relation_editor_A12M.html")
    r.caption("같은 PDF를 실제 1층 도면의 관계도 편집기에 올립니다 — 지시 불러오기"); r.hold(2)
    y0 = r.vid("grids()")["Y2"]

    def load(path):
        with r.page.expect_file_chooser() as fc:
            r.click("#btnInstr")
        fc.value.set_files(str(path)); r.hold(1.2)

    load(j1)
    st = r.vid("state()")["instr"]; r.check(len(st) == 2 and not st[0]["applied"] and "#8E" in st[0]["note"], "지시 2건, [1]은 사람에게 남김")
    r.caption("이 PDF는 다른 도면에서 낸 것이라 핸들 #8E가 이 도면에 없습니다\nC1 타입 기둥도 3개라 스스로 정하지 않고 사람에게 묻습니다"); r.hold(6)
    r.caption("기둥 X6-Y2를 클릭하고 [1]의 '고른 줄에 적용'")
    c = r.vid("node(a[0], a[1])", ["X6", "Y2"]); r.svg("column", c["id"])
    r.panel('#instrPanel .instrApply[data-i="0"]:not([data-col])')
    r.check(r.vid("grids()")["Y2"] == y0 + 300, "Y2 +300")
    r.caption("Y2 그리드가 +300, 그 줄의 기둥 두 개가 따라가고 치수가 바뀝니다 (3000 → 2700, 1900 → 2200)"); r.hold(5)

    r.caption("되돌리고, 플러그인이 '이 도면'에서 냈을 때의 형식(핸들이 이 도면 기둥의 것)으로 다시 불러옵니다\n※ 이 파일은 그 경우를 보이기 위해 같은 형식으로 만든 시험용입니다")
    r.click("#btnUndo"); r.click("#btnUndo"); r.hold(1)
    r.check(r.vid("grids()")["Y2"] == y0, "되돌림")
    load(j2)
    st = r.vid("state()")["instr"]; r.check(st[0]["applied"] and r.vid("grids()")["Y2"] == y0 + 300, "핸들로 바로 적용")
    r.caption("핸들이 맞으면 묻지 않고 바로 적용됩니다: Y2 그리드 +300 (기둥 X6-Y2가 놓인 줄)\n그 다음은 1부와 같습니다 — 경고 확인, 변경 내보내기, 도면에 반영"); r.hold(7)
    r.caption("")


def main():
    if OUT.exists():
        shutil.rmtree(OUT, ignore_errors=True)
    SLIDES.mkdir(parents=True, exist_ok=True)
    raw = OUT / "raw"
    t0 = time.time()
    with sync_playwright() as p:
        br = p.chromium.launch(channel="msedge", headless=True)
        ctx = br.new_context(viewport={"width": W, "height": H}, record_video_dir=str(raw), record_video_size={"width": W, "height": H}, accept_downloads=True, locale="ko-KR")
        ctx.add_init_script(CURSOR_JS)
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        r = Rec(page)
        err = None
        try:
            r.title("관계도로 도면을 고치고, 관계도로 도면을 그린다", ["도면의 선을 하나씩 고치는 대신 '기둥·벽·보·문·창호가 서로 어떻게 붙어 있는가'를 고치면",
                                                   "선과 치수와 설비 위치는 따라옵니다", "~이 영상의 조작은 모두 실제 편집기에서 실제 마우스·키보드 이벤트로 진행한 것입니다"], sec=6)
            for part in PARTS:
                print(f"== {part}부")
                {"1": part1, "2": part2, "3": part3}[part](r)
            r.title("정리", ["1부: 있는 도면을 관계도로 읽어서 고쳤습니다", "2부: 관계도를 먼저 그려서 도면을 뽑았습니다", "3부: 회의에서 나온 지시(PDF)를 그대로 받아 반영했습니다",
                          "~방향은 달라도 가운데에 있는 것은 같은 관계도입니다"], sec=6)
        except Exception as e:                      # 실패해도 영상은 남겨 어디서 멈췄는지 본다
            err = e
            try:
                page.screenshot(path=str(OUT / "error.png"))
            except Exception:
                pass
        vpath = page.video.path()
        ctx.close(); br.close()
    (OUT / "record_log.txt").write_text("\n".join(r.log) + (f"\n\n오류: {err}" if err else ""), encoding="utf-8")
    print("\n".join(l for l in r.log if l.startswith("FAIL")) or f"단계 확인 {len(r.log)}개 모두 통과")
    webm = OUT / "demo.webm"
    shutil.move(vpath, webm)
    mp4 = OUT / ("시연_영상.mp4" if PARTS == ["1", "2", "3"] and not err else f"시연_영상_{'-'.join(PARTS)}{'_오류' if err else ''}.mp4")
    ff = shutil.which("ffmpeg")
    if not ff:
        try:
            import imageio_ffmpeg
            ff = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ff = None
    if ff:
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(webm), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "25", "-movflags", "+faststart", str(mp4)], check=True)
        print("saved", mp4, f"({mp4.stat().st_size / 1e6:.1f} MB)")
    print("saved", webm, f"| 녹화 {time.time() - t0:.0f}초")
    if err:
        print("오류:", err); sys.exit(1)


if __name__ == "__main__":
    main()
