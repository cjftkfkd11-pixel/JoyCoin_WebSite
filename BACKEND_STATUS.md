# 백엔드 진행 상황 (JoyCoin USDT 구매 사이트 기준)

**프로젝트 목표**: 사용자가 JoyCoin을 USDT로 구매할 수 있는 사이트  
**필요 기능**: 회원가입, 로그인, 구매하기, 마이페이지, 추천인, 포인트

---

## ✅ 백엔드에서 이미 된 것

| 기능 | API/동작 | 상태 |
|------|----------|------|
| **회원가입** | `POST /auth/signup` (username, referral_code, center_id) | ✅ 완료 |
| **로그인** | `POST /auth/login` → JWT | ✅ 완료 |
| **센터 목록** | `GET /centers` | ✅ 완료 |
| **상품 목록** | `GET /products` (JOY 패키지, 가격, 할인) | ✅ 완료 |
| **입금 요청** | `POST /deposits/request` (chain, amount_usdt) | ✅ 완료 |
| **내 입금 내역** | `GET /deposits/my` (pending/approved/rejected) | ✅ 완료 |
| **관리자 입금 목록** | `GET /admin/deposits` | ✅ 완료 |
| **관리자 입금 승인/거절** | `POST /admin/deposits/{id}/approve`, `/reject` | ✅ 완료 |
| **관리자 유저 목록/승급** | `GET /admin/users`, `POST /admin/users/{id}/promote` | ✅ 완료 |
| **추천인** | 가입 시 `referral_code` 입력 → Referral 기록 + 추천인에게 Point 100 지급 | ✅ 완료 |
| **포인트 (기록)** | Point 테이블에 추천 보너스 적립 (referral_bonus) | ✅ DB/로직 완료 |

---

## ❌ 백엔드에서 아직 안 된 것 (남은 작업)

### 1. 구매(Purchase) 흐름 연동

- **현재**: 입금 요청은 "금액 + 체인"만 보냄. **어떤 상품(JOY 패키지)을 사는지** 연결 안 됨.
- **필요**:
  - **상품 선택 → 구매(Purchase) 생성**  
    - 예: `POST /purchases` (user_id, product_id, quantity) → Purchase 생성 (status=pending), 응답에 expected_amount(USDT) 등 반환.
  - **입금 요청 시 purchase_id 연결**  
    - 예: `POST /deposits/request` Body에 `purchase_id` 추가 → DepositRequest가 특정 Purchase와 연결.
- **효과**: "이 입금이 어떤 JOY 구매에 대한 것인지" 관리자/시스템이 알 수 있음.

### 2. 입금 승인 시 “구매 완료” 처리

- **현재**: 관리자가 입금 승인하면 `DepositRequest.status = approved` 만 바뀜. **Purchase 완료 처리나 JOY “지급” 로직 없음.**
- **필요**:
  - 입금 승인 시 해당 `DepositRequest`에 `purchase_id`가 있으면  
    → 해당 **Purchase.status = completed**, `completed_at` 설정 (그리고 필요하면 “JOY 지급” 개념을 같은 시점에 처리).
- **효과**: “입금 확인됨 = 해당 구매 완료”로 일관되게 동작.

### 3. 마이페이지용 API

| API | 설명 | 상태 |
|-----|------|------|
| **내 구매 내역** | `GET /purchases/my` (또는 `/me/purchases`) | ❌ 없음 |
| **내 포인트 잔액/내역** | `GET /points/me` 또는 `GET /users/me/points` (잔액 + 내역) | ❌ 없음 |

- **내 구매 내역**: Purchase 테이블에서 `user_id = 현재 유저` 목록 반환 (상품명, JOY 수량, USDT, status, created_at 등).
- **내 포인트**: Point 테이블에서 `user_id = 현재 유저`로 합산 잔액 + 최근 내역 리스트 (type, amount, description, created_at).

### 4. (선택) 회원가입 후 JWT 바로 발급

- **현재**: signup 성공 시 `message`, `user_id`, `referral_code`만 반환. JWT 없음 → 프론트에서 로그인 화면으로 보냄.
- **선택**: signup 응답에 `access` (JWT) 포함하면, 프론트에서 “가입 즉시 로그인 상태” 처리 가능.

---

## 요약: 백엔드는 어디까지 된 거야?

| 구분 | 상태 |
|------|------|
| **회원가입 / 로그인** | ✅ 완료 |
| **구매하기 (상품 보기 + 입금 요청)** | ✅ “입금 요청”까지 완료. **상품(Product)과 구매(Purchase) 연결은 미완** |
| **마이페이지** | ⚠️ “내 입금 내역”만 가능. **내 구매 내역, 내 포인트** API 없음 |
| **추천인** | ✅ 가입 시 추천인 코드 → Referral + 포인트 100 지급 완료 |
| **포인트** | ✅ 추천 보너스 적립 로직/DB 완료. **유저가 “내 포인트” 조회 API는 없음** |
| **관리자** | ✅ 입금 목록/승인/거절, 유저 목록/승급 완료 |

---

## 남은 백엔드 작업 우선순위 제안

1. **마이페이지용 API**  
   - `GET /purchases/my` (내 구매 내역)  
   - `GET /points/me` 또는 `GET /users/me/points` (포인트 잔액 + 내역)
2. **구매(Purchase) 연동**  
   - `POST /purchases` (상품 선택 시 구매 생성)  
   - `POST /deposits/request`에 `purchase_id` (선택) 추가  
   - 입금 승인 시 `purchase_id` 있으면 해당 Purchase를 completed 처리

이렇게 하면 “JoyCoin을 USDT로 구매” + “마이페이지(구매/포인트)” + “추천인/포인트”까지 백엔드가 한 번에 맞춰진다.
