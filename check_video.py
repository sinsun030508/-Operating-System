"""
제출 전 과제 조건 검사:  python check_video.py [영상 경로]
  자동 판정: 해상도 360x640 · 비율 9:16 · 길이 60초 · 소리가 실제로 들어 있는지
  눈으로 확인: 0-5초(타이틀) · 5-55초(내용) · 55-60초(한줄 평) 장면을 check_sections.png 로 뽑는다
  하나라도 어긋나면 종료 코드 1
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, DUR, TOL = 360, 640, 60.0, 0.1

def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)

def audio_rms(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    return float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0

def frame(path, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1",
                          "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.frombytes("RGB", (W, H), raw) if len(raw) == W * H * 3 else Image.new("RGB", (W, H))

def main():
    default = os.path.join(HERE, "media", "quantum_os_ai.mp4")
    if not os.path.exists(default): default = os.path.join(HERE, "media", "quantum_os_shorts.mp4")
    path = sys.argv[1] if len(sys.argv) > 1 else default
    info = probe(path)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    rms = audio_rms(path) if a else 0.0
    checks = [
        ("해상도 360x640", v and (v["width"], v["height"]) == (W, H), f"{v['width']}x{v['height']}" if v else "영상 없음"),
        ("비율 9:16", v and v["width"] * 16 == v["height"] * 9, f"{v['width']}:{v['height']}" if v else "-"),
        ("길이 60초", abs(dur - DUR) <= TOL, f"{dur:.2f}초"),
        ("소리 트랙", a is not None, a["codec_name"] if a else "없음"),
        ("소리가 무음이 아님", rms > 0.005, f"RMS {rms:.3f}"),
    ]
    print(f"\n검사 대상: {path}")
    ok = True
    for name, passed, val in checks:
        ok &= bool(passed)
        print(f"  {'통과' if passed else '실패'}  {name:<14} ({val})")
    # 구간별 장면: 0-5 타이틀 / 5-55 내용 / 55-60 한줄 평
    times = [(1.5, "타이틀"), (4.0, "타이틀"), (7, "내용 시작"), (30, "내용"), (52, "내용 끝"), (57.5, "한줄 평")]
    sheet = Image.new("RGB", (W * len(times), H + 40), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    try:
        import make_video as mv
        from PIL import ImageFont
        font = ImageFont.truetype(mv.KO, 22)
    except Exception:
        font = None
    for i, (t, label) in enumerate(times):
        sheet.paste(frame(path, t), (i * W, 40))
        d.text((i * W + 10, 8), f"{t}초 · {label}", fill=(20, 20, 40), font=font)
    out = os.path.join(HERE, "check_sections.png")
    sheet.save(out)
    print(f"  확인  구간별 장면 → {out}  (0~5초에 제목, 55~60초에 한줄 평이 보이는지)")
    print("\n결과:", "모든 자동 검사 통과" if ok else "조건 위반이 있습니다")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
