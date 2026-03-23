# FAISS 인덱스 (대화 RAG)

④ **비슷한 대화 참고** 는 `indexes/conv_index/` 안의 `index.faiss`, `index.pkl` 이 있어야 동작합니다.

## 한 번만 빌드하기

프로젝트 **루트**에서:

```powershell
pip install python-dotenv langchain-openai langchain-community faiss-cpu
python scripts/build_conv_index.py
```

- `data/conv_samples.jsonl` 을 읽어 OpenAI 임베딩으로 인덱스를 만듭니다.
- `.env` 또는 환경 변수에 `OPENAI_API_KEY` 가 있어야 합니다.

빌드 후 Streamlit을 다시 실행하세요.

## 샘플 추가

`data/conv_samples.jsonl` 에 한 줄에 JSON 하나:

```json
{"id": "x1", "text": "A: …\nB: …"}
```

추가한 뒤 위 스크립트를 다시 실행하면 인덱스가 갱신됩니다.
