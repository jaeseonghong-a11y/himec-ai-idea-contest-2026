"""시연 영상의 첫 장면: 실무 도면(가린 1층 평면도)을 AutoCAD에서 여는 모습을 화면 녹화한다.

python tools/record_autocad_intro.py            # out/video_intro/autocad_intro.mp4
python tools/record_autocad_intro.py --shot     # 녹화 없이 AutoCAD 창 그림 한 장만 (자를 범위 확인용)

- AutoCAD 창만 찍는다(PrintWindow). 창이 다른 창 뒤에 있어도 되고, 바탕 화면의 다른 것은 찍히지 않는다.
- 여는 파일은 사무소·대지 정보를 가린 복사본이다. 제목 줄(로그인 이름이 보이는 곳)은 잘라 낸다.
- 열기, 전체 보기, 평면 확대, 세부 확대는 AutoCAD COM 명령으로 한다.
필요: AutoCAD, pywin32, ffmpeg
"""
import ctypes
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pythoncom
import pywintypes
import win32com.client
import win32con
import win32gui

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "video_intro"; OUT.mkdir(parents=True, exist_ok=True)
SRC = next((p for p in (ROOT / "masked_dxf" / "A12.dxf", ROOT / "real_dxf" / "A12.dxf") if p.exists() and (p.parent.name == "masked_dxf" or not (ROOT / "masked_dxf").exists())), None)
TMP = Path("C:/himec_tmp"); TMP.mkdir(exist_ok=True)
WORK = TMP / "A-12_1층_평면도.dxf"
TOP_CUT = 34            # 제목 줄 높이(픽셀). 로그인 이름이 보이므로 잘라 낸다
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


def retry(fn, n=60, w=1.5):
    last = None
    for _ in range(n):
        try:
            return fn()
        except (pywintypes.com_error, AttributeError) as e:
            last = e; time.sleep(w)
    raise last


def pt(x, y):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (float(x), float(y), 0.0))


CUT = (8, 36, 8, 8)      # 왼쪽, 위, 오른쪽, 아래에서 잘라 낼 픽셀. 위쪽은 제목 줄(로그인 이름이 보임)
FPS = 10


class Grabber:
    """AutoCAD 창만 찍는다(PrintWindow). 다른 창에 가려져 있어도 되고, 바탕 화면의 다른 것은 찍히지 않는다."""

    def __init__(self, hwnd):
        self.hwnd = hwnd
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        self.w, self.h = r - l, b - t
        self.box = (CUT[0], CUT[1], (self.w - CUT[2] - CUT[0]) // 2 * 2 + CUT[0], (self.h - CUT[3] - CUT[1]) // 2 * 2 + CUT[1])
        self.size = (self.box[2] - self.box[0], self.box[3] - self.box[1])

    def grab(self):
        from PIL import Image
        import win32ui
        hdc = win32gui.GetWindowDC(self.hwnd); mdc = win32ui.CreateDCFromHandle(hdc); sdc = mdc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap(); bmp.CreateCompatibleBitmap(mdc, self.w, self.h); sdc.SelectObject(bmp)
        ctypes.windll.user32.PrintWindow(self.hwnd, sdc.GetSafeHdc(), 2)
        im = Image.frombuffer("RGB", (self.w, self.h), bmp.GetBitmapBits(True), "raw", "BGRX", 0, 1).crop(self.box)
        win32gui.DeleteObject(bmp.GetHandle()); sdc.DeleteDC(); mdc.DeleteDC(); win32gui.ReleaseDC(self.hwnd, hdc)
        return im


def main():
    import json
    import threading
    if SRC is None:
        sys.exit("가린 도면(masked_dxf/A12.dxf)이 없습니다. tools/mask_dxf.py 로 먼저 만드세요.")
    shutil.copyfile(SRC, WORK)
    pythoncom.CoInitialize()
    acad = win32com.client.Dispatch("AutoCAD.Application")
    retry(lambda: setattr(acad, "Visible", True))
    for d in list(retry(lambda: acad.Documents)):                 # 앞서 열어 둔 같은 이름의 도면은 닫는다
        try:
            if d.Name == WORK.name:
                d.Close(False)
        except Exception:
            pass
    d0 = retry(lambda: acad.Documents.Add())
    for var, val in (("PROXYNOTICE", 0), ("FILEDIA", 0), ("CMDDIA", 0)):
        try:
            retry(lambda: d0.SetVariable(var, val), n=4)
        except Exception:
            pass
    hwnd = retry(lambda: acad.HWND)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)           # 앞으로 가져오지는 않는다(쓰고 있는 화면을 방해하지 않음)
    time.sleep(2.0)
    g = Grabber(hwnd)
    print(f"AutoCAD 창 {g.w}x{g.h} → 영상 {g.size[0]}x{g.size[1]}")
    if "--shot" in sys.argv:
        doc = retry(lambda: acad.Documents.Open(str(WORK), True)); time.sleep(4)
        retry(lambda: acad.ZoomExtents()); time.sleep(2)
        g.grab().save(OUT / "shot.png"); print("saved", OUT / "shot.png")
        retry(lambda: doc.Close(False)); return

    ff = shutil.which("ffmpeg")
    mp4 = OUT / "autocad_intro.mp4"
    rec = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{g.size[0]}x{g.size[1]}", "-framerate", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", "25", str(mp4)], stdin=subprocess.PIPE)
    stop = threading.Event(); t0 = time.time(); marks = {}; count = [0]

    def loop():                                                    # 일정한 간격으로 창을 찍어 ffmpeg 에 넘긴다
        while not stop.is_set():
            due = t0 + count[0] / FPS
            if time.time() < due:
                time.sleep(max(0.0, due - time.time())); continue
            try:
                rec.stdin.write(g.grab().tobytes())
            except Exception:
                break
            count[0] += 1
    th = threading.Thread(target=loop, daemon=True); th.start()
    mark = lambda k: marks.__setitem__(k, round(time.time() - t0, 2))
    doc = None
    try:
        time.sleep(2.0); mark("open")
        doc = retry(lambda: acad.Documents.Open(str(WORK), True))          # 읽기 전용으로 연다
        time.sleep(2.5)
        retry(lambda: acad.ZoomExtents()); mark("extents"); time.sleep(5.0)
        (x0, y0, _), (x1, y1, _) = retry(lambda: (doc.GetVariable("EXTMIN"), doc.GetVariable("EXTMAX")))
        W, H = x1 - x0, y1 - y0
        retry(lambda: acad.ZoomWindow(pt(x0 + W * 0.08, y0 + H * 0.12), pt(x0 + W * 0.86, y0 + H * 0.82))); mark("plan"); time.sleep(5.0)
        retry(lambda: acad.ZoomWindow(pt(x0 + W * 0.22, y0 + H * 0.36), pt(x0 + W * 0.56, y0 + H * 0.76))); mark("detail"); time.sleep(5.0)
        retry(lambda: acad.ZoomExtents()); mark("back"); time.sleep(3.0)
    finally:
        mark("end"); stop.set(); th.join(timeout=5)
        rec.stdin.close(); rec.wait(timeout=60)
    marks["frames"] = count[0]; marks["size"] = list(g.size); marks["extents"] = marks.get("extents")
    (OUT / "marks.json").write_text(json.dumps(marks), encoding="utf-8")
    print("saved", mp4, marks)
    try:
        retry(lambda: doc.Close(False), n=5)
    except Exception:
        pass


if __name__ == "__main__":
    main()
