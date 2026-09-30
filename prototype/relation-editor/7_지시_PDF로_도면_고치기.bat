@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
rem 플러그인이 낸 '설계 변경 지시 일람표' PDF(samples\instructions\ 의 최근 것)로 시험 도면을 고치고 전후 그림을 연다.
rem 편집기용 JSON 도 함께 만든다: out\real\instructions_*.json (편집기 상단 [지시 불러오기]로 연다)
python tools\show_pdf_apply.py %*
echo.
pause
