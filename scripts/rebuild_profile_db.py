# -*- coding: utf-8 -*-
"""profile_db.jsonl 재구성: 기존 행에 id·확장 필드 부여 + 신규 프로필 추가."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "profile_db.jsonl"
OUT = ROOT / "data" / "profile_db.jsonl"

_LIFESTYLES = [
    "집순이/집돌이",
    "활동형",
    "균형형",
    "주말 낮 선호",
    "밤 활동형",
    "술자리 적음",
    "계획형",
    "즉흥형",
]
_DATING = [
    "천천히 친해지는 편",
    "연락은 적당히, 부담 없이",
    "표현은 담백한 편",
    "상황 보면 리드도 가능",
    "배려와 예의 중시",
    "안정감 있는 관계 선호",
    "공통 취미로 가까워지고 싶음",
]
_CONV = [
    "차분한 편",
    "가벼운 유머 섞는 편",
    "상대 말 끝까지 듣는 편",
    "리액션 잘하는 편",
    "질문으로 대화 이어가는 편",
    "경청 위주",
    "솔직하지만 무례하진 않게",
    "처음엔 조심스럽게",
    "에너지는 있는 편",
]


def _enrich_row(obj: dict, idx: int) -> dict:
    o = dict(obj)
    o["id"] = f"p{idx + 1:04d}"
    o.setdefault("lifestyle", _LIFESTYLES[idx % len(_LIFESTYLES)])
    o.setdefault("dating_style", _DATING[idx % len(_DATING)])
    o.setdefault("conversation_style", _CONV[idx % len(_CONV)])
    if "tags" not in o:
        job = str(o.get("job", ""))
        kws = o.get("keywords") or []
        extra = [x for x in (kws[:2] if isinstance(kws, list) else [])]
        o["tags"] = extra + [job[:6] + " 일상"] if job else extra
    return o


# 신규 55명 — 관심사·직업·문체 분산 (현실적인 톤)
NEW: list[dict] = [
    {"name": "고은별", "age": 27, "gender": "여자", "job": "대학원생 (도시계획)", "bio": "논문 때문에 야근이 잦아요. 스트레스는 밤 산책이나 맛집 탐방으로 풀어요. 처음엔 말이 짧을 수 있는데 편해지면 수다 많아져요.", "keywords": ["산책", "맛집", "독서", "자기계발"], "lifestyle": "균형형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "처음엔 조심스럽게", "tags": ["석사", "야근", "조용한 카페"]},
    {"name": "남기찬", "age": 29, "gender": "남자", "job": "백엔드 개발자", "bio": "장애 대응하다 보면 하루가 순삭이에요. 주말엔 러닝이나 헬스로 리셋. 드라마보단 다큐나 팟캐스트를 더 듣는 편.", "keywords": ["러닝", "헬스", "팟캐스트", "자기계발"], "lifestyle": "활동형", "dating_style": "천천히 친해지는 편", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["야근", "운동 루틴"]},
    {"name": "류하람", "age": 26, "gender": "여자", "job": "콘텐츠 마케터", "bio": "짧은 영상 기획이 일이에요. 퇴근 후엔 요가 한 번이 없으면 허리가 뻐근해요. 전시나 팝업스토어 구경 좋아해요.", "keywords": ["요가", "전시", "영화", "카페"], "lifestyle": "주말 낮 선호", "dating_style": "공통 취미로 가까워지고 싶음", "conversation_style": "리액션 잘하는 편", "tags": ["SNS", "팝업"]},
    {"name": "모태성", "age": 33, "gender": "남자", "job": "공기업 사무", "bio": "규칙적인 출퇴근이 몸에 배었어요. 술자리는 가끔만 가고, 대신 보드게임 모임이 취미. 말은 천천히 하는 편이에요.", "keywords": ["보드게임", "독서", "영화", "산책"], "lifestyle": "술자리 적음", "dating_style": "안정감 있는 관계 선호", "conversation_style": "차분한 편", "tags": ["정시퇴근", "모임"]},
    {"name": "문세린", "age": 28, "gender": "여자", "job": "초등 교사", "bio": "아이들한테 말 많이 해서 퇴근하면 조용한 걸 찾게 돼요. 집에서 드라마 한 편 보거나 반려묘랑 노는 게 힐링.", "keywords": ["드라마", "반려동물", "요리", "독서"], "lifestyle": "집순이/집돌이", "dating_style": "배려와 예의 중시", "conversation_style": "경청 위주", "tags": ["고양이", "퇴근 후 휴식"]},
    {"name": "민도현", "age": 31, "gender": "남자", "job": "영상 편집자", "bio": "컷 편집하다 보면 밤이 금방 가요. 낮에 햇살 받으며 촬영 다니는 건 좋아하는데 편집실은 어두운 게 편해요. 캠핑은 가끔 친구들이랑.", "keywords": ["캠핑", "영화", "음악", "사진"], "lifestyle": "밤 활동형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "가벼운 유머 섞는 편", "tags": ["프리랜서", "야행성"]},
    {"name": "백지우", "age": 25, "gender": "여자", "job": "빵집 점장", "bio": "새벽 출근이라 저녁 데이트가 더 맞아요. 오븐 냄새 말고 커피 마시며 쉬는 시간이 소중해요. 맛집 리스트는 메모장에 가득.", "keywords": ["맛집", "커피", "베이킹", "산책"], "lifestyle": "주말 낮 선호", "dating_style": "배려와 예의 중시", "conversation_style": "리액션 잘하는 편", "tags": ["새벽 근무", "디저트"]},
    {"name": "서동혁", "age": 36, "gender": "남자", "job": "중소기업 대표", "bio": "일이 우선인 시기였는데 이제는 균형을 찾는 중이에요. 골프보다는 낚시나 드라이브가 맞아요. 말보다 행동으로 챙기는 타입.", "keywords": ["낚시", "여행", "와인", "독서"], "lifestyle": "계획형", "dating_style": "안정감 있는 관계 선호", "conversation_style": "차분한 편", "tags": ["바쁨", "드라이브"]},
    {"name": "신유나", "age": 30, "gender": "여자", "job": "병원 코디네이터", "bio": "환자 분들 안내하다 보면 하루가 빨리 가요. 스트레스는 필라테스랑 명상으로 풀어요. 주말 브런치 예약하는 재미가 있어요.", "keywords": ["필라테스", "명상", "카페", "영화"], "lifestyle": "균형형", "dating_style": "표현은 담백한 편", "conversation_style": "질문으로 대화 이어가는 편", "tags": ["브런치", "건강"]},
    {"name": "안세진", "age": 27, "gender": "남자", "job": "게임 QA", "bio": "버그 찾는 게 일이에요. 집에서 인디 게임 깨는 것도 일의 연장 같아요. 가끔 롤드컵 시즌엔 밤샘도 해요.", "keywords": ["게임", "영화", "음악", "자기계발"], "lifestyle": "집순이/집돌이", "dating_style": "천천히 친해지는 편", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["PC방", "e스포츠"]},
    {"name": "양하은", "age": 29, "gender": "여자", "job": "패션 스타일리스트", "bio": "촬영장에서 바쁘게 돌아다녀요. 개인 시간엔 빈티지 샵이나 편집숍 구경. 옷 얘기 말고도 잡담 좋아해요.", "keywords": ["패션", "전시", "카페", "사진"], "lifestyle": "활동형", "dating_style": "상황 보면 리드도 가능", "conversation_style": "에너지는 있는 편", "tags": ["촬영", "빈티지"]},
    {"name": "엄지후", "age": 32, "gender": "남자", "job": "회계사무소 직원", "bio": "세금 신고 시즌만 피하면 나름 여유 있어요. 퇴근 후 헬스 가거나 동네 맥주집에서 한 잔. 말수는 적은 편인데 듣는 건 잘해요.", "keywords": ["헬스", "맥주", "독서", "야구"], "lifestyle": "술자리 적음", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "경청 위주", "tags": ["야구 직관", "동네 술집"]},
    {"name": "오채원", "age": 24, "gender": "여자", "job": "뮤지션 (보컬)", "bio": "버스킹이랑 작은 공연 위주로 활동해요. 낮엔 녹음실, 밤엔 공연이라 스케줄이 들쭉날쭉해요. 조용한 카페에서 얘기 나누는 거 좋아해요.", "keywords": ["음악", "공연", "카페", "산책"], "lifestyle": "즉흥형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "리액션 잘하는 편", "tags": ["버스킹", "야간 공연"]},
    {"name": "우재빈", "age": 28, "gender": "남자", "job": "데이터 엔지니어", "bio": "파이프라인 잡다 보면 시간이 훅 가요. 주말엔 등산이나 러닝으로 머리 비우기. 카페에 노트북 들고 가도 일 안 하고 멍 때리기도 해요.", "keywords": ["등산", "러닝", "커피", "독서"], "lifestyle": "활동형", "dating_style": "천천히 친해지는 편", "conversation_style": "질문으로 대화 이어가는 편", "tags": ["오픈소스", "새벽 러닝"]},
    {"name": "원지안", "age": 31, "gender": "여자", "job": "출판 편집자", "bio": "원고 읽고 저자랑 소통하는 게 일이에요. 퇴근 후 서점이나 도서관 가면 마음이 편해져요. 드라마는 한 번에 몰아보기.", "keywords": ["독서", "드라마", "카페", "전시"], "lifestyle": "집순이/집돌이", "dating_style": "표현은 담백한 편", "conversation_style": "경청 위주", "tags": ["원고", "서점"]},
    {"name": "유승호", "age": 34, "gender": "남자", "job": "영업 사원", "bio": "사람 만나는 게 일이라 개인 시간엔 조용한 걸 찾게 돼요. 골프는 동호회 때문에 가끔, 진짜 취미는 낚시예요.", "keywords": ["낚시", "골프", "맛집", "와인"], "lifestyle": "균형형", "dating_style": "상황 보면 리드도 가능", "conversation_style": "가벼운 유머 섞는 편", "tags": ["출장", "회식"]},
    {"name": "윤서하", "age": 26, "gender": "여자", "job": "애견 미용사", "bio": "강아지들 손질하다 보면 기분이 좋아져요. 퇴근 후 우리 집 말티즈 산책이 일과예요. 사람보다 동물 얘기를 더 잘할 수도…", "keywords": ["반려동물", "산책", "카페", "요리"], "lifestyle": "활동형", "dating_style": "배려와 예의 중시", "conversation_style": "리액션 잘하는 편", "tags": ["애견카페", "말티즈"]},
    {"name": "이한결", "age": 30, "gender": "남자", "job": "제품 디자이너", "bio": "피그마랑 친구예요. 전시나 소품샵 가면 아이디어가 샘솟아요. 밤에 작업할 때가 많아 연락이 늦을 수 있어요.", "keywords": ["디자인", "전시", "카페", "사진"], "lifestyle": "밤 활동형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["UI", "소품샵"]},
    {"name": "장미소", "age": 29, "gender": "여자", "job": "영양사", "bio": "급식 메뉴 짜는 일이에요. 집에선 오히려 간단히 먹어요. 주말엔 재래시장 가서 재료 사고 요리하는 게 취미.", "keywords": ["요리", "맛집", "산책", "요가"], "lifestyle": "계획형", "dating_style": "안정감 있는 관계 선호", "conversation_style": "상대 말 끝까지 듣는 편", "tags": ["시장", "건강식"]},
    {"name": "전우석", "age": 27, "gender": "남자", "job": "스포츠 트레이너", "bio": "낮엔 체육관, 저녁엔 개인 레슨이에요. 본인 운동은 주로 수영이랑 크로스핏. 식단은 안 지켜도 말하지 말아 주세요.", "keywords": ["헬스", "수영", "음악", "맛집"], "lifestyle": "활동형", "dating_style": "상황 보면 리드도 가능", "conversation_style": "에너지는 있는 편", "tags": ["크로스핏", "레슨"]},
    {"name": "정나래", "age": 28, "gender": "여자", "job": "HR 담당자", "bio": "면접과 행사 준비로 바쁜 날이 많아요. 힐링은 친구들이랑 소극장 공연이나 연극 보는 거예요. 첫 만남에 너무 깊은 얘기는 살짝 부담.", "keywords": ["공연", "영화", "카페", "독서"], "lifestyle": "균형형", "dating_style": "천천히 친해지는 편", "conversation_style": "처음엔 조심스럽게", "tags": ["연극", "면접"]},
    {"name": "조이준", "age": 35, "gender": "남자", "job": "건축 설계사무소 소장", "bio": "현장이랑 사무실 오가다 보면 하루가 금방 가요. 주말엔 미술관이나 건축 투어 다녀요. 말은 짧게, 생각은 깊게 하는 편.", "keywords": ["건축", "전시", "사진", "커피"], "lifestyle": "주말 낮 선호", "dating_style": "표현은 담백한 편", "conversation_style": "차분한 편", "tags": ["설계", "투어"]},
    {"name": "지유진", "age": 25, "gender": "여자", "job": "일러스트 매니저", "bio": "작가님들 일정 잡고 커뮤니케이션하는 역할이에요. 그림 구경하는 건 여전히 좋아해요. 집에서 게임도 자주 해요.", "keywords": ["게임", "전시", "카페", "독서"], "lifestyle": "집순이/집돌이", "dating_style": "공통 취미로 가까워지고 싶음", "conversation_style": "리액션 잘하는 편", "tags": ["일러스트", "스위치"]},
    {"name": "차민혁", "age": 32, "gender": "남자", "job": "약사 (조제)", "bio": "처방 받으시는 분들 상담하다 보면 보람 있어요. 퇴근 후엔 조용한 술집보다 카페에서 책 읽는 걸 선호해요.", "keywords": ["독서", "카페", "영화", "산책"], "lifestyle": "술자리 적음", "dating_style": "안정감 있는 관계 선호", "conversation_style": "경청 위주", "tags": ["건강 상담", "조제"]},
    {"name": "채은성", "age": 30, "gender": "여자", "job": "라디오 작가", "bio": "새벽 방송 준비하다 보면 생활 패턴이 좀 특이해요. 낮에 잠자고 저녁에 일하는 날도 많아요. 팟캐스트랑 오디오북 즐겨 들어요.", "keywords": ["음악", "독서", "카페", "영화"], "lifestyle": "밤 활동형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "가벼운 유머 섞는 편", "tags": ["방송", "오디오"]},
    {"name": "천우영", "age": 29, "gender": "남자", "job": "여행사 상품기획", "bio": "패키지 짜다 보면 제가 더 가고 싶어져요. 실제로는 짧은 국내 여행 자주 다녀요. 계획은 세우되 유연하게 바꾸는 편.", "keywords": ["여행", "사진", "맛집", "카페"], "lifestyle": "즉흥형", "dating_style": "상황 보면 리드도 가능", "conversation_style": "질문으로 대화 이어가는 편", "tags": ["국내여행", "기획"]},
    {"name": "최다은", "age": 27, "gender": "여자", "job": "플로리스트 (온라인)", "bio": "배송 주문 받아서 집에서 작업해요. 사람 많은 데는 피하고 싶은 날이 많아요. 대신 꽃 시장 가는 건 좋아해요.", "keywords": ["꽃", "요리", "영화", "산책"], "lifestyle": "집순이/집돌이", "dating_style": "천천히 친해지는 편", "conversation_style": "조심스러운 편", "tags": ["재택", "꽃시장"]},
    {"name": "한동욱", "age": 31, "gender": "남자", "job": "소방관", "bio": "당번이 많아서 연락이 끊길 수 있어요. 쉬는 날엔 무조건 야외로 나가요. 캠핑이랑 등산이 제일 리프레시.", "keywords": ["캠핑", "등산", "운동", "음악"], "lifestyle": "활동형", "dating_style": "배려와 예의 중시", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["당번", "야외"]},
    {"name": "허지민", "age": 28, "gender": "여자", "job": "UX 라이터", "bio": "버튼 문구 하나에도 진심인 직업이에요. 사용자 인터뷰 보러 카페 자주 가요. 퇴근 후엔 필라테스로 거북목 관리 중.", "keywords": ["카페", "필라테스", "독서", "전시"], "lifestyle": "균형형", "dating_style": "표현은 담백한 편", "conversation_style": "질문으로 대화 이어가는 편", "tags": ["카피", "인터뷰"]},
    {"name": "강민재", "age": 33, "gender": "남자", "job": "투자 심사역", "bio": "숫자랑 사람 얘기를 같이 봐요. 술자리는 최소화하려 하고, 대신 와인 한 잔 하면서 얘기하는 건 좋아해요.", "keywords": ["와인", "독서", "골프", "자기계발"], "lifestyle": "술자리 적음", "dating_style": "안정감 있는 관계 선호", "conversation_style": "차분한 편", "tags": ["재무", "심사"]},
    {"name": "구하영", "age": 26, "gender": "여자", "job": "댄스 강사", "bio": "주간엔 키즈 클래스, 주말엔 성인 반 수업이에요. 몸 쓰는 만큼 먹는 것도 좋아해요. 조용한 영화관이 데이트로 편해요.", "keywords": ["댄스", "영화", "맛집", "음악"], "lifestyle": "활동형", "dating_style": "상황 보면 리드도 가능", "conversation_style": "에너지는 있는 편", "tags": ["스튜디오", "키즈"]},
    {"name": "길태오", "age": 37, "gender": "남자", "job": "요리 연구가 (프리랜서)", "bio": "레시피 개발하고 글 써요. 맛집보다 시장이나 재료 산지 가는 게 더 설레요. 집에서 밥 해주는 걸 좋아하는 편.", "keywords": ["요리", "맛집", "와인", "독서"], "lifestyle": "계획형", "dating_style": "배려와 예의 중시", "conversation_style": "경청 위주", "tags": ["레시피", "시장"]},
    {"name": "나예진", "age": 29, "gender": "여자", "job": "세무사 보조", "bio": "증빙 정리하다 보면 하루가 가요. 정확한 걸 좋아해서 약속 시간도 지키려 해요. 쉴 땐 산책이랑 카페가 제일 편해요.", "keywords": ["산책", "카페", "독서", "영화"], "lifestyle": "균형형", "dating_style": "안정감 있는 관계 선호", "conversation_style": "차분한 편", "tags": ["세무", "꼼꼼"]},
    {"name": "도현우", "age": 28, "gender": "남자", "job": "모션 그래픽 디자이너", "bio": "애니메이션처럼 움직이는 그래픽 만드는 일이에요. 영화 엔딩 크레딛 보면 직업병 와요. 게임도 좋아하고요.", "keywords": ["영화", "게임", "음악", "카페"], "lifestyle": "밤 활동형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "가벼운 유머 섞는 편", "tags": ["애프터이펙트", "크레딧"]},
    {"name": "라은지", "age": 31, "gender": "여자", "job": "심리상담 센터 코디네이터", "bio": "예약 잡고 상담 일정 맞추는 일이에요. 직접 상담은 아니에요. 퇴근 후 명상 앱 켜고 하루 정리하는 게 루틴.", "keywords": ["명상", "독서", "요가", "카페"], "lifestyle": "집순이/집돌이", "dating_style": "천천히 친해지는 편", "conversation_style": "경청 위주", "tags": ["예약", "멘탈케어"]},
    {"name": "마서준", "age": 30, "gender": "남자", "job": "자동차 정비사", "bio": "손으로 만지는 일이 좋아요. 퇴근 후엔 드라이브나 세차가 취미. 말은 많지 않은데 진지하게 들어줘요.", "keywords": ["드라이브", "음악", "맛집", "영화"], "lifestyle": "활동형", "dating_style": "표현은 담백한 편", "conversation_style": "상대 말 끝까지 듣는 편", "tags": ["정비", "차"]},
    {"name": "박솔미", "age": 27, "gender": "여자", "job": "스포츠 저널리스트", "bio": "경기장 자주 나가요. 집에선 축구 안 보고 예능 보는 식으로 머리 비워요. 맥주 한 캔이면 충분해요.", "keywords": ["스포츠", "영화", "맥주", "여행"], "lifestyle": "즉흥형", "dating_style": "공통 취미로 가까워지고 싶음", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["취재", "축구"]},
    {"name": "석민국", "age": 34, "gender": "남자", "job": "음식점 운영", "bio": "주방과 홀 오가다 보면 하루 종일 서 있어요. 쉬는 날엔 다른 동네 맛집 레퍼런스 쌓으러 다녀요.", "keywords": ["맛집", "요리", "와인", "여행"], "lifestyle": "주말 낮 선호", "dating_style": "상황 보면 리드도 가능", "conversation_style": "가벼운 유머 섞는 편", "tags": ["레스토랑", "레퍼런스"]},
    {"name": "송이현", "age": 25, "gender": "여자", "job": "대학원생 (통계)", "bio": "코드랑 숫자랑 씨름해요. 스트레스는 친구들이랑 보드게임 카페. 연애는 서두르기보다 맞는 사람이면 천천히.", "keywords": ["보드게임", "커피", "독서", "자기계발"], "lifestyle": "집순이/집돌이", "dating_style": "천천히 친해지는 편", "conversation_style": "조심스러운 편", "tags": ["R코드", "통계"]},
    {"name": "신동욱", "age": 29, "gender": "남자", "job": "크리에이티브 디렉터", "bio": "브랜드 캠페인 방향 잡는 일이에요. 아이디어 회의는 즐거운데 밤샘은 힘들어요. 전시랑 팝업 자주 찾아다녀요.", "keywords": ["전시", "영화", "카페", "사진"], "lifestyle": "밤 활동형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "에너지는 있는 편", "tags": ["캠페인", "브랜드"]},
    {"name": "안소희", "age": 32, "gender": "여자", "job": "한의원 원무", "bio": "환자 응대와 보험 처리가 주 업무예요. 성격은 무던한 편이에요. 주말엔 요가랑 가벼운 등산으로 몸 풀어요.", "keywords": ["요가", "등산", "독서", "카페"], "lifestyle": "균형형", "dating_style": "안정감 있는 관계 선호", "conversation_style": "상대 말 끝까지 듣는 편", "tags": ["한의원", "원무"]},
    {"name": "오세빈", "age": 28, "gender": "남자", "job": "음대 강사", "bio": "피아노 레슨이 주 업무예요. 주말엔 연주회 가거나 학생 발표회. 클래식 말고 재즈도 좋아해요.", "keywords": ["음악", "공연", "카페", "독서"], "lifestyle": "주말 낮 선호", "dating_style": "표현은 담백한 편", "conversation_style": "차분한 편", "tags": ["레슨", "재즈"]},
    {"name": "유채은", "age": 26, "gender": "여자", "job": "웹 디자이너", "bio": "원격 근무라 집에만 있으면 우울해서 카페에서 일해요. 디자인 말고도 잡담 좋아해요. 반려견 키워요.", "keywords": ["디자인", "카페", "반려동물", "영화"], "lifestyle": "집순이/집돌이", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "리액션 잘하는 편", "tags": ["재택", "반려견"]},
    {"name": "윤도겸", "age": 35, "gender": "남자", "job": "물류 관리자", "bio": "창고랑 시스템 보며 하루 보내요. 퇴근 후 헬스 가는 게 루틴. 주말엔 아이들이랑 캠핑 가려고 연습 중이에요.", "keywords": ["헬스", "캠핑", "음악", "맛집"], "lifestyle": "계획형", "dating_style": "안정감 있는 관계 선호", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["창고", "가족"]},
    {"name": "이다윤", "age": 30, "gender": "여자", "job": "큐레이터 보조", "bio": "전시 설치랑 도슨트 일 돕는 일이에요. 작가 인터뷰 정리하는 것도 좋아해요. 사람 많은 개막식은 조금 피곤해요.", "keywords": ["전시", "독서", "카페", "영화"], "lifestyle": "균형형", "dating_style": "천천히 친해지는 편", "conversation_style": "경청 위주", "tags": ["미술관", "도슨트"]},
    {"name": "임재혁", "age": 27, "gender": "남자", "job": "스타트업 PM", "bio": "스프린트마다 목표가 바뀌어요. 러닝 크루 나가며 스트레스 풀어요. 회의 많은 날엔 연락 늦을 수 있어요.", "keywords": ["러닝", "커피", "자기계발", "영화"], "lifestyle": "활동형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "질문으로 대화 이어가는 편", "tags": ["스프린트", "크루"]},
    {"name": "장하람", "age": 28, "gender": "여자", "job": "패션 MD", "bio": "시즌 샘플이랑 숫자 싸움이에요. 퇴근 후엔 찜질방 가거나 집에서 드라마. 술은 한두 잔이면 충분해요.", "keywords": ["드라마", "카페", "여행", "요가"], "lifestyle": "술자리 적음", "dating_style": "표현은 담백한 편", "conversation_style": "가벼운 유머 섞는 편", "tags": ["샘플", "찜질방"]},
    {"name": "정우람", "age": 31, "gender": "남자", "job": "카메라 기자", "bio": "현장 나가 촬영하는 일이에요. 급한 뉴스 있으면 연락 두절될 수 있어요. 쉴 땐 사진 없이 산책만 해요.", "keywords": ["사진", "산책", "영화", "음악"], "lifestyle": "즉흥형", "dating_style": "배려와 예의 중시", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["취재", "현장"]},
    {"name": "조아린", "age": 24, "gender": "여자", "job": "성우 지망생", "bio": "학원 다니며 녹음 연습 중이에요. 아르바이트는 카페. 목소리 얘기 말고도 잡화 얘기 잘해요.", "keywords": ["음악", "영화", "카페", "게임"], "lifestyle": "집순이/집돌이", "dating_style": "천천히 친해지는 편", "conversation_style": "리액션 잘하는 편", "tags": ["녹음", "학원"]},
    {"name": "지한솔", "age": 33, "gender": "남자", "job": "IT 보안 컨설턴트", "bio": "고객사 점검 다니다 보면 한 주가 금방 가요. 집에선 넷플릭스보다 유튜브 기술 채널. 등산은 가끔 동호회로.", "keywords": ["등산", "독서", "게임", "자기계발"], "lifestyle": "균형형", "dating_style": "안정감 있는 관계 선호", "conversation_style": "차분한 편", "tags": ["보안", "점검"]},
    {"name": "진유미", "age": 29, "gender": "여자", "job": "호텔 프론트", "bio": "밤 근무도 있어서 생활이 불규칙해요. 낮엔 잠자고 저녁에 산책. 여행은 직업병으로 호텔 리뷰부터 봐요.", "keywords": ["여행", "산책", "카페", "영화"], "lifestyle": "밤 활동형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "배려형", "tags": ["교대근무", "호텔"]},
    {"name": "채민수", "age": 36, "gender": "남자", "job": "농협 직원", "bio": "지역 축제나 장터 일정 잡는 일도 해요. 술은 회식 때만 적당히. 주말엔 등산이나 동네 봉사 활동으로 시간 보내요.", "keywords": ["등산", "독서", "여행", "음악"], "lifestyle": "주말 낮 선호", "dating_style": "안정감 있는 관계 선호", "conversation_style": "차분한 편", "tags": ["지역", "봉사"]},
    {"name": "한별", "age": 27, "gender": "여자", "job": "독립 출판 편집", "bio": "책 만드는 일 작지만 보람 있어요. 저자들이랑 카페에서 만나 원고 얘기해요. 소개팅은 오랜만이라 어색할 수 있어요.", "keywords": ["독서", "카페", "전시", "영화"], "lifestyle": "집순이/집돌이", "dating_style": "천천히 친해지는 편", "conversation_style": "조심스러운 편", "tags": ["출판", "원고"]},
    {"name": "허대윤", "age": 30, "gender": "남자", "job": "전기 기술자", "bio": "현장 다니며 설비 점검해요. 손으로 고치는 일이 좋아요. 퇴근 후 맥주 한 잔이면 하루 피로가 풀려요.", "keywords": ["맥주", "야구", "영화", "등산"], "lifestyle": "활동형", "dating_style": "표현은 담백한 편", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["현장", "설비"]},
    {"name": "황서연", "age": 28, "gender": "여자", "job": "영양 상담사", "bio": "1:1 상담으로 식단 짜드려요. 본인은 주말엔 치팅데이 있어요. 요가로 죄책감 줄이는 중.", "keywords": ["요가", "요리", "맛집", "산책"], "lifestyle": "균형형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "가벼운 유머 섞는 편", "tags": ["상담", "식단"]},
    {"name": "황태민", "age": 32, "gender": "남자", "job": "대학 조교", "bio": "박사 과정 밟는 중이라 월급은 별로예요. 주말엔 과외나 연구실. 그래도 전시 무료일 때 미술관 가는 건 놓치지 않아요.", "keywords": ["전시", "독서", "카페", "영화"], "lifestyle": "계획형", "dating_style": "천천히 친해지는 편", "conversation_style": "경청 위주", "tags": ["연구", "조교"]},
    {"name": "강서윤", "age": 26, "gender": "여자", "job": "앱 테스터", "bio": "버그 리포트 쓰는 일이에요. 집돌이 기질 있어요. 가끔 친구들이랑 PC방 가면 스트레스 풀려요.", "keywords": ["게임", "영화", "카페", "독서"], "lifestyle": "집순이/집돌이", "dating_style": "공통 취미로 가까워지고 싶음", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["QA", "PC방"]},
    {"name": "권도영", "age": 29, "gender": "남자", "job": "항공 정비사", "bio": "비행기 전에 점검하는 일이에요. 비행기는 좋은데 제가 여행 자주 가지는 못해요. 쉴 땐 집에서 영화 마라톤.", "keywords": ["영화", "음악", "맛집", "여행"], "lifestyle": "균형형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "차분한 편", "tags": ["야간근무", "정비"]},
    {"name": "기다은", "age": 31, "gender": "여자", "job": "브랜드 SNS 운영", "bio": "캡션 짜고 댓글 응대하는 일이에요. 트렌드 따라가느라 피곤할 때 전시 보러 가요. 사진 찍는 건 서툴러요.", "keywords": ["전시", "카페", "영화", "맛집"], "lifestyle": "활동형", "dating_style": "상황 보면 리드도 가능", "conversation_style": "리액션 잘하는 편", "tags": ["SNS", "캡션"]},
    {"name": "김도윤", "age": 34, "gender": "남자", "job": "부동산 중개인", "bio": "사람 만나는 게 일이에요. 솔직히 퇴근 후엔 말하기 싫은 날도 있어요. 그럴 땐 러닝이나 헬스.", "keywords": ["러닝", "헬스", "맛집", "와인"], "lifestyle": "술자리 적음", "dating_style": "상황 보면 리드도 가능", "conversation_style": "가벼운 유머 섞는 편", "tags": ["매물", "중개"]},
    {"name": "남시우", "age": 28, "gender": "여자", "job": "리서치 애널리스트", "bio": "리포트 쓰다 보면 야근 각이에요. 주말엔 반드시 야외로 나가요. 캠핑 장비 늘리는 게 취미…", "keywords": ["캠핑", "등산", "독서", "커피"], "lifestyle": "활동형", "dating_style": "안정감 있는 관계 선호", "conversation_style": "질문으로 대화 이어가는 편", "tags": ["리포트", "장비"]},
    {"name": "도은찬", "age": 27, "gender": "남자", "job": "일러스트레이터", "bio": "의뢰 받아 그림 그려요. 밤에 집중 잘 해요. 낮 데이트가 몸에 맞아요.", "keywords": ["일러스트", "영화", "카페", "게임"], "lifestyle": "밤 활동형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "조심스러운 편", "tags": ["프리랜스", "낮데이트"]},
    {"name": "류지훈", "age": 33, "gender": "여자", "job": "병원 행정", "bio": "서류랑 보험 처리가 주업무예요. 스트레스는 친구들이랑 노래방. 서로 시간 맞출 수 있는 만남이면 좋겠어요.", "keywords": ["음악", "영화", "카페", "산책"], "lifestyle": "균형형", "dating_style": "안정감 있는 관계 선호", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["행정", "노래방"]},
    {"name": "배준서", "age": 30, "gender": "남자", "job": "소믈리에", "bio": "와인 페어링 추천이 일이에요. 일 끝나고는 맥주가 더 땡길 때도 있어요. 맛집 탐방은 여전히 좋아해요.", "keywords": ["와인", "맛집", "여행", "음악"], "lifestyle": "밤 활동형", "dating_style": "표현은 담백한 편", "conversation_style": "가벼운 유머 섞는 편", "tags": ["페어링", "레스토랑"]},
    {"name": "사공민지", "age": 25, "gender": "여자", "job": "댓글 모더레이터", "bio": "온라인 커뮤니티 관리해요. 하루 종일 글 읽다 보면 머리 아파요. 퇴근 후엔 반드시 산책해요.", "keywords": ["산책", "독서", "게임", "영화"], "lifestyle": "집순이/집돌이", "dating_style": "천천히 친해지는 편", "conversation_style": "경청 위주", "tags": ["모더", "커뮤니티"]},
    {"name": "송태리", "age": 29, "gender": "남자", "job": "e커머스 운영", "bio": "할인 행사 기간엔 야근 각이에요. 평소엔 헬스로 멘탈 관리. 주말 브런치 예약 잘해요.", "keywords": ["헬스", "맛집", "카페", "영화"], "lifestyle": "계획형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "질문으로 대화 이어가는 편", "tags": ["행사", "야근"]},
    {"name": "여은호", "age": 32, "gender": "여자", "job": "특수교사", "bio": "아이 한 명 한 명 속도가 달라요. 퇴근 후엔 조용히 쉬고 싶어요. 주말엔 미술 공방 다녀요.", "keywords": ["미술", "독서", "산책", "음악"], "lifestyle": "주말 낮 선호", "dating_style": "배려와 예의 중시", "conversation_style": "차분한 편", "tags": ["특수교육", "공방"]},
    {"name": "오한결", "age": 28, "gender": "남자", "job": "크루즈 승무원", "bio": "한 달에 반은 바다 위에 있어요. 육지에 있을 땐 친구들이랑 맛집이랑 노래방. 연락이 끊기면 선박 중이에요.", "keywords": ["여행", "맛집", "음악", "영화"], "lifestyle": "즉흥형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "에너지는 있는 편", "tags": ["승무원", "출항"]},
    {"name": "유진솔", "age": 27, "gender": "여자", "job": "프로덕트 디자이너", "bio": "앱 화면 설계가 일이에요. 사용자 인터뷰 보러 다니는 게 좋아요. 퇴근 후 필라테스.", "keywords": ["디자인", "필라테스", "카페", "전시"], "lifestyle": "균형형", "dating_style": "공통 취미로 가까워지고 싶음", "conversation_style": "질문으로 대화 이어가는 편", "tags": ["UI", "인터뷰"]},
    {"name": "이도한", "age": 35, "gender": "남자", "job": "신문 기자", "bio": "취재 전화 오면 바로 나가요. 데이트 중에도 전화 오면 미안할 수 있어요. 쉴 땐 책이나 산책.", "keywords": ["독서", "산책", "영화", "음악"], "lifestyle": "즉흥형", "dating_style": "배려와 예의 중시", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["취재", "돌발"]},
    {"name": "임채린", "age": 26, "gender": "여자", "job": "뷰티 컨텐츠 PD", "bio": "짧은 영상 찍고 편집해요. 피부 관리에 진심이에요. 퇴근 후 홈트나 요가.", "keywords": ["요가", "영화", "카페", "맛집"], "lifestyle": "활동형", "dating_style": "상황 보면 리드도 가능", "conversation_style": "리액션 잘하는 편", "tags": ["PD", "뷰티"]},
    {"name": "장도현", "age": 31, "gender": "남자", "job": "창고 관리자", "bio": "물류 팀이랑 소통 많이 해요. 몸 쓰는 일이라 퇴근 후엔 조용히 쉬어요. 주말만큼은 등산이나 드라이브.", "keywords": ["등산", "드라이브", "음악", "맛집"], "lifestyle": "주말 낮 선호", "dating_style": "표현은 담백한 편", "conversation_style": "경청 위주", "tags": ["물류", "창고"]},
    {"name": "전서아", "age": 30, "gender": "여자", "job": "결혼정보업체 코디네이터", "bio": "일은 일이고, 개인적으로는 편하게 만나고 싶어요. 취미는 와인 클래스.", "keywords": ["와인", "영화", "카페", "독서"], "lifestyle": "술자리 적음", "dating_style": "안정감 있는 관계 선호", "conversation_style": "솔직하지만 무례하진 않게", "tags": ["매칭", "클래스"]},
    {"name": "조민재", "age": 29, "gender": "남자", "job": "스포츠 마사지사", "bio": "선수들 몸 풀어주는 일이에요. 본인도 스트레칭 매일 해요. 밤엔 조용히 재즈 들어요.", "keywords": ["운동", "음악", "영화", "맛집"], "lifestyle": "활동형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "상대 말 끝까지 듣는 편", "tags": ["재활", "스트레칭"]},
    {"name": "지은태", "age": 28, "gender": "여자", "job": "로스쿨생", "bio": "스터디에 시험이라 바빠요. 스트레스는 러닝. 카페에서 공부하는 타입.", "keywords": ["러닝", "독서", "커피", "자기계발"], "lifestyle": "계획형", "dating_style": "천천히 친해지는 편", "conversation_style": "조심스러운 편", "tags": ["스터디", "로스쿨"]},
    {"name": "진우석", "age": 33, "gender": "남자", "job": "항공기 조종사", "bio": "스케줄이 한 달 단위로 바뀌어요. 연락이 늦거나 없을 땐 비행 중일 수 있어요. 쉴 땐 여행지 가서 쉬기도 해요.", "keywords": ["여행", "영화", "음악", "맛집"], "lifestyle": "즉흥형", "dating_style": "연락은 적당히, 부담 없이", "conversation_style": "차분한 편", "tags": ["비행", "스케줄"]},
    {"name": "하진아", "age": 27, "gender": "여자", "job": "반려동물 미용", "bio": "강아지들 손질하다 보면 시간 가는 줄 몰라요. 퇴근 후 우리 집 반려견 산책 필수. 사람보다 동물한테 말 잘해요.", "keywords": ["반려동물", "산책", "카페", "영화"], "lifestyle": "활동형", "dating_style": "배려형", "conversation_style": "리액션 잘하는 편", "tags": ["미용", "산책"]},
    {"name": "현도윤", "age": 30, "gender": "남자", "job": "클라우드 엔지니어", "bio": "온콜 있을 때는 새벽에도 일어나요. 평소엔 헬스랑 영화로 균형. 소개팅은 오랜만이라 설렘 반 긴장 반.", "keywords": ["헬스", "영화", "게임", "커피"], "lifestyle": "균형형", "dating_style": "천천히 친해지는 편", "conversation_style": "가벼운 유머 섞는 편", "tags": ["온콜", "인프라"]},
]

def main() -> None:
    rows: list[dict] = []
    if SRC.is_file():
        with SRC.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    for i, obj in enumerate(rows):
        rows[i] = _enrich_row(obj, i)
    start = len(rows)
    for j, p in enumerate(NEW):
        p = dict(p)
        p["id"] = f"p{start + j + 1:04d}"
        rows.append(p)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for obj in rows:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print("existing", start, "new", len(NEW), "total", len(rows), "->", OUT)


if __name__ == "__main__":
    main()
