# AI 애니메이션 프롬프트 시트 — 「큐비트에게도 운영체제가 필요할까?」

## 0. 작업 순서 (총 1~2시간)

1. **캐릭터 이미지 1장 만들기** (아래 1번 프롬프트, 아무 이미지 생성 AI) → `qubi.png`
2. **장면 10개 클립 생성** (Kling · Runway · Hailuo · Pika 등 영상 AI)
   - 비율은 **9:16** 선택 (16:9로 만들어도 스크립트가 가운데를 잘라 쓰지만, 양옆이 잘린다)
   - 가능하면 **image-to-video**로 `qubi.png`를 첫 프레임에 넣는다 → 장면마다 캐릭터 생김새가 유지된다
   - 길이는 **5초**로 충분하다. 장면이 더 길면 스크립트가 슬로모션(1.75배 이내 — 5초 클립 하나로 모든 장면이 덮인다)으로 늘린다
     (8초 장면은 10초로 생성하면 슬로모션 없이 더 매끄럽다)
3. 파일 이름을 `01_...mp4` ~ `10_...mp4`로 바꿔 `clips/` 폴더에 넣는다 (번호만 맞으면 뒤는 자유)
4. 실행:
   ```bash
   python3 compose.py --preview   # 10장면 미리보기 이미지 → preview_ai.png
   python3 compose.py             # 완성본 → media/quantum_os_ai.mp4 (약 1분 반)
   ```
   - 클립이 없는 장면은 기존 코드 애니메이션으로 자동 대체 → 하나씩 만들면서 확인 가능
   - 자막·BGM·효과음·0~5초 타이틀·55~60초 한줄 평은 **스크립트가 입힌다**. AI 클립에는 글자가 없어야 한다
   - 주인공이 화면 밖으로 잘리면 `compose.py`의 `CROP_X`에서 그 장면 값을 0(왼쪽)~1(오른쪽)로 조절

> **왜 영상 속 글자를 AI에게 맡기지 않나?** 영상 AI는 한글을 거의 항상 깨진 모양으로 그린다.
> 그래서 모든 프롬프트에 "no text"를 넣고, 정확한 자막은 코드로 덧입힌다.

> **학업 정직성:** 레포트의 「제작 방법」에 사용한 AI 툴 이름과 "영상 클립은 AI로 생성, 기획·콘티·자막·
> 합성·음악은 직접 제작"을 적어 두자. 대부분의 수업에서 AI 사용 표기를 요구하고, 표기하면 오히려 감점 위험이 없다.

---

## ★ 영상 크레딧이 부족할 때: AI 이미지 + 코드 카메라 움직임

> **한국어 프롬프트와 무료 사이트 안내는 [`이미지_프롬프트.md`](이미지_프롬프트.md)에 따로 정리했다.**

영상 AI 크레딧 없이도 됩니다. **장면마다 AI 이미지 1장**만 만들어 `clips/`에 넣으면, `compose.py`가 장면마다 다른
카메라 움직임(다가가기 → 물러나기 → 왼쪽에서 오른쪽 → 위에서 아래, 반복)과 살짝 둥실거림을 넣어 영상처럼 만든다.

1. 무료로 이미지를 만들 수 있는 아무 AI 이미지 툴을 쓴다 (예: Gemini, ChatGPT, Bing Image Creator, Kling 이미지 생성 등
   — 무료 한도는 툴마다 다르니 각 사이트에서 확인)
2. 아래 **1번 캐릭터 시트**로 큐비를 먼저 만들고, 그 이미지를 참고 이미지로 함께 올리면 장면마다 생김새가 비슷해진다
3. 각 장면 프롬프트 맨 앞에 `A single still frame:`을, 끝에 공통 문구를 붙인다. 움직임 묘사(flips, flies in...)는
   **그 순간을 멈춘 장면**으로 읽히므로 그대로 써도 된다
4. 비율은 **9:16 세로**가 가장 좋다. 정사각형(1:1)도 되지만 양옆이 잘리니 주인공을 가운데에 둔다
5. 저장: `clips/01.png` ~ `clips/10.png` (png · jpg · webp). **같은 번호에 영상이 있으면 영상이 우선**이라,
   크레딧이 남을 때 중요한 장면(01 타이틀, 09 측정)만 영상으로 바꿔 넣으면 된다

> 왜 이게 통하나? 다큐멘터리에서 사진 한 장을 천천히 확대·이동하며 보여 주는 기법(켄 번스 효과)과 같다.
> 움직임이 느리고 장면마다 방향이 바뀌면 정지 이미지도 충분히 영상처럼 느껴진다.

---

## 1. 캐릭터 시트 — 「큐비(Qubi)」 (이미지 생성 AI용)

```
Character design of "Qubi", a cute small round robot made of translucent glass,
a glowing cyan energy core inside with a tiny rotating arrow (like a Bloch sphere vector),
two big expressive LED eyes, tiny floating hands, soft rim light,
3D animated movie style, Pixar-like, deep navy and violet background with cyan and magenta neon accents,
full body, centered, vertical 9:16 composition, no text
```

**모든 장면 프롬프트 끝에 붙일 공통 문구 (스타일 고정)**
```
3D animated movie style, Pixar-like, cinematic volumetric light, deep navy and violet palette
with cyan and magenta neon accents, vertical 9:16, smooth motion, no text, no letters, no subtitles
```

**네거티브 프롬프트 (지원하는 툴만)**
```
text, letters, words, subtitles, watermark, logo, distorted face, extra limbs, flicker, low quality
```

---

## 2. 장면별 프롬프트

> 아래 영어 프롬프트 뒤에 위의 **공통 문구**를 붙여서 넣는다.
> 「자막」은 스크립트가 자동으로 넣는 내용이라 참고용이다. 화면 아래 1/4에는 자막 패널이 올라가니 **주인공은 화면 가운데~위쪽**에 둔다.

### 01 · 타이틀 (0–5초 · 5초 생성)
- **화면:** 어두운 우주 같은 서버실에 큐비가 떠서 천천히 돌고, 빛 입자가 주위를 공전한다. 아래 절반은 제목 자리로 비워 둔다
- **자막:** 큐비트에게도 / 운영체제가 필요할까?
```
Qubi floats in the upper half of a dark cosmic server room, slowly rotating, glowing particles orbiting around it,
rows of server racks fading into stars, slow camera push-in, empty dark space in the lower half
```

### 02 · 비트와 큐비트 (5–13초 · 10초 생성)
- **화면:** 왼쪽엔 평범한 전등 스위치가 켜졌다 꺼졌다(비트). 오른쪽 큐비는 반투명한 두 모습으로 겹쳐 아른거린다(중첩)
- **자막:** 비트는 0 또는 1, 큐비트는 동시에 / 측정 전까지 여러 상태가 겹친다 — 중첩
```
On the left, a simple old light switch flips on and off repeatedly. On the right, Qubi shimmers and splits into
two overlapping translucent ghost copies of itself, one glowing cyan and one glowing magenta, blending in and out
like a superposition, gentle camera pan from left to right
```

### 03 · 지수적으로 커지는 상태 (13–20초 · 10초 생성 또는 5초)
- **화면:** 큐비가 둘, 넷, 여덟…로 복제되고 빛의 실로 서로 연결되며 은하처럼 퍼진다(2ⁿ, 얽힘)
- **자막:** 큐비트 n개 → 2ⁿ개 상태 / 50개면 약 1,126조 개를 한꺼번에
```
Qubi duplicates into two, then four, then eight, then dozens of small glowing spheres arranged in a grid,
thin threads of light connect them all, the network rapidly expands outward into a glowing galaxy,
camera pulls back fast to reveal the scale
```

### 04 · 큐비트는 금방 잊는다 — 결어긋남 (20–28초 · 10초 생성)
- **화면:** 실험실의 큐비 주위로 열기 아지랑이·진동·전기 잡음이 일고, 빛이 깜빡이다 회색으로 바래며 어지러워한다. 옆의 모래시계가 빠르게 빠진다
- **자막:** 결어긋남: 수백 μs면 상태가 무너진다 / → 모든 작업에 마감이 있는 실시간 스케줄링
```
Qubi floats in a lab, heat haze, shaking vibrations and crackling static noise surround it, its cyan glow flickers
and slowly fades to dull grey, Qubi looks dizzy and its inner arrow blurs, a small hourglass beside it drains rapidly,
slightly shaky handheld camera
```

### 05 · 스케줄링 (28–33초 · 5초 생성)
- **화면:** 관제탑의 관제사가 된 큐비가 분홍·금색·초록 빛 상자들을 양자 칩 위 4×4 착륙장에 차례로 내려앉힌다
- **자막:** CPU 스케줄링 → QPU 작업 스케줄링 / 여러 사용자의 회로를 한 장비에 나눠 싣는다
```
Qubi as an air traffic controller wearing a tiny headset, directing glowing cubes in magenta, gold and green
that fly in one after another and land neatly on a 4 by 4 grid of glowing pads on a futuristic quantum chip,
top-down angled camera
```

### 06 · 가상 큐비트 주소 (33–38초 · 5초 생성)
- **화면:** 크리스털 호텔의 안내원 큐비가 손님들에게 빛나는 열쇠를 건네고, 빛줄기가 각자 다른 방으로 이어진다(가상 주소 → 실제 위치)
- **자막:** 가상 메모리 → 가상 큐비트 주소 / 상태 좋은 큐비트는 OS가 골라 준다
```
Qubi as a hotel concierge in a crystal hotel lobby, handing glowing keys to small sphere guests, beams of light
travel from each key to different glowing rooms on different floors of the crystal building, some rooms brighter
than others, smooth dolly camera
```

### 07 · 드라이버 (38–43초 · 5초 생성)
- **화면:** 친근한 레트로 대형 컴퓨터 로봇이 큐비를 그래픽카드처럼 슬롯에 꽂는다. 뒤로 서로 다른 양자 장비 3종(금빛 샹들리에 냉각기, 레이저 이온 트랩, 빛의 광자 칩)이 나타난다
- **자막:** 드라이버 → QPU는 주변 장치 / 고전 컴퓨터가 GPU처럼 부린다
```
A big friendly retro computer robot gently plugs Qubi into a glowing expansion slot on its chest like a graphics card,
behind them three different machines light up one by one: a golden dilution refrigerator chandelier,
an ion trap with thin laser beams, and a photonic chip with flowing light, slow orbit camera
```

### 08 · 양자 오류 정정 (43–48초 · 5초 생성)
- **화면:** 작은 큐비 9명이 손을 잡고 원을 그려 가운데 금빛 큐비를 지킨다. 둘이 빨갛게 깜빡이자 나머지가 고쳐 주고, 모두 하나의 빛나는 구로 합쳐진다
- **자막:** ECC → 양자 오류 정정 / 물리 큐비트 여럿이 논리 큐비트 하나를 지킨다
```
Nine tiny Qubis hold hands in a circle protecting one larger golden Qubi in the center, two of the tiny ones
flicker red with glitches, the others glow brighter and fix them back to cyan, then all of them merge into
one shining green sphere with a burst of light, slow push-in
```

### 09 · 디버깅의 역설 — 측정 (48–55초 · 10초 생성)
- **화면:** 아른거리는 큐비에게 거대한 돋보기(또는 카메라)가 다가온다. 플래시가 터지는 순간 큐비가 하나의 단단한 모습으로 굳고 깜짝 놀란다
- **자막:** print(qubit) 하는 순간 상태가 붕괴 / 보기만 해도 계산이 망가진다 → 실행 전 검증
```
Qubi shimmers in a blurry superposition of several translucent copies, a giant magnifying glass slowly approaches,
a bright camera flash goes off, instantly all copies collapse into one solid opaque Qubi that freezes
with a surprised expression, dramatic slow motion
```

### 10 · 한줄 평 (55–60초 · 5초 생성)
- **화면:** 큐비가 손을 흔들며 별 사이로 천천히 떠오른다. 따뜻하고 희망적인 빛. 가운데는 글자 자리로 넓게 비운다
- **자막:** 큐비트는 금방 잊는다. / 그 짧은 순간을 여럿이 나눠 쓰게 하는 것, / 그게 양자 OS다.
```
Qubi waves goodbye and slowly floats upward into a starry sky at the very top of the frame, warm hopeful light,
soft bokeh stars, large empty dark area in the center, gentle camera tilt up
```

---

## 3. 잘 안 될 때

| 증상 | 해결 |
|---|---|
| 장면마다 큐비 생김새가 다르다 | image-to-video로 `qubi.png`를 첫 프레임에 넣는다. 또는 툴의 "캐릭터 참조" 기능을 쓴다 |
| 영상에 이상한 글자가 생긴다 | 네거티브에 `text, letters`를 넣고 다시 생성한다. 어쩔 수 없으면 `CROP_X`로 피한다 |
| 주인공이 자막 패널에 가려진다 | 프롬프트에 `in the upper half of the frame`을 붙인다 |
| 동작이 너무 빠르거나 느리다 | 5초 클립을 10초 장면에 쓰면 반복된다. 10초로 다시 생성하거나 프롬프트에 `slow motion`을 붙인다 |
