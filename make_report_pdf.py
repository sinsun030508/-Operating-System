"""
docs/report.md → docs/report.pdf (A4) 변환기
  필요: pip install markdown  +  Chrome/Chromium/Edge 중 하나 (명령줄 인쇄 기능을 쓴다)
  사용: python make_report_pdf.py   (브라우저를 못 찾으면 CHROME 환경변수로 경로 지정)
"""
import os, pathlib, shutil, subprocess, glob, re
import markdown

HERE = pathlib.Path(__file__).resolve().parent
DOCS = HERE / "docs"
CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font-family: 'Noto Sans KR','Pretendard','Malgun Gothic','Apple SD Gothic Neo','WenQuanYi Zen Hei',sans-serif;
       font-size: 10.5pt; line-height: 1.65; color: #1b1d2a; }
h1 { font-size: 21pt; margin: 0 0 4pt; color: #0b0d2e; }
h2 { font-size: 13.5pt; margin: 18pt 0 6pt; padding-bottom: 3pt; border-bottom: 2px solid #5ae6ff; color: #0b0d2e; }
p, li { margin: 3pt 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; font-size: 9.2pt; page-break-inside: avoid; }
th, td { border: 1px solid #c9cde0; padding: 4pt 6pt; vertical-align: top; }
th { background: #eef6ff; }
blockquote { margin: 8pt 0; padding: 6pt 10pt; background: #f4f0ff; border-left: 4px solid #ff5ac8; }
code { font-family: 'JetBrains Mono','Consolas',monospace; font-size: 9pt; background: #f1f2f7; padding: 0 3pt; border-radius: 3px; }
img { width: 100%; border-radius: 6px; margin: 6pt 0; page-break-inside: avoid; }
hr { border: none; border-top: 1px solid #d5d8e6; margin: 10pt 0; }
a { color: #1a5fd0; text-decoration: none; }
.keep { break-inside: avoid; page-break-inside: avoid; }
td:first-child { white-space: nowrap; }
"""

def find_browser():
    cands = [os.environ.get("CHROME", ""), "/opt/pw-browsers/chromium/chrome-linux64/chrome",
             *glob.glob("/opt/pw-browsers/chromium-*/chrome-linux64/chrome"),
             r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    cands += [shutil.which(n) or "" for n in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge")]
    for c in cands:
        if c and os.path.exists(c): return c
    raise SystemExit("Chrome/Edge 를 찾지 못했습니다. CHROME 환경변수에 브라우저 경로를 넣어 주세요.")

def main():
    md = (DOCS / "report.md").read_text(encoding="utf-8")
    body = markdown.markdown(md, extensions=["tables", "fenced_code"])
    # 제목이 쪽 끝에 혼자 남지 않도록 h2 와 바로 다음 블록을 한 덩어리로 묶는다
    body = re.sub(r"(<h2>.*?</h2>\s*<(p|ul|ol|blockquote)>.*?</\2>)", r"<div class='keep'>\1</div>", body, flags=re.S)
    html = f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
    tmp = DOCS / "_report.html"
    tmp.write_text(html, encoding="utf-8")
    out = DOCS / "report.pdf"
    subprocess.run([find_browser(), "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={out}", tmp.as_uri()], check=True, capture_output=True)
    tmp.unlink()
    print("saved", out)

if __name__ == "__main__":
    main()
