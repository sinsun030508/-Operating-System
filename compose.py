"""
AI 생성 클립 + 자막 + BGM 합성기  →  360x640, 30fps, 60초
  clips/ 폴더에 01~10 으로 시작하는 영상(mp4/mov/webm) 또는 이미지(png/jpg/webp)를 넣고 실행:
      python3 compose.py              # 완성본 media/quantum_os_ai.mp4
      python3 compose.py --preview    # 장면별 대표 프레임만 preview_ai.png
  - 이미지는 장면마다 다른 카메라 움직임(다가가기·물러나기·가로/세로 흐름)으로 움직인다.
  - 어떤 해상도·비율·fps 든 받아서 화면을 꽉 채우도록 확대 후 가운데를 잘라 360x640 으로 만든다.
  - 클립 길이가 장면보다 짧으면: 1.75배 이내면 슬로모션, 그 이상이면 반복. 길면 앞부분만 쓴다.
  - 클립이 없는 장면은 make_video.py 의 기존 장면(코드 애니메이션)으로 자동 대체한다.
  - 클립 오디오는 쓰지 않고, 장면 타이밍에 맞춘 BGM(bgm.wav)을 입힌다.
  - 피사체가 가운데가 아니면 CROP_X 에서 장면별로 가로 위치(0=왼쪽, 0.5=가운데, 1=오른쪽)를 바꾼다.
"""
import glob, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
import make_video as mv
from make_video import W, H, FPS, DUR, S, F, KO, EN_B, EN_M, SYM, CYAN, MAG, GOLD, WHITE, DIM, RED, GREEN

HERE = os.path.dirname(os.path.abspath(__file__))
CLIP_DIR = os.path.join(HERE, "clips")
SLOTS = [(0, 5), (5, 13), (13, 20), (20, 28), (28, 33), (33, 38), (38, 43), (43, 48), (48, 55), (55, 60)]
CROP_X = [0.5] * 10          # 장면별 가로 자르기 위치
XFADE = 0.3                  # 장면 사이 겹침(초)
TRIM_BOTTOM = 0.06           # AI 이미지 아래쪽을 이만큼 잘라 낸다 (무료 이미지 툴의 구석 워터마크 가리기, 0 이면 안 자름)

# ---------- 내레이션 (voice/01.mp3 ~ voice/10.mp3, 또는 통파일 voice/full.mp3) ----------
VOICE_DIR = os.path.join(HERE, "voice")
VOICE_LEAD = 0.3             # 장면이 시작되고 몇 초 뒤에 말을 시작할지
MAX_SPEEDUP = 1.25           # 장면보다 길면 이 배율까지는 자동으로 빠르게 재생
DUCK = 0.3                   # 말하는 동안 배경음악 크기 (1 = 그대로)
VOICE_CREDIT = ""            # 무료 TTS 출처 표기 문구. 예: "음성: 네이버 클로바더빙" (한줄 평 화면 아래에 작게)
SR = 44100
AUDIO_EXT = ("mp3", "wav", "m4a", "ogg", "aac", "flac")

# ---------- 자막 내용 ----------
# (챕터 번호, 챕터 이름, 강조 줄, 설명 줄, 강조 색, 출처)
CAPS = [
    None,  # 0: 타이틀은 따로 그림
    ("01", "비트와 큐비트", "비트는 0 또는 1, 큐비트는 동시에", "측정 전까지 여러 상태가 겹친다 — 중첩", CYAN, None),
    ("02", "지수적으로 커지는 상태", "큐비트 n개 → 2ⁿ개 상태", "50개면 약 1,126조 개를 한꺼번에", GOLD, None),
    ("03", "큐비트는 금방 잊는다", "결어긋남: 수백 μs면 상태가 무너진다", "→ 모든 작업에 마감이 있는 실시간 스케줄링", RED, None),
    ("04", "OS가 할 일 · 스케줄링", "CPU 스케줄링 → QPU 작업 스케줄링", "여러 사용자의 회로를 한 장비에 나눠 싣는다", CYAN, "QOS · OSDI '25"),
    ("05", "OS가 할 일 · 메모리", "가상 메모리 → 가상 큐비트 주소", "상태 좋은 큐비트는 OS가 골라 준다", MAG, "QNodeOS(QMMU) · Nature 2025"),
    ("06", "OS가 할 일 · 드라이버", "드라이버 → QPU는 주변 장치", "고전 컴퓨터가 GPU처럼 부린다", GOLD, "QNodeOS · NV·이온 트랩 드라이버"),
    ("07", "OS가 할 일 · 오류 정정", "ECC → 양자 오류 정정", "물리 큐비트 여럿이 논리 큐비트 하나를 지킨다", GREEN, None),
    ("08", "디버깅의 역설", "print(qubit) 하는 순간 상태가 붕괴", "보기만 해도 계산이 망가진다 → 실행 전 검증", GOLD, None),
    None,  # 9: 한줄 평은 따로 그림
]

def fit_text(d, s, x, y, size, color, alpha, maxw=310, font=KO):
    """한 줄이 화면 폭을 넘으면 글자 크기를 줄여서 맞춘다 (폰트에 없는 글자는 먼저 대체)"""
    s = mv.safe(s, font)
    while size > 10 and d.textlength(s, font=F(font, size)) > S(maxw):
        size -= 0.5
    mv.text(d, s, x, y, size, color, alpha, font=font)

# ---------- 가독성용 어둡게 깔기 (한 번만 만든다) ----------
def _shade():
    y = np.linspace(0, 1, H * S(1))[:, None]
    a = np.clip((y - 0.62) / 0.3, 0, 1) * 185 + np.clip((0.14 - y) / 0.14, 0, 1) * 110
    arr = np.zeros((H * S(1), W * S(1), 4), np.uint8)
    arr[..., 3] = a.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")
SHADE = _shade()
_title_shade = None
def title_shade():
    global _title_shade
    if _title_shade is None:
        y = np.linspace(0, 1, H * S(1))[:, None]
        a = np.exp(-((y - 0.64) / 0.16) ** 2) * 170
        arr = np.zeros((H * S(1), W * S(1), 4), np.uint8); arr[..., 3] = a.astype(np.uint8)
        _title_shade = Image.fromarray(arr, "RGBA")
    return _title_shade

def overlay(img, k, t):
    a0, b0 = SLOTS[k]
    lt = t - a0
    a = mv.win(t, a0, b0, 0.35) if k not in (0, 9) else mv.ease((t - a0) / 0.4) * mv.ease((b0 - t) / 0.5)
    img.paste(SHADE, (0, 0), SHADE)
    d = ImageDraw.Draw(img, "RGBA")
    if k == 0:
        img.paste(title_shade(), (0, 0), title_shade()); d = ImageDraw.Draw(img, "RGBA")
        t1 = mv.ease_back((lt - 0.4) / 0.6); t2 = mv.ease_back((lt - 0.8) / 0.6)
        mv.text(d, "큐비트에게도", W / 2, 360 + 20 * (1 - t1), 28, WHITE, a * mv.clamp((lt - 0.4) / 0.3))
        def g(gd):
            aa = a * mv.clamp((lt - 0.8) / 0.3)
            mv.text(gd, "운영체제가", W / 2, 405 + 20 * (1 - t2), 36, CYAN, aa)
            mv.text(gd, "필요할까?", W / 2, 450 + 20 * (1 - t2), 36, CYAN, aa)
        mv.glow_layer(img, g, radius=8, strength=0.9); d = ImageDraw.Draw(img, "RGBA")
        a3 = a * mv.clamp((lt - 1.6) / 0.4)
        mv.rrect(d, W / 2 - 95, 494, W / 2 + 95, 520, 13, fill=(0, 0, 0, int(90 * a3)), outline=MAG + (int(220 * a3),), width=1)
        mv.text(d, "QUANTUM  ×  OS", W / 2, 507, 13, MAG, a3, font=EN_M)
    elif k == 9:
        mv.rrect(d, 22, 300, W - 22, 560, 18, fill=(5, 6, 20, int(150 * a)))
        mv.text(d, "한 줄 평", W / 2, 325, 13, MAG, a)
        a1 = a * mv.ease((lt - 0.3) / 0.4); a2 = a * mv.ease((lt - 1.1) / 0.4); a3 = a * mv.ease((lt - 2.0) / 0.4)
        mv.text(d, "큐비트는 금방 잊는다.", W / 2, 365, 20, WHITE, a1)
        mv.text(d, "그 짧은 순간을\n여럿이 나눠 쓰게 하는 것,", W / 2, 420, 18, WHITE, a2)
        mv.glow_layer(img, lambda gd: mv.text(gd, "그게 양자 OS다.", W / 2, 482, 26, CYAN, a3), radius=8)
        d = ImageDraw.Draw(img, "RGBA")
        a4 = a * mv.ease((lt - 3.0) / 0.4)
        mv.text(d, "Giortamis et al., QOS (OSDI '25) · Delle Donne et al., QNodeOS (Nature 2025)",
                W / 2, 538, 7.5, DIM, a4, font=EN_M)
        if VOICE_CREDIT:
            mv.text(d, VOICE_CREDIT, W / 2, 551, 8, DIM, a4)
    else:
        num, chap, l1, l2, col, ref = CAPS[k]
        mv.rrect(d, 16, 34, 16 + 30 + len(chap) * 13, 58, 12, fill=(5, 6, 20, int(170 * a)))   # 밝은 화면 대비
        mv.chapter(d, t, num, chap, a)
        p = mv.ease_out((lt - 0.2) / 0.5)
        mv.rrect(d, 20, 472 + 12 * (1 - p), W - 20, 556 + 12 * (1 - p), 16,
                 fill=(5, 6, 20, int(170 * a * p)), outline=col + (int(170 * a * p),), width=1)
        fit_text(d, l1, W / 2, 500 + 12 * (1 - p), 16.5, col, a * p)
        fit_text(d, l2, W / 2, 530 + 12 * (1 - p), 13.5, WHITE, a * mv.ease((lt - 0.7) / 0.4))
        if ref:
            mv.text(d, ref, W - 26, 574, 9.5, DIM, a * 0.9, anchor="rm")
    mv.progress(ImageDraw.Draw(img, "RGBA"), t)

# ---------- 클립 읽기 ----------
VIDEO_EXT = ("mp4", "mov", "webm", "mkv", "m4v")
IMAGE_EXT = ("png", "jpg", "jpeg", "webp")

def find_clip(k):
    """장면 번호로 시작하는 영상을 먼저, 없으면 이미지를 찾는다 (같은 번호면 영상이 이긴다)"""
    for ext in VIDEO_EXT + IMAGE_EXT + tuple(e.upper() for e in VIDEO_EXT + IMAGE_EXT):
        m = sorted(glob.glob(os.path.join(CLIP_DIR, f"{k + 1:02d}*.{ext}")))
        if m: return m[0]
    return None

# 이미지 장면의 카메라 움직임 (켄 번스 효과): 장면마다 번갈아 쓴다
#   (시작 확대, 끝 확대, 가로 중심 시작→끝, 세로 중심 시작→끝)  중심은 0~1 (0.5 = 가운데)
MOVES = [(1.00, 1.14, (0.5, 0.5), (0.5, 0.45)),    # 천천히 다가가기
         (1.14, 1.00, (0.5, 0.45), (0.5, 0.5)),    # 천천히 물러나기
         (1.10, 1.10, (0.30, 0.5), (0.70, 0.5)),   # 왼쪽 → 오른쪽
         (1.10, 1.10, (0.5, 0.35), (0.5, 0.62))]   # 위 → 아래

class StillMotion:
    """이미지 한 장을 카메라가 움직이며 찍는 것처럼 보여 준다"""
    def __init__(self, path, k, dur):
        img = Image.open(path).convert("RGB")
        if TRIM_BOTTOM > 0:                        # 아래 구석 워터마크가 화면에 비치지 않게
            img = img.crop((0, 0, img.width, int(img.height * (1 - TRIM_BOTTOM))))
        self.img = img
        self.k, self.dur = k, dur
        iw, ih = self.img.size
        self.s0 = max(W / iw, H / ih) * 1.005      # 화면을 꽉 채우는 배율 (+0.5%: 잘라 올 창이 항상 이미지 안에 들도록)
        self.move = MOVES[k % len(MOVES)]
    def frame(self, lt):
        z0, z1, (x0, y0), (x1, y1) = self.move
        p = mv.ease(lt / self.dur)
        z = z0 + (z1 - z0) * p
        cxf = x0 + (x1 - x0) * p + (CROP_X[self.k] - 0.5)
        cyf = y0 + (y1 - y0) * p + 0.006 * math.sin(lt * 1.7)    # 아주 살짝 둥실
        if self.k == 3:                                           # 04 결어긋남: 갈수록 심해지는 떨림
            amp = 0.012 * p
            cxf += amp * (math.sin(lt * 31) + math.sin(lt * 53)) / 2
            cyf += amp * (math.sin(lt * 37) + math.sin(lt * 47)) / 2
        iw, ih = self.img.size
        ww, wh = W / (self.s0 * z), H / (self.s0 * z)             # 원본에서 잘라 올 창 크기
        cx = min(max(cxf * iw, ww / 2 + 1), iw - ww / 2 - 1)      # 1px 안쪽: 이미지 밖(검은색)을 읽지 않게
        cy = min(max(cyf * ih, wh / 2 + 1), ih - wh / 2 - 1)
        box = (cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2)
        return self.img.transform((W, H), Image.EXTENT, box, resample=Image.BICUBIC)

# ---------- 이미지 장면이 스스로 움직이게 하는 효과 (2배 크기 화면 위에) ----------
FX_SPARKLE_N = {0: 55, 9: 60}                                  # 장면별 빛 입자 수 (기본 34)
_sparkles = {}
def _sparkle_set(k):
    if k not in _sparkles:
        import random
        r = random.Random(100 + k)
        _sparkles[k] = [(r.random(), r.random(), r.uniform(0.01, 0.05), r.uniform(0.7, 2.2), r.uniform(0, 6.28),
                         r.choice([(150, 240, 255), (255, 255, 255), (255, 150, 220)]))
                        for _ in range(FX_SPARKLE_N.get(k, 34))]
    return _sparkles[k]

def still_fx(big, k, lt, dur):
    """밝기 숨쉬기 · 장면별 효과(02 색 아른거림, 04 깜빡임·잡음, 09 플래시) · 떠다니는 빛 입자"""
    p = mv.clamp(lt / dur)
    arr = np.asarray(big, np.float32)
    gain = 1 + 0.06 * math.sin(lt * 2.2)                       # 숨쉬듯 밝아졌다 어두워짐
    if k == 1:                                                 # 02 중첩: 청록 ↔ 분홍
        w = 0.10 * math.sin(lt * 3.0)
        tint = np.array(CYAN if w > 0 else MAG, np.float32)
        arr = arr * (1 - abs(w)) + tint * abs(w)
    if k == 3:                                                 # 04 결어긋남: 색이 바래고 깜빡인다
        g = 0.55 * p
        gray = arr.mean(axis=2, keepdims=True)
        arr = arr * (1 - g) + gray * g
        import random
        if p > 0.25 and random.Random(int(lt * 14)).random() < 0.35 * p:
            gain *= 0.62
    arr = arr * gain
    if k == 8:                                                 # 09 측정: 효과음(50.6초)과 같은 순간 플래시
        fl = mv.clamp(1 - abs(lt - 2.6) / 0.3)
        arr = arr + (255 - arr) * 0.85 * fl
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    if k == 3 and p > 0.4:                                     # 04: 지지직 잡음 줄
        import random
        r = random.Random(int(lt * 20))
        for _ in range(r.randint(0, 3)):
            y = r.uniform(0, H) * S(1); hh = r.uniform(1, 4) * S(1)
            d.rectangle([0, y, W * S(1), y + hh], fill=(255, 255, 255, int(70 * p)))
    rise = 0.09 if k == 9 else 0.0                             # 10 한줄 평: 위로 떠오른다
    for x0, y0, sp, sz, ph, col in _sparkle_set(k):
        x = (x0 + 0.02 * math.sin(lt * 0.8 + ph)) * W
        y = ((y0 - (sp + rise) * lt) % 1.0) * H
        tw = 0.5 + 0.5 * math.sin(lt * 3.1 + ph)               # 반짝임
        a = int(200 * tw)
        if a < 12: continue
        R = sz * S(1)
        d.ellipse([S(x) - R * 3, S(y) - R * 3, S(x) + R * 3, S(y) + R * 3], fill=col + (a // 6,))
        d.ellipse([S(x) - R, S(y) - R, S(x) + R, S(y) + R], fill=col + (a,))
    return img

def load_clip(path, k, max_sec=15):
    cx = CROP_X[k]
    vf = (f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
          f"crop={W}:{H}:(iw-{W})*{cx}:(ih-{H})/2,setsar=1")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-t", str(max_sec), "-i", path, "-vf", vf, "-an",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (W * H * 3)
    if n == 0: raise RuntimeError(f"프레임을 못 읽었다: {path}")
    return np.frombuffer(raw[: n * W * H * 3], np.uint8).reshape(n, H, W, 3)

def mapper(n, need):
    """장면에 필요한 프레임 수(need)에 맞춰 클립 프레임 번호를 고른다"""
    if n >= need: return lambda i: min(i, n - 1)
    if need / n <= 1.75: return lambda i: min(int(i * n / need), n - 1)       # 슬로모션
    return lambda i: i % n                                                   # 반복

class Scene:
    def __init__(self, k):
        self.k = k; self.a, self.b = SLOTS[k]
        path = find_clip(k)
        self.path = path
        self.still = None
        if path and path.lower().endswith(IMAGE_EXT):
            self.still = StillMotion(path, k, self.b - self.a + XFADE)
        elif path:
            self.frames = load_clip(path, k)
            need = int((self.b - self.a + XFADE) * FPS)
            self.idx = mapper(len(self.frames), need)
    def frame(self, t):
        if not self.path:                      # 대체: 기존 코드 애니메이션 (자막 포함)
            # 원래 영상도 장면 경계에서 자기 페이드를 하므로, 경계 0.3초는 장면이 다 보이는 시각으로 묶는다
            # (안 묶으면 우리 전환 위에 원래 전환이 겹쳐 글자가 두 번 보였다)
            return mv.render(min(max(t, self.a + 0.3), self.b - 0.3)), False
        if self.still:                         # AI 이미지 + 카메라 움직임
            return self.still.frame(max(0.0, t - self.a)), True
        i = max(0, int(round((t - self.a) * FPS)))
        return Image.fromarray(self.frames[self.idx(i)]), True

def compose_frame(scenes, t):
    k = max(i for i, (a, b) in enumerate(SLOTS) if a <= t or i == 0)
    cur = scenes[k]
    img, is_clip = cur.frame(t)
    if is_clip:
        big = img.resize((W * S(1), H * S(1)), Image.BILINEAR)
        if cur.still:
            big = still_fx(big, k, t - cur.a, cur.b - cur.a)
        overlay(big, k, t)
        img = big.resize((W, H), Image.LANCZOS)
    # 장면 전환 크로스페이드
    if k > 0 and t - SLOTS[k][0] < XFADE:
        prev = scenes[k - 1]
        pimg, p_clip = prev.frame(t)
        if p_clip:
            pbig = pimg.resize((W * S(1), H * S(1)), Image.BILINEAR)
            if prev.still:
                pbig = still_fx(pbig, k - 1, t - prev.a, prev.b - prev.a)
            overlay(pbig, k - 1, min(t, SLOTS[k - 1][1] - 0.01))
            pimg = pbig.resize((W, H), Image.LANCZOS)
        img = Image.blend(pimg, img, mv.ease((t - SLOTS[k][0]) / XFADE))
    return img

# ---------- 오디오: BGM + 내레이션 + 더킹 ----------
def pcm(x): return (np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()

def load_audio(path=None, data=None, af=None):
    """어떤 오디오 형식이든 44.1kHz 모노 float 배열로 읽는다 (data를 주면 그 배열에 필터만 건다)"""
    src = ["-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-"] if data is not None else ["-i", path]
    cmd = ["ffmpeg", "-v", "error"] + src + (["-af", af] if af else []) + ["-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, input=pcm(data) if data is not None else None, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def find_voice(name):
    for ext in AUDIO_EXT:
        m = sorted(glob.glob(os.path.join(VOICE_DIR, f"{name}*.{ext}")))
        if m: return m[0]
    return None

def moving_avg(x, w):
    w = max(1, int(w)); c = np.cumsum(np.concatenate([[0.0], x]))
    out = (c[w:] - c[:-w]) / w
    pad = len(x) - len(out)
    return np.concatenate([np.full(pad // 2, out[0]), out, np.full(pad - pad // 2, out[-1])])

def trim_silence(v, thr=0.02):
    """TTS 파일 앞뒤에 붙은 무음을 잘라 낸다 (앞 0.03초, 뒤 0.1초는 여유로 남김)"""
    env = moving_avg(np.abs(v), SR * 0.02)
    idx = np.where(env > thr * env.max())[0]
    if len(idx) == 0: return v
    return v[max(0, idx[0] - int(SR * 0.03)): idx[-1] + int(SR * 0.1)]

def level(v, target=0.12):
    """파일마다 다른 음량을 같은 크기(RMS)로 맞춘다"""
    env = moving_avg(np.abs(v), SR * 0.05)
    loud = v[env > 0.1 * env.max()]
    rms = np.sqrt(np.mean(loud ** 2)) if len(loud) else 1
    v = v * (target / max(rms, 1e-6))
    pk = np.abs(v).max()
    return v * (0.95 / pk) if pk > 0.95 else v

def build_audio():
    """voice/ 의 내레이션을 장면 시각에 놓고 배경음악을 그 아래로 줄여 mix.wav 를 만든다.
       내레이션 파일이 하나도 없으면 None"""
    os.makedirs(VOICE_DIR, exist_ok=True)
    full = find_voice("full")
    per = {k: find_voice(f"{k + 1:02d}") for k in range(10)}
    if not full and not any(per.values()): return None
    wav = os.path.join(HERE, "bgm.wav")
    if not os.path.exists(wav): mv.make_audio(wav)
    bgm = load_audio(wav); n = SR * DUR
    bgm = np.pad(bgm, (0, max(0, n - len(bgm))))[:n]
    voice = np.zeros(n, np.float32); rows = []
    if full:
        v = level(load_audio(full)); e = min(n, len(v)); voice[:e] = v[:e]
        rows.append(("full", os.path.basename(full), f"{len(v) / SR:.1f}s", "0~60초", "통파일" + (" — 60초 넘음!" if len(v) > n else "")))
    else:
        for k, path in per.items():
            a0, b0 = SLOTS[k]
            if not path:
                rows.append((f"{k + 1:02d}", "-", "", f"{a0}~{b0}초", "없음")); continue
            v = level(trim_silence(load_audio(path)))
            start = a0 + VOICE_LEAD; avail = b0 - start - 0.15
            dur = len(v) / SR; note = "OK"
            if dur > avail:
                f = dur / avail
                if f <= MAX_SPEEDUP:
                    v = load_audio(data=v, af=f"atempo={f:.4f}"); note = f"{f:.2f}배 빠르게"
                else:
                    note = f"넘침! {dur - avail:.1f}초 줄이세요"
            s = int(start * SR); e = min(n, s + len(v)); voice[s:e] += v[: e - s]
            rows.append((f"{k + 1:02d}", os.path.basename(path), f"{dur:.1f}s / {avail:.1f}s", f"{a0}~{b0}초", note))
    # 더킹: 목소리가 있는 구간(앞 0.15초·뒤 0.35초 여유)에서 배경음악을 DUCK 배로 줄인다
    env = moving_avg(np.abs(voice), SR * 0.03)
    active = (env > 0.004).astype(np.float32)
    active = (moving_avg(active, SR * 0.5) > 0).astype(np.float32)
    gain = 1 - (1 - DUCK) * np.clip(moving_avg(active, SR * 0.25) * 1.0, 0, 1)
    mix = bgm * 0.55 * gain + voice
    pk = np.abs(mix).max()
    if pk > 0.97: mix *= 0.97 / pk
    out = os.path.join(HERE, "mix.wav")
    import wave
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm(mix))
    print("\n장면  파일                   길이/허용      구간       상태")
    for r in rows: print(f"{r[0]:<5} {r[1]:<22} {r[2]:<14} {r[3]:<10} {r[4]}")
    print("→", out, "\n")
    return out

def main():
    if "--audio" in sys.argv:            # 소리만 빠르게 확인
        if not build_audio(): print("voice/ 폴더에 내레이션 파일이 없습니다 (01.mp3 ~ 10.mp3)")
        return
    os.makedirs(CLIP_DIR, exist_ok=True)
    scenes = {}
    def get(k):
        if k not in scenes:
            scenes[k] = Scene(k)
            print(f"장면 {k + 1:02d}: {os.path.basename(scenes[k].path) if scenes[k].path else '클립 없음 → 기존 애니메이션'}"
                  + (" (이미지 + 카메라 움직임)" if scenes[k].still else f" ({len(scenes[k].frames)}프레임)" if scenes[k].path else ""), flush=True)
        for old in [o for o in scenes if o < k - 1]: del scenes[old]   # 메모리 절약
        return scenes[k]
    class Lazy(dict):
        def __getitem__(self, k): return get(k)
    lazy = Lazy()
    if "--preview" in sys.argv:
        times = [2.5, 9, 16.5, 24, 30.5, 35.5, 40.5, 45.5, 51.5, 58.5]
        sheet = Image.new("RGB", (W * 5, H * 2))
        for i, t in enumerate(times):
            sheet.paste(compose_frame(lazy, t), ((i % 5) * W, (i // 5) * H))
        out = os.path.join(HERE, "preview_ai.png"); sheet.save(out); print("saved", out); return
    wav = build_audio()                  # 내레이션이 있으면 mix.wav, 없으면 BGM만
    if not wav:
        wav = os.path.join(HERE, "bgm.wav")
        if not os.path.exists(wav): mv.make_audio(wav)
    os.makedirs(os.path.join(HERE, "media"), exist_ok=True)
    out = os.path.join(HERE, "media", "quantum_os_ai.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(FPS * DUR):
        p.stdin.write(compose_frame(lazy, i / FPS).convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    print("done:", out)

if __name__ == "__main__":
    main()
