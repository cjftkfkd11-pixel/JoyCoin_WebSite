# 데이터베이스(Claude Code) 작업 진행 상황 정리

**원칙: 백엔드 우선. 프론트는 백엔드 스펙에 맞춰 나중에 연동.**

---

## ✅ 백엔드 완료된 부분

### 1. DB 모델 (테이블)
| 모델 | 파일 | 비고 |
|------|------|------|
| User | `models/user.py` | referral_code, referred_by, center_id, 관계 정의 |
| Center | `models/center.py` | name, region, manager_name, is_active |
| Referral | `models/referral.py` | referrer_id, referred_id, reward_points |
| Product | `models/product.py` | joy_amount, price_usdt, price_krw, discount_rate, sort_order |
| Purchase | `models/purchase.py` | user_id, product_id, total_joy, total_usdt, status |
| DepositRequest | `models/deposit_request.py` | purchase_id(선택), status: pending/approved/rejected |
| Point | `models/point.py` | user_id, amount, type (referral_bonus 등) |
| ExchangeRate | `models/exchange_rate.py` | joy_to_krw, usdt_to_krw, is_active |

### 2. API 라우터
| 라우터 | 파일 | 비고 |
|--------|------|------|
| /centers | `api/centers.py` | GET 목록 (is_active=True) |
| /products | `api/products.py` | GET 목록 (가격, 할인율, sort_order) |
| /auth | `api/auth.py` | signup(추천인·센터·포인트), login (이메일 인증 없음) |
| /deposits | `api/deposits.py` | POST /request, GET /my |
| /admin/deposits | `api/admin_deposits.py` | GET 목록, POST /{id}/approve, /{id}/reject |
| /admin/users | `api/admin_users.py` | GET 목록, POST /{id}/promote |

### 3. 시드 데이터 (main.py)
- 슈퍼관리자: `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD`
- 센터 3개: 서울, 부산, 대구
- 상품 3개: JOY 1000/2000/5000 패키지
- 환율 1건: joy_to_krw=13, usdt_to_krw=1300

---

## 백엔드 API 스펙 (프론트 연동 시 참고)

프론트 작업 시 **이 스펙에 맞춰** 연동하면 됨.

### POST /auth/signup
- **Body**: `{ "email", "password", "username" (필수), "referral_code" (선택), "center_id" (선택) }`
- **응답**: `{ "message", "user_id", "referral_code" }` — JWT 없음. 로그인 화면 이동 또는 별도 POST /auth/login 호출 필요.

### POST /auth/login
- **Body**: `{ "email", "password" }`
- **응답**: `{ "access": "JWT..." }`

### GET /centers
- **인증**: 없음
- **응답**: `[{ "id", "name", "region" }, ...]`

### GET /products
- **인증**: 없음
- **응답**: `[{ "id", "name", "joy_amount", "price_usdt", "price_krw", "discount_rate", "description" }, ...]`

### POST /deposits/request
- **Header**: `Authorization: Bearer <access>`
- **Body**: `{ "chain": "TRON"|"ETH", "amount_usdt": number }`
- **응답**: `{ "id", "chain", "assigned_address", "expected_amount", "reference_code", "status" }`

### GET /deposits/my
- **Header**: `Authorization: Bearer <access>`
- **응답**: `{ "items": [ { "id", "chain", "assigned_address", "expected_amount", "status", "created_at", ... } ] }`
- **status 값**: `pending` | `approved` | `rejected` (프론트에서 이 세 가지로 표시하면 됨)

### Admin
- **GET /admin/deposits**: Query `?status=pending|approved|rejected`
- **POST /admin/deposits/{id}/approve**: Body `{ "actual_amount?", "admin_notes?" }`
- **POST /admin/deposits/{id}/reject**: Body `{ "admin_notes?" }`
- **GET /admin/users**, **POST /admin/users/{id}/promote**: 관리자 전용

---

## 백엔드 쪽에서 나중에 할 수 있는 작업 (선택)

- **Purchase–DepositRequest 연동**: 상품 선택 → Purchase 생성 → 입금 요청 시 `purchase_id` 넣는 플로우 (필요 시 백엔드에 구매 생성 API 추가).
- **회원가입 후 JWT 반환**: signup 응답에 `access` 넣어 주면 프론트에서 회원가입 직후 로그인 상태로 처리하기 쉬움.

---

## 요약

| 구분 | 상태 |
|------|------|
| DB 모델·테이블 | ✅ 완료 |
| 백엔드 API (centers, products, auth, deposits, admin) | ✅ 완료 |
| 시드 데이터 | ✅ 완료 |
| 프론트 | 나중에 위 API 스펙에 맞춰 연동 |
