# unified_streamlit_app

기능별로 흩어진 Streamlit 데모를 **하나의 멀티페이지 Streamlit 앱**으로 통합한 프로젝트입니다.

## 실행 방법

- `.streamlit/config.toml`: 밝은 로즈/핑크 테마(발표·시연용)
- API 키는 환경 변수 또는 `.streamlit/secrets.toml` (Git에 올리지 마세요)

1) 가상환경 생성/활성화 (권장)

2) 의존성 설치(기본)

```bash
pip install -r requirements.txt
```

2-1) 의존성 “업그레이드”(권장)

```bash
pip install -U -r requirements-upgrade.txt
```

3) OpenAI API Key 설정

키가 **삭제·유실**된 경우, 문자열은 복구할 수 없으니 [OpenAI](https://platform.openai.com/api-keys)에서 **새 키를 발급**한 뒤 아래 중 하나로 넣으세요.

**방법 A — Streamlit secrets (권장)**  
- `Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml`  
- `secrets.toml` 을 열어 `OPENAI_API_KEY = "sk-..."` 저장  

**방법 B — `.env`**  
- `Copy-Item .env.example .env` 후 `OPENAI_API_KEY=sk-...` 저장 (`pip install python-dotenv` 필요)

**방법 C — 환경 변수 (세션 한정)**

```powershell
$env:OPENAI_API_KEY="YOUR_KEY"
```

4) 실행

```bash
streamlit run app.py
```

## 버전 고정(재현 가능한 환경 만들기)

업그레이드 후 현재 환경을 그대로 고정하려면 아래처럼 lock 파일을 만들면 됩니다.

```bash
pip freeze > requirements.lock
```

다음부터는 아래로 동일 환경 재구성이 가능합니다.

```bash
pip install -r requirements.lock
```

## 폴더 구조

- `app.py`: 메인(랜딩) · 단계 안내
- `pages/`: `01` AI 프로필 → `02` 매칭 → `03` 인사말 → `04` 대화 도우미
- `_ui.py`: 테마·내비·공통 셸
- `_persistence.py`: 로컬 임시저장(`data/app_session_state.json`)
- `assets/`: 이미지 등 리소스
- `data/`: `profile_db.jsonl` 등 데이터
- `indexes/`: `conv_index` (RAG용 FAISS, 없으면 ④ RAG 모드만 비활성 안내)

