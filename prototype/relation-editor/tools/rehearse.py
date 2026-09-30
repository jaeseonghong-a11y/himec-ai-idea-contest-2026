"""시연 대본 리허설: 편집기가 대본 단계를 화면 조작 그대로 진행하게 하고(#rehearsal), 단계마다 화면을 찍고, 끝에 도면 반영과 왕복 검증까지 한다.

python tools/rehearse.py           # 1부(A12M)와 2부(NEW1) 모두
python tools/rehearse.py NEW1      # 2부만
python tools/rehearse.py P3        # 3부(플러그인 PDF 지시로 고치기, A12M 편집기)만
결과: out/rehearsal/<sheet>_step<N>.png, out/rehearsal/<sheet>_log.txt, out/real/<sheet>_edited.dxf
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
EDGE = next((p for p in (Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"), Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")) if p.exists()), None)
OUT = ROOT / "out" / "rehearsal"; OUT.mkdir(parents=True, exist_ok=True)


def run(page, hashpart, shot=None, dump=False):
    url = (ROOT / "out" / "editor" / page).as_uri() + "#" + hashpart
    args = [str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1700,1050", "--virtual-time-budget=15000"]
    if shot:
        args.append(f"--screenshot={shot}")
    if dump:
        args.append("--dump-dom")
    r = subprocess.run(args + [url], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    return r.stdout if dump else ""


PARTS = {"P3": ("A12M", "rehearsal&part3")}      # 이름 → (편집기 페이지, 해시)


def rehearse(sheet):
    page_sheet, hashpart = PARTS.get(sheet, (sheet, "rehearsal"))
    page = f"relation_editor_{page_sheet}.html"
    dom = run(page, hashpart, dump=True)
    i = dom.find('id="rehearsalOut"')
    if i < 0:
        print(f"{sheet}: 리허설 결과를 찾지 못함"); return None
    j = dom.find(">", i) + 1; k = dom.find("</textarea>", j)
    import html as H
    res = json.loads(H.unescape(dom[j:k]))
    print(f"== {sheet}: {res['done']}/{res['steps']} 단계 진행")
    for l in res["log"]:
        print("  ", l)
    print(f"   경고 {len(res['warnings'])}건" + ("".join("\n     - " + w for w in res["warnings"][:10])))
    (OUT / f"{sheet}_log.txt").write_text("\n".join(res["log"]) + "\n\n경고\n" + "\n".join(res["warnings"]), encoding="utf-8")
    for n in range(1, res["steps"] + 1):      # 단계별 화면
        run(page, hashpart.replace("rehearsal", f"rehearsal={n}"), shot=str(OUT / f"{sheet}_step{n:02d}.png"))
    ch = OUT / f"changes_{sheet}.json"
    ch.write_text(json.dumps(res["changes"], ensure_ascii=False, indent=1), encoding="utf-8")
    ex = OUT / f"expected_{sheet}.json"
    ex.write_text(json.dumps(res["expected"], ensure_ascii=False, indent=1), encoding="utf-8")
    if res["done"] == res["steps"]:
        t0 = time.time()
        r = subprocess.run([sys.executable, str(ROOT / "propagate" / "apply_edits.py"), page_sheet, str(ch), str(ex), "--quick"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        lines = [l for l in r.stdout.splitlines() if l.strip().startswith(("CR-", "saved", "벽 맞물림", "겹침", "FAIL")) or "오류" in l or ("일치" in l and "/" in l)]
        tot = next((l.strip() for l in r.stdout.splitlines() if "일치" in l and "/" in l), "왕복 검증 없음")
        print(f"   도면 반영 {time.time() - t0:.0f}초, 왕복 검증 {tot}, 기록 {len(lines)}줄" + ("" if r.returncode == 0 else " (실패)"))
        for l in lines[:40]:
            print("    ", l[:150])
        with (OUT / f"{sheet}_log.txt").open("a", encoding="utf-8") as f:
            f.write(f"\n\n도면 반영 {time.time() - t0:.0f}초, 왕복 검증 {tot}\n" + "\n".join(l for l in lines if l.strip().startswith("FAIL") or "오류" in l))
        if r.returncode:
            print(r.stderr[-600:])
    return res


if __name__ == "__main__":
    for sheet in (sys.argv[1:] or ["P3", "NEW1", "A12M"]):      # 3부와 1부가 같은 A12M 결과 파일을 쓰므로 1부를 마지막에 (시나리오 그림은 1부 결과)
        rehearse(sheet)
    print("saved", OUT)
