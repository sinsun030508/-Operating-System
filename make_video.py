"""
양자 컴퓨터 × 운영체제 1분 쇼츠 생성기
  - 출력: 360x640 (9:16), 30fps, 60초, H.264 + AAC
  - 원리: 매 프레임을 720x1280(2배)로 그린 뒤 360x640으로 줄여(슈퍼샘플링) 계단 현상을 없앤다.
          프레임은 디스크에 저장하지 않고 ffmpeg 표준입력으로 바로 흘려보낸다(파이프).
사용법: python3 make_video.py [--preview]   (--preview: 장면별 대표 프레임 PNG만 저장)
"""
import math, random, subprocess, sys, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 360, 640          # 최종 해상도
SS = 2                   # 슈퍼샘플 배율
FPS, DUR = 30, 60
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- 폰트 (Windows · Mac · Linux 순서로 있는 것을 고른다) ----------
# 더 예쁜 폰트를 쓰고 싶으면 이 파일 옆 fonts/ 폴더에 넣는다 (예: NotoSansKR-Bold.ttf). 그쪽을 먼저 찾는다.
try: sys.stdout.reconfigure(errors="replace")   # Windows 콘솔에서 특수문자 출력 오류 방지
except Exception: pass
_LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
_WIN = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
def _pick(kind, *cands):
    for c in cands:
        p = c if os.path.isabs(c) else os.path.join(_LOCAL, c)
        if os.path.exists(p): return p
    raise SystemExit(f"[폰트 없음] {kind} 폰트를 찾지 못했습니다. fonts/ 폴더에 .ttf/.otf 를 넣어 주세요.")
KO = _pick("한글", "NotoSansKR-Bold.ttf", "NotoSansKR-Bold.otf", "Pretendard-Bold.otf",
           os.path.join(_WIN, "malgunbd.ttf"), os.path.join(_WIN, "malgun.ttf"),
           "/System/Library/Fonts/AppleSDGothicNeo.ttc", "/Library/Fonts/AppleGothic.ttf",
           "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
           "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")
EN_B = _pick("영문 굵게", "Inter-Black.otf", "/usr/share/fonts/opentype/inter/Inter-Black.otf",
             os.path.join(_WIN, "seguibl.ttf"), os.path.join(_WIN, "ariblk.ttf"), os.path.join(_WIN, "arialbd.ttf"),
             "/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", KO)
EN_M = _pick("영문", "Inter-Bold.otf", "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
             os.path.join(_WIN, "segoeuib.ttf"), os.path.join(_WIN, "arialbd.ttf"),
             "/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", KO)
MONO = _pick("고정폭", "JetBrainsMono-Bold.ttf", "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
             os.path.join(_WIN, "consolab.ttf"), os.path.join(_WIN, "cour.ttf"),
             "/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf", EN_M)
SYM = _pick("기호", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            os.path.join(_WIN, "seguisym.ttf"), os.path.join(_WIN, "segoeuib.ttf"),
            "/System/Library/Fonts/Apple Symbols.ttf", "/Library/Fonts/Arial Unicode.ttf", EN_M)
_fc = {}
def F(path, size):
    key = (path, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(path, int(size * SS))
    return _fc[key]

# 폰트에 없는 글자는 □ 로 찍힌다 → 비슷한 글자로 바꿔 찍는다
_SUB = {"ⁿ": "^n", "⟩": ">", "⟨": "<", "→": "->", "←": "<-", "▼": "v", "▌": "|", "μ": "u", "—": "-", "×": "x", "·": "-"}
_has = {}
def _missing(path, ch):
    key = (path, ch)
    if key not in _has:
        f = F(path, 20)
        a, b = f.getmask(ch), f.getmask("\uffff")
        _has[key] = a.getbbox() == b.getbbox() and bytes(a) == bytes(b)
    return _has[key]
def safe(s, path):
    return "".join(_SUB[c] if c in _SUB and _missing(path, c) else c for c in s)

# ---------- 색 ----------
BG_TOP = (8, 10, 30); BG_BOT = (28, 10, 52)
CYAN = (90, 230, 255); MAG = (255, 90, 200); GOLD = (255, 205, 90)
WHITE = (240, 244, 255); DIM = (150, 160, 200); RED = (255, 95, 95); GREEN = (110, 240, 160)

# ---------- 시간 도우미 ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_back(x):
    x = clamp(x); c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def win(t, a, b, f=0.35):
    """[a,b] 동안 보이고 앞뒤 f초 동안 서서히 나타나고 사라지는 불투명도"""
    return ease((t - a) / f) * ease((b - t) / f)

# ---------- 배경(고정 별 + 그라데이션) ----------
_grad = None
def background():
    global _grad
    if _grad is None:
        y = np.linspace(0, 1, H * SS)[:, None, None]
        top = np.array(BG_TOP)[None, None, :]; bot = np.array(BG_BOT)[None, None, :]
        arr = (top * (1 - y) + bot * y) * np.ones((1, W * SS, 1))
        _grad = Image.fromarray(arr.astype(np.uint8), "RGB")
    return _grad.copy()

rng = random.Random(7)
STARS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.4, 1.4), rng.uniform(0, 6.28), rng.uniform(0.5, 2))
         for _ in range(70)]
def draw_stars(d, t, drift=6):
    for x, y, r, ph, sp in STARS:
        a = int(120 + 110 * math.sin(t * sp + ph))
        yy = (y + t * drift * r) % H
        d.ellipse([(x - r) * SS, (yy - r) * SS, (x + r) * SS, (yy + r) * SS], fill=(200, 220, 255, max(0, a)))

# ---------- 그리기 도우미 (좌표는 360x640 기준) ----------
def S(v): return v * SS
def text(d, s, x, y, size, color, alpha=1.0, font=KO, anchor="mm", spacing=6):
    if alpha <= 0.01: return
    s = safe(s, font)
    d.multiline_text((S(x), S(y)), s, font=F(font, size), fill=color + (int(255 * alpha),),
                     anchor=anchor, align="center", spacing=S(spacing))

def glow_layer(img, draw_fn, radius=10, strength=1.0):
    """draw_fn으로 그린 것을 흐리게 번지게 해서 더한다 (네온 효과)"""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer, "RGBA"))
    blur = layer.filter(ImageFilter.GaussianBlur(S(radius)))
    if strength != 1.0:
        a = blur.getchannel("A").point(lambda v: min(255, int(v * strength)))
        blur.putalpha(a)
    img.paste(blur, (0, 0), blur)
    img.paste(layer, (0, 0), layer)

def rrect(d, x0, y0, x1, y1, r, fill=None, outline=None, width=1):
    d.rounded_rectangle([S(x0), S(y0), S(x1), S(y1)], radius=S(r), fill=fill, outline=outline, width=max(1, int(round(S(width)))))

def line(d, pts, color, width=2):
    d.line([(S(x), S(y)) for x, y in pts], fill=color, width=max(1, int(round(S(width)))), joint="curve")

def dot(d, x, y, r, color):
    d.ellipse([S(x - r), S(y - r), S(x + r), S(y + r)], fill=color)

def arrow(d, x0, y0, x1, y1, color, width=3, head=9):
    line(d, [(x0, y0), (x1, y1)], color, width)
    ang = math.atan2(y1 - y0, x1 - x0)
    p1 = (x1 - head * math.cos(ang - 0.45), y1 - head * math.sin(ang - 0.45))
    p2 = (x1 - head * math.cos(ang + 0.45), y1 - head * math.sin(ang + 0.45))
    d.polygon([(S(x1), S(y1)), (S(p1[0]), S(p1[1])), (S(p2[0]), S(p2[1]))], fill=color)

def bloch(d, cx, cy, R, theta, phi, alpha=1.0, vec_len=1.0, color=CYAN, labels=True, blur_noise=0.0, t=0.0):
    """블로흐 구: 큐비트 상태를 구 위의 한 점(화살표)으로 나타낸 그림"""
    a = int(255 * alpha)
    if a <= 2: return
    d.ellipse([S(cx - R), S(cy - R), S(cx + R), S(cy + R)], outline=(120, 140, 220, int(a * 0.8)), width=S(2))
    # 적도 (뒤쪽은 점선)
    for i in range(48):
        u0, u1 = i / 48 * 2 * math.pi, (i + 0.6) / 48 * 2 * math.pi
        back = math.sin(u0) < 0
        if back and i % 2: continue
        p0 = (cx + R * math.cos(u0), cy + 0.28 * R * math.sin(u0))
        p1 = (cx + R * math.cos(u1), cy + 0.28 * R * math.sin(u1))
        line(d, [p0, p1], (120, 140, 220, int(a * (0.35 if back else 0.8))), 1.5)
    line(d, [(cx, cy - R), (cx, cy + R)], (120, 140, 220, int(a * 0.4)), 1)
    if labels:
        text(d, "|0⟩", cx, cy - R - 13, 14, WHITE, alpha, font=SYM)
        text(d, "|1⟩", cx, cy + R + 13, 14, WHITE, alpha, font=SYM)
    # 상태 벡터
    L = R * vec_len
    jx = blur_noise * math.sin(t * 37) * R * 0.15
    jy = blur_noise * math.cos(t * 29) * R * 0.15
    ex = cx + L * math.sin(theta) * math.cos(phi) + jx
    ey = cy - L * math.cos(theta) + 0.28 * L * math.sin(theta) * math.sin(phi) + jy
    if vec_len > 0.05:
        arrow(d, cx, cy, ex, ey, color + (a,), 3, 9)
        dot(d, ex, ey, 4, color + (a,))
    dot(d, cx, cy, 2.5, (220, 230, 255, a))

def chapter(d, t, num, label, a):
    """왼쪽 위 챕터 태그"""
    if a <= 0.01: return
    rrect(d, 16, 34, 16 + 30 + len(label) * 13, 58, 12, fill=(255, 255, 255, int(28 * a)),
          outline=CYAN + (int(150 * a),), width=1)
    text(d, num, 30, 46, 12, CYAN, a, font=EN_B)
    text(d, label, 46, 46, 12, WHITE, a, anchor="lm")

def progress(d, t):
    """화면 맨 위 진행 막대 (쇼츠 느낌)"""
    rrect(d, 16, 16, W - 16, 20, 2, fill=(255, 255, 255, 40))
    x1 = 16 + (W - 32) * clamp(t / DUR)
    if x1 > 18: rrect(d, 16, 16, x1, 20, 2, fill=CYAN + (230,))

# =====================================================================
# 장면들 (t: 전체 시각, 초)
# =====================================================================
def sc_title(img, d, t):                       # 0~5s 타이틀
    a = win(t, 0, 5.0, 0.4)
    # 회전하는 블로흐 구 + 궤도 입자
    k = ease_out(t / 1.2)
    glow_layer(img, lambda g: bloch(g, W / 2, 205, 70 * k, 1.1 + 0.4 * math.sin(t * 1.3), t * 2.2,
                                     alpha=a, labels=False, color=CYAN), radius=6, strength=1.2)
    for i in range(3):
        u = t * (1.4 + i * 0.5) + i * 2.1
        ox = W / 2 + 105 * math.cos(u); oy = 205 + 36 * math.sin(u) * (1 if i % 2 else -1)
        dot(d, ox, oy, 3, (MAG if i == 1 else GOLD) + (int(220 * a),))
    t1 = ease_back((t - 0.5) / 0.6); t2 = ease_back((t - 0.9) / 0.6)
    text(d, "큐비트에게도", W / 2, 340 + 20 * (1 - t1), 30, WHITE, a * clamp((t - 0.5) / 0.3))
    def title2(g):
        text(g, "운영체제가", W / 2, 388 + 20 * (1 - t2), 38, CYAN, a * clamp((t - 0.9) / 0.3))
        text(g, "필요할까?", W / 2, 436 + 20 * (1 - t2), 38, CYAN, a * clamp((t - 0.9) / 0.3))
    glow_layer(img, title2, radius=8, strength=0.9)
    a3 = a * clamp((t - 1.8) / 0.4)
    rrect(d, W / 2 - 95, 486, W / 2 + 95, 512, 13, outline=MAG + (int(200 * a3),), width=1)
    text(d, "QUANTUM  ×  OS", W / 2, 499, 13, MAG, a3, font=EN_M)
    text(d, "운영체제 · 1분 영상", W / 2, 560, 13, DIM, a3)

def sc_bit_qubit(img, d, t):                   # 5~13s 비트 vs 큐비트
    a = win(t, 5, 13)
    chapter(d, t, "01", "비트와 큐비트", a)
    lt = t - 5
    # 왼쪽: 비트 (0/1 깜빡이는 스위치)
    aL = a * ease((lt - 0.2) / 0.4)
    bit = int(lt * 1.5) % 2
    rrect(d, 40, 150, 160, 270, 18, fill=(255, 255, 255, int(18 * aL)), outline=GOLD + (int(220 * aL),), width=2)
    text(d, str(bit), 100, 205, 64, GOLD, aL, font=EN_B)
    text(d, "비트", 100, 295, 20, WHITE, aL)
    text(d, "0 또는 1", 100, 322, 15, DIM, aL)
    # 오른쪽: 큐비트 (블로흐 구)
    aR = a * ease((lt - 1.4) / 0.4)
    glow_layer(img, lambda g: bloch(g, 262, 210, 52, 1.57 + 1.0 * math.sin(lt * 1.6), lt * 2.5,
                                     alpha=aR, color=CYAN), radius=5)
    text(d, "큐비트", 262, 295, 20, CYAN, aR)
    text(d, "0과 1을 동시에", 262, 322, 15, DIM, aR)
    # 하단 설명
    a2 = a * ease((lt - 3.0) / 0.4)
    rrect(d, 30, 380, W - 30, 490, 16, fill=(90, 230, 255, int(22 * a2)))
    text(d, "중첩 (Superposition)", W / 2, 410, 20, CYAN, a2)
    text(d, "측정하기 전까지는\n여러 상태가 확률로 겹쳐 있다", W / 2, 455, 15, WHITE, a2)
    a3 = a * ease((lt - 5.0) / 0.4)
    text(d, "그래서 한 번에 많은 경우를 다룬다 →", W / 2, 540, 14, GOLD, a3)

def sc_power(img, d, t):                       # 13~20s 2^n
    a = win(t, 13, 20)
    chapter(d, t, "02", "지수적으로 커지는 상태", a)
    lt = t - 13
    n = int(clamp(lt / 4.5) * 50) if lt > 0.6 else 1
    n = max(1, n)
    # 큐비트 점 격자 (10x5)
    for i in range(50):
        r, c = divmod(i, 10)
        x = 63 + c * 26; y = 130 + r * 26
        on = i < n
        col = CYAN if on else (70, 80, 120)
        dot(d, x, y, 7 if on else 5, col + (int(255 * a * (1 if on else 0.6)),))
    text(d, "큐비트", W / 2 - 28, 290, 18, WHITE, a)
    text(d, f"{n}", W / 2 + 34, 290, 26, CYAN, a, font=EN_B)
    text(d, "개면 동시에 다루는 상태 수", W / 2, 330, 15, DIM, a)
    val = 2 ** n
    s = f"{val:,}"
    size = 34 if len(s) < 12 else (26 if len(s) < 18 else 20)
    glow_layer(img, lambda g: text(g, s, W / 2, 385, size, GOLD, a, font=EN_B), radius=6)
    text(d, "2ⁿ", W / 2, 425, 18, GOLD, a * 0.8, font=SYM)
    a2 = a * ease((lt - 5.0) / 0.4)
    rrect(d, 30, 470, W - 30, 560, 16, fill=(255, 205, 90, int(22 * a2)))
    text(d, "50개만 있어도 약 1,126조\n일반 컴퓨터로는 흉내 내기 벅차다", W / 2, 515, 15, WHITE, a2)

def sc_decoherence(img, d, t):                 # 20~28s 결어긋남
    a = win(t, 20, 28)
    chapter(d, t, "03", "문제: 큐비트는 금방 잊는다", a)
    lt = t - 20
    life = clamp(1 - (lt - 1.0) / 4.0)            # 1 → 0
    noise = (1 - life) * 1.2
    col = tuple(int(CYAN[i] * life + RED[i] * (1 - life)) for i in range(3))
    bloch(d, W / 2, 200, 70, 1.2, lt * 2.0, alpha=a, vec_len=max(0.0, life), color=col,
          blur_noise=noise, t=lt)
    # 수명 막대
    rrect(d, 50, 315, W - 50, 333, 9, outline=(255, 255, 255, int(120 * a)), width=1)
    if life > 0.01:
        rrect(d, 52, 317, 52 + (W - 104) * life, 331, 7, fill=col + (int(230 * a),))
    text(d, "남은 수명", 50, 300, 12, DIM, a, anchor="lm")
    text(d, "수백 μs 안팎", W - 50, 300, 12, col, a, anchor="rm")
    a2 = a * ease((lt - 1.2) / 0.4)
    text(d, "결어긋남 (Decoherence)", W / 2, 375, 21, RED, a2)
    text(d, "열·진동·전자기 잡음 때문에\n중첩 상태가 금방 무너진다", W / 2, 420, 15, WHITE, a2)
    a3 = a * ease((lt - 4.6) / 0.4)
    rrect(d, 26, 470, W - 26, 575, 16, fill=(90, 230, 255, int(24 * a3)), outline=CYAN + (int(160 * a3),), width=1)
    text(d, "OS 관점으로 보면", W / 2, 494, 13, DIM, a3)
    text(d, "모든 작업에 '마감'이 있는\n실시간 스케줄링 문제!", W / 2, 535, 17, CYAN, a3)

def os_card_frame(d, t, a, num, cls, qnt, ref):
    """OS 개념 대응 카드 공통 틀: 위=고전 OS, 아래=양자 OS"""
    chapter(d, t, num, "OS가 할 일", a)
    rrect(d, 24, 80, W - 24, 130, 14, fill=(255, 255, 255, int(20 * a)))
    text(d, "고전 OS", 44, 105, 12, DIM, a, anchor="lm")
    text(d, cls, W - 44, 105, 17, WHITE, a, anchor="rm")
    text(d, "▼", W / 2, 146, 14, CYAN, a)
    rrect(d, 24, 162, W - 24, 212, 14, fill=(90, 230, 255, int(30 * a)), outline=CYAN + (int(180 * a),), width=1)
    text(d, "양자 OS", 44, 187, 12, CYAN, a, anchor="lm")
    text(d, qnt, W - 44, 187, 17, CYAN, a, anchor="rm")
    if ref:
        text(d, ref, W / 2, 590, 11, DIM, a * 0.9)

def sc_sched(img, d, t):                       # 28~33s 스케줄링
    a = win(t, 28, 33, 0.3); lt = t - 28
    os_card_frame(d, t, a, "04", "CPU 스케줄링", "QPU 작업 스케줄링", "예) QOS — OSDI '25, TU München")
    # QPU 격자 (4x4 큐비트)
    gx, gy = 196, 300
    jobs = [(MAG, "A", [(0, 0), (0, 1), (1, 0), (1, 1)]), (GOLD, "B", [(0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]),
            (GREEN, "C", [(2, 0), (3, 0), (3, 1), (2, 1)])]
    text(d, "QPU", gx + 52, gy - 22, 13, WHITE, a, font=EN_M)
    for r in range(4):
        for c in range(4):
            dot(d, gx + c * 35, gy + r * 35, 9, (70, 80, 120, int(255 * a)))
    for k, (col, name, cells) in enumerate(jobs):
        p = ease_out((lt - 0.4 - k * 0.7) / 0.6)
        # 대기열에서 날아오기
        qx, qy = 60, 300 + k * 50
        rrect(d, qx - 26, qy - 15, qx + 26, qy + 15, 8, fill=col + (int(200 * a * (1 - p)),))
        text(d, f"회로 {name}", qx, qy, 12, (20, 20, 40), a * (1 - p))
        for (r, c) in cells:
            x = qx + (gx + c * 35 - qx) * p; y = qy + (gy + r * 35 - qy) * p
            dot(d, x, y, 9 * max(p, 0.4), col + (int(255 * a * max(p, 0.15)),))
    text(d, "대기열", 60, 270, 12, DIM, a)
    a2 = a * ease((lt - 2.6) / 0.4)
    text(d, "여러 사용자의 회로를\n한 장비에 나눠 실어 대기 시간을 줄인다", W / 2, 490, 14, WHITE, a2)

def sc_memory(img, d, t):                      # 33~38s 가상 큐비트 주소
    a = win(t, 33, 38, 0.3); lt = t - 33
    os_card_frame(d, t, a, "05", "가상 메모리", "가상 큐비트 주소", "예) QNodeOS의 QMMU — Nature, 2025")
    text(d, "프로그램이 보는 큐비트", 90, 255, 12, DIM, a)
    text(d, "실제 큐비트", 275, 255, 12, DIM, a)
    mapping = [2, 0, 3, 1]
    for i in range(4):
        y = 290 + i * 45
        rrect(d, 50, y - 15, 130, y + 15, 8, outline=MAG + (int(220 * a),), width=2)
        text(d, f"v{i}", 90, y, 14, MAG, a, font=EN_M)
        rrect(d, 235, y - 15, 315, y + 15, 8, outline=CYAN + (int(220 * a),), width=2)
        text(d, f"q{i}", 275, y, 14, CYAN, a, font=EN_M)
    for i, j in enumerate(mapping):
        p = ease_out((lt - 0.5 - i * 0.35) / 0.5)
        y0 = 290 + i * 45; y1 = 290 + j * 45
        x1 = 132 + (233 - 132) * p; yy = y0 + (y1 - y0) * p
        if p > 0.02: arrow(d, 132, y0, x1, yy, (255, 255, 255, int(200 * a)), 2, 7)
    a2 = a * ease((lt - 2.4) / 0.4)
    text(d, "프로그램은 실제 위치를 몰라도 된다\n상태 좋은 큐비트는 OS가 골라 준다", W / 2, 510, 14, WHITE, a2)

def sc_driver(img, d, t):                      # 38~43s 하이브리드 + 드라이버
    a = win(t, 38, 43, 0.3); lt = t - 38
    os_card_frame(d, t, a, "06", "디바이스 드라이버", "QPU = 주변 장치", "QNodeOS: 다이아몬드 NV · 이온 트랩 드라이버 시연")
    layers = [("응용 프로그램", WHITE), ("양자 OS  (고전 CPU 위에서 동작)", CYAN), ("드라이버", GOLD)]
    for i, (name, col) in enumerate(layers):
        p = ease_back((lt - 0.3 - i * 0.35) / 0.5)
        y = 265 + i * 52
        rrect(d, 40, y - 18 + 15 * (1 - p), W - 40, y + 18 + 15 * (1 - p), 10,
              fill=col + (int(40 * a * clamp(p)),), outline=col + (int(220 * a * clamp(p)),), width=1)
        text(d, name, W / 2, y + 15 * (1 - p), 14, col, a * clamp(p))
    p = ease_out((lt - 1.5) / 0.5)
    hw = [("초전도", 90), ("이온 트랩", 180), ("광자", 270)]
    for k, (name, x) in enumerate(hw):
        aa = a * clamp(p - k * 0.15)
        line(d, [(x, 393), (x, 420)], (255, 205, 90, int(180 * aa)), 2)
        rrect(d, x - 38, 422, x + 38, 452, 8, fill=(255, 255, 255, int(25 * aa)), outline=(255, 255, 255, int(150 * aa)), width=1)
        text(d, name, x, 437, 12, WHITE, aa)
    a2 = a * ease((lt - 2.5) / 0.4)
    text(d, "양자 컴퓨터는 혼자 돌지 않는다\n고전 컴퓨터가 GPU처럼 부리는 장치", W / 2, 510, 14, WHITE, a2)

def sc_ecc(img, d, t):                         # 43~48s 오류 정정
    a = win(t, 43, 48, 0.3); lt = t - 43
    os_card_frame(d, t, a, "07", "오류 검출 (ECC·RAID)", "양자 오류 정정", None)
    cx, cy = W / 2, 340
    p = ease(( lt - 1.6) / 1.0)
    for i in range(9):
        r, c = divmod(i, 3)
        bx = cx + (c - 1) * 46; by = cy + (r - 1) * 46
        flick = (i in (2, 6)) and (int(lt * 6) % 2 == 0) and lt < 1.6
        col = RED if flick else CYAN
        x = bx + (cx - bx) * p; y = by + (cy - by) * p
        dot(d, x, y, 10 * (1 - 0.6 * p), col + (int(255 * a * (1 - 0.7 * p)),))
    if p > 0.05:
        glow_layer(img, lambda g: dot(g, cx, cy, 26 * p, GREEN + (int(255 * a * p),)), radius=8)
        text(d, "논리\n큐비트", cx, cy, 11, (10, 30, 20), a * p, spacing=2)
    text(d, "물리 큐비트 9개", cx, 255, 13, DIM, a * clamp(1 - 2 * p))      # 앞 문구가 다 사라진 뒤
    text(d, "→ 믿을 수 있는 1개", cx, 255, 13, GREEN, a * clamp(2 * p - 1))  # 다음 문구가 나타난다
    a2 = a * ease((lt - 2.8) / 0.4)
    text(d, "여러 개가 하나를 지켜 오류를 찾아낸다\n(9개는 쇼어 부호 예시)", W / 2, 490, 14, WHITE, a2)

def sc_debug(img, d, t):                       # 48~55s 디버깅의 역설
    a = win(t, 48, 55); lt = t - 48
    chapter(d, t, "08", "디버깅의 역설", a)
    # 코드 창
    rrect(d, 30, 90, W - 30, 200, 12, fill=(10, 12, 24, int(230 * a)), outline=(120, 140, 220, int(150 * a)), width=1)
    for k, c in enumerate([RED, GOLD, GREEN]):
        dot(d, 48 + k * 14, 106, 4, c + (int(255 * a),))
    typed = "print(qubit)"
    n = int(clamp((lt - 0.5) / 1.2) * len(typed))
    cursor = "▌" if int(lt * 3) % 2 == 0 and lt < 2.6 else ""
    text(d, ">>> " + typed[:n] + cursor, 46, 140, 15, WHITE, a, font=MONO, anchor="lm")
    measured = lt > 2.6
    if measured:
        text(d, "0", 46, 172, 15, GOLD, a * ease((lt - 2.6) / 0.2), font=MONO, anchor="lm")
        text(d, "← 중첩이 사라졌다", 70, 172, 13, DIM, a * ease((lt - 2.9) / 0.3), anchor="lm")
    # 블로흐 구: 측정 순간 붕괴
    if not measured:
        th = 1.57 + 0.9 * math.sin(lt * 2.2); ph = lt * 3; col = CYAN
    else:
        k = ease_out((lt - 2.6) / 0.35); th = 1.57 * (1 - k); ph = 0; col = GOLD
    flash = clamp(1 - abs(lt - 2.6) / 0.25)
    if flash > 0:
        d.rectangle([0, 0, S(W), S(H)], fill=(255, 255, 255, int(110 * flash * a)))
    glow_layer(img, lambda g: bloch(g, W / 2, 315, 62, th, ph, alpha=a, color=col), radius=5)
    a2 = a * ease((lt - 3.4) / 0.4)
    text(d, "보는 순간 상태가 결정된다 (측정)", W / 2, 432, 16, GOLD, a2)
    text(d, "중간값을 찍어 보는 디버깅이\n양자에서는 계산을 망가뜨린다", W / 2, 475, 14, WHITE, a2)
    a3 = a * ease((lt - 4.8) / 0.4)
    text(d, "→ OS·컴파일러가 실행 전에 검증해야 한다", W / 2, 540, 13, CYAN, a3)

def sc_outro(img, d, t):                       # 55~60s 한줄 평
    a = ease((t - 55) / 0.5) * ease((60 - t) / 0.6)
    lt = t - 55
    glow_layer(img, lambda g: bloch(g, W / 2, 175, 44, 1.0 + 0.3 * math.sin(lt * 2), lt * 2,
                                     alpha=a, labels=False, color=CYAN), radius=6)
    text(d, "한 줄 평", W / 2, 268, 13, MAG, a)
    line(d, [(W / 2 - 40, 284), (W / 2 + 40, 284)], MAG + (int(200 * a),), 1)
    a1 = a * ease((lt - 0.3) / 0.4); a2 = a * ease((lt - 1.1) / 0.4)
    text(d, "큐비트는 금방 잊는다.", W / 2, 325, 20, WHITE, a1)
    glow_layer(img, lambda g: text(g, "그 짧은 순간을\n여럿이 나눠 쓰게 하는 것,", W / 2, 383, 19, WHITE, a2), radius=5, strength=0.5)
    a3 = a * ease((lt - 2.0) / 0.4)
    glow_layer(img, lambda g: text(g, "그게 양자 OS다.", W / 2, 448, 27, CYAN, a3), radius=8)
    a4 = a * ease((lt - 3.0) / 0.4)
    text(d, "참고 문헌", W / 2, 540, 10, DIM, a4)
    text(d, "Giortamis et al., QOS (OSDI '25)\nDelle Donne et al., QNodeOS (Nature 639, 2025)",
         W / 2, 568, 10, DIM, a4, font=EN_M, spacing=4)

SCENES = [(0, 5.4, sc_title), (4.6, 13.4, sc_bit_qubit), (12.6, 20.4, sc_power), (19.6, 28.4, sc_decoherence),
          (27.7, 33.3, sc_sched), (32.7, 38.3, sc_memory), (37.7, 43.3, sc_driver), (42.7, 48.4, sc_ecc),
          (47.6, 55.4, sc_debug), (54.6, 60.1, sc_outro)]

def render(t):
    img = background()
    d = ImageDraw.Draw(img, "RGBA")
    draw_stars(d, t)
    for a, b, fn in SCENES:
        if a <= t <= b:
            fn(img, d, t)
            d = ImageDraw.Draw(img, "RGBA")   # glow_layer가 paste한 뒤 새 draw로
    if t > 0.3:
        progress(d, t)
    return img.resize((W, H), Image.LANCZOS)

# =====================================================================
# 사운드: 신시사이저 패드 + 전환 효과음 + 측정 '틱' (모두 직접 합성 → 저작권 문제 없음)
# =====================================================================
def make_audio(path, sr=44100):
    n = sr * DUR; tt = np.arange(n) / sr
    out = np.zeros(n)
    def note(f): return 440 * 2 ** ((f - 69) / 12)
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F C G
    seg = 4.0
    for k in range(int(DUR / seg)):
        s0 = int(k * seg * sr); s1 = min(n, int((k + 1) * seg * sr + 0.8 * sr))
        lt = tt[s0:s1] - k * seg
        env = np.clip(lt / 0.8, 0, 1) * np.clip((seg + 0.8 - lt) / 1.2, 0, 1)
        for m in chords[k % 4]:
            for det in (-0.12, 0.12):
                f = note(m) * 2 ** (det / 12)
                out[s0:s1] += 0.035 * env * np.sin(2 * np.pi * f * lt)
        out[s0:s1] += 0.05 * env * np.sin(2 * np.pi * note(chords[k % 4][0] - 12) * lt)
    # 아르페지오 반짝임 (8분음)
    step = 0.25
    for i in range(int(DUR / step)):
        k = int(i * step / seg) % 4
        m = chords[k][i % 3] + 12 + (12 if i % 8 == 7 else 0)
        s0 = int(i * step * sr); L = int(0.35 * sr); s1 = min(n, s0 + L)
        lt = tt[s0:s1] - i * step
        vol = 0.022 if 5 <= i * step <= 55 else 0.012
        out[s0:s1] += vol * np.exp(-lt * 9) * np.sin(2 * np.pi * note(m) * lt)
    def whoosh(at, dur=0.5, vol=0.08):
        s0 = int(at * sr); L = int(dur * sr); s1 = min(n, s0 + L)
        lt = np.arange(s1 - s0) / sr
        noise = np.random.default_rng(int(at * 10)).standard_normal(s1 - s0)
        noise = np.convolve(noise, np.ones(30) / 30, mode="same")
        env = np.sin(np.pi * lt / dur) ** 2
        out[s0:s1] += vol * env * noise * 4
    def blip(at, f=1200, dur=0.25, vol=0.12):
        s0 = int(at * sr); s1 = min(n, s0 + int(dur * sr)); lt = np.arange(s1 - s0) / sr
        out[s0:s1] += vol * np.exp(-lt * 18) * np.sin(2 * np.pi * f * lt * (1 + 0.5 * np.exp(-lt * 30)))
    for at in (4.8, 12.8, 19.8, 27.8, 32.8, 37.8, 42.8, 47.8, 54.8):
        whoosh(at)
    blip(0.5, 660); blip(0.9, 990)
    for i in range(3): blip(28.4 + i * 0.7, 880 + i * 220, vol=0.06)    # 회로 탑재
    for i in range(4): blip(33.5 + i * 0.35, 700, vol=0.05)             # 주소 매핑
    blip(44.6, 520, 0.6, 0.08)                                           # 논리 큐비트 합체
    blip(50.6, 1800, 0.4, 0.2)                                           # 측정 붕괴
    blip(57.0, 784, 0.8, 0.1); blip(57.0, 1175, 0.8, 0.06)               # 마무리 차임
    # 전체 페이드 + 정규화
    fade = np.clip(tt / 0.5, 0, 1) * np.clip((DUR - tt) / 1.0, 0, 1)
    out *= fade
    out = out / np.max(np.abs(out)) * 0.8
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())

def main():
    if "--preview" in sys.argv:
        times = [2.5, 4.9, 9.5, 18.5, 26.5, 31.5, 36.5, 41.5, 46.5, 50.0, 53.5, 59.0]
        frames = [render(t) for t in times]
        sheet = Image.new("RGB", (W * 6, H * 2))
        for i, f in enumerate(frames):
            sheet.paste(f, ((i % 6) * W, (i // 6) * H))
        sheet.save(os.path.join(OUT_DIR, "preview_sheet.png"))
        print("preview saved"); return
    wav = os.path.join(OUT_DIR, "bgm.wav"); make_audio(wav)
    os.makedirs(os.path.join(OUT_DIR, "media"), exist_ok=True)
    out = os.path.join(OUT_DIR, "media", "quantum_os_shorts.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = FPS * DUR
    for i in range(total):
        p.stdin.write(render(i / FPS).tobytes())
        if i % 300 == 0: print(f"{i}/{total}", flush=True)
    p.stdin.close(); p.wait()
    print("done:", out)

if __name__ == "__main__":
    main()
