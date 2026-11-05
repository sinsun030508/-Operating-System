# 큐비트에게도 운영체제가 필요할까?

운영체제 과목 과제 — **양자 컴퓨터 1분 영상** (9:16 · 360×640 · 60초)

> 양자 컴퓨터를 "0과 1을 동시에"에서 멈추지 않고, **우리가 배운 OS 개념(스케줄링·가상 메모리·드라이버·
> 오류 검출·디버깅)으로 다시 읽는다.** 큐비트는 수백 μs 만에 상태를 잃기 때문에, 양자 OS의 핵심 자원은 '시간'이다.

<p align="center"><img src="media/preview.gif" width="200" alt="영상 미리보기 (2배속)"></p>

▶ **완성 영상:** [`media/quantum_os_shorts.mp4`](media/quantum_os_shorts.mp4) · 📄 **레포트:** [`docs/report.pdf`](docs/report.pdf) ([md](docs/report.md))

## 구성 (과제 조건: 0–5초 타이틀 · 5–55초 내용 · 55–60초 한줄 평)

| 시간 | 장면 | OS 개념 |
|---|---|---|
| 0–5초 | **타이틀** — 큐비트에게도 운영체제가 필요할까? | |
| 5–13초 | 비트와 큐비트 (중첩) | |
| 13–20초 | 큐비트 50개 → 2⁵⁰ ≈ 1,126조 상태 | |
| 20–28초 | 결어긋남 — 큐비트는 금방 잊는다 | 실시간 스케줄링 (마감) |
| 28–33초 | 여러 사용자의 회로를 한 QPU에 | CPU 스케줄링 |
| 33–38초 | 가상 큐비트 주소 → 실제 큐비트 | 가상 메모리 |
| 38–43초 | QPU는 고전 컴퓨터가 부리는 장치 | 디바이스 드라이버 |
| 43–48초 | 물리 큐비트 여럿 → 논리 큐비트 1개 | 오류 검출 (ECC·RAID) |
| 48–55초 | `print(qubit)` 하는 순간 상태 붕괴 | 디버깅 |
| 55–60초 | **한줄 평** — 큐비트는 금방 잊는다. 그 짧은 순간을 여럿이 나눠 쓰게 하는 것, 그게 양자 OS다. | |

## 파일

| 경로 | 내용 |
|---|---|
| `media/quantum_os_shorts.mp4` | 완성 영상 (코드로 생성한 모션그래픽 버전) |
| `docs/report.pdf` · `report.md` | 레포트 — 기획 의도, 콘티(장면 캡처), 제작 방법, 사실 확인, 참고 문헌 |
| `make_report_pdf.py` | `report.md` → A4 PDF 변환 (Chrome/Edge 명령줄 인쇄) |
| `make_video.py` | 영상 전체를 코드로 그리는 생성기 (Pillow + ffmpeg, 배경음 직접 합성) |
| `compose.py` | **AI 애니메이션 버전** 합성기 — `clips/`의 AI 영상 + `voice/`의 AI 내레이션 + 자막·BGM |
| `docs/prompts.md` | Kling 등 영상 AI용 장면별 프롬프트 (마스코트 「큐비」) |
| `docs/narration.md` | 장면 길이에 맞춘 내레이션 대본 (클로바더빙 등 TTS용) |
| `docs/실행방법.md` | Windows · Mac 실행 방법과 자주 나는 오류 |

## 실행

```bash
pip install pillow numpy          # + ffmpeg 필요 (docs/실행방법.md)
python make_video.py              # 코드 애니메이션 버전 → media/quantum_os_shorts.mp4
python compose.py --preview       # AI 버전 장면 미리보기 → preview_ai.png
python compose.py --audio         # 내레이션 길이표 + mix.wav
python compose.py                 # AI 버전 완성본 → media/quantum_os_ai.mp4
```

`clips/`·`voice/`가 비어 있으면 해당 장면은 코드 애니메이션과 배경음악으로 대체되므로, 클립을 하나씩 넣으며 확인할 수 있다.

## 참고 문헌

1. E. Giortamis, F. Romão, N. Tornow, P. Bhatotia, "QOS: A Quantum Operating System," *USENIX OSDI '25*, 2025.
2. C. Delle Donne et al., "An operating system for executing applications on quantum network nodes," *Nature* 639, 2025.
