import sys, io, time, os; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import win32com.client, pythoncom, pywintypes
pythoncom.CoInitialize()
acad = win32com.client.Dispatch("AutoCAD.Application")
def retry(fn, n=30, w=2):
    last=None
    for _ in range(n):
        try: return fn()
        except pywintypes.com_error as e: last=e; time.sleep(w)
    raise last
doc = retry(lambda: acad.ActiveDocument)
print("active:", retry(lambda: doc.Name), "| ReadOnly:", retry(lambda: doc.ReadOnly))
outp = "C:/himec_tmp/dimcheck3.txt"
if os.path.exists(outp): os.remove(outp)
handles = ["8B54","8B55","8D64","8D65","8B53","8B51"]
lisp = '(progn (setq f (open "%s" "w")) ' % outp
for h in handles:
    lisp += ('(setq e (handent "%s")) (entmod (entget e)) (entupd e) '
             '(setq d (entget e)) (setq p13 (cdr (assoc 13 d)) p14 (cdr (assoc 14 d))) '
             '(princ (strcat "%s " (rtos (cdr (assoc 42 d)) 2 0) " " (rtos (distance p13 p14) 2 0) "\n") f) ') % (h, h)
lisp += '(close f) (princ))\n'
retry(lambda: doc.SendCommand(lisp))
for _ in range(20):
    if os.path.exists(outp) and os.path.getsize(outp) > 0: break
    time.sleep(1)
want = {"8B54":6200, "8B55":2400, "8D64":6200, "8D65":5200, "8B53":14800, "8B51":11400}
print("AutoCAD entmod 후 그룹코드 42(실측) / 정의점 13-14 거리:")
for line in open(outp, encoding="utf-8", errors="replace"):
    h, m, dist = line.split()
    m = int(float(m)); dist = int(float(dist))
    print(f"  {h}: 기대 {want[h]} / AutoCAD 실측 {m} / 정의점 거리 {dist} {'OK' if m==want[h] else ('정의점만 OK' if dist==want[h] else 'MISMATCH')}")
