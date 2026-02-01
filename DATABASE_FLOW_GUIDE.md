# JoyCoin 데이터베이스 흐름 및 사용 가이드

이 문서는 **데이터베이스가 어떻게 구성되어 있고**, **어떤 순서로 사용하면 되는지** 단계별로 설명합니다.

---

## 1. 데이터베이스 구성 요약

| 항목 | 내용 |
|------|------|
| **DB 종류** | PostgreSQL |
| **연결** | `postgresql+psycopg://app:app@db:5432/app` (Docker 기준, `DB_URL`로 변경 가능) |
| **테이블 생성** | 앱 시작 시 `Base.metadata.create_all()` 한 번 실행 (마이그레이션 없음) |
| **시드** | 슈퍼관리자, 센터 3개, 상품 3개, 환율 1건 자동 생성 |

---

## 2. 테이블(모델) 역할 한눈에 보기

| 테이블 | 역할 | 주요 용도 |
|--------|------|------------|
| **users** | 회원 | 로그인, 추천인·센터 연결, 입금 요청 주체 |
| **centers** | 지역 센터 | 회원가입 시 선택(선택), 목록 노출용 |
| **referrals** | 추천 관계 | A가 B를 추천했을 때 1건 기록 |
| **products** | JOY 상품 | 구매 페이지용 상품 목록 (가격, 할인 등) |
| **purchases** | 구매 내역 | 상품 구매 기록 (현재 API에서는 입금과 미연동) |
| **deposit_requests** | USDT 입금 요청 | 사용자가 입금 요청 → 관리자 승인/거절 |
| **points** | 포인트 내역 | 추천 보너스 등 포인트 적립/사용 기록 |
| **exchange_rates** | 환율 | JOY↔KRW, USDT↔KRW (참고용) |

---

## 3. 앱 기동 시 흐름 (무슨 일이 일어나는지)

```
[백엔드 서버 시작]
       │
       ▼
① Base.metadata.create_all(engine)
   → users, centers, referrals, products, purchases,
     deposit_requests, points, exchange_rates 테이블 생성
       │
       ▼
② seed_super_admin()
   → SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD 있으면
     해당 계정 생성(없을 때만), role=admin
       │
       ▼
③ seed_initial_data()
   → 센터 3개(서울/부산/대구)
   → 상품 3개(JOY 1000/2000/5000)
   → 환율 1건(joy_to_krw=13, usdt_to_krw=1300)
       │
       ▼
[API 서버 준비 완료]
```

- **테이블이 없으면** 이때 생성되고, **이미 있으면** 그대로 사용합니다.
- 슈퍼관리자는 **최초 1회만** 생성되며, 이미 있으면 role만 `admin`으로 맞춥니다.

---

## 4. 사용자 관점: 어떻게 사용해야 하는지 (전체 흐름)

### 4.1 흐름 개요

```
[회원가입] → [로그인] → [입금 요청] → [내 입금 조회]
     │            │            │              │
   /auth/signup  /auth/login  /deposits/request  /deposits/my
```

- **로그인 전**: 센터·상품 목록만 조회 가능 (`/centers`, `/products`).
- **로그인 후**: JWT를 들고 `/deposits/request`, `/deposits/my` 사용.

---

### 4.2 1단계: 회원가입 (POST /auth/signup)

**언제**: 가입 화면에서 이메일, 비밀번호, 이름(필수)과 선택 항목 입력 후 요청.

**요청 예시**

```json
{
  "email": "user@example.com",
  "password": "mypassword123!",
  "username": "홍길동",
  "referral_code": "JOY7K2M9",
  "center_id": 1
}
```

| 필드 | 필수 | 설명 |
|------|------|------|
| email | ✅ | 이메일 (중복 불가) |
| password | ✅ | 12자 이상 |
| username | ✅ | 2~100자 |
| referral_code | ❌ | 추천인 코드(있으면 추천인에게 100포인트 지급, Referral·Point 기록) |
| center_id | ❌ | 센터 ID (GET /centers로 확인) |

**응답 예시**

```json
{
  "message": "회원가입 성공",
  "user_id": 5,
  "referral_code": "JOYABC12"
}
```

- **JWT는 주지 않습니다.** 가입 직후 로그인하려면 `POST /auth/login` 호출.
- `referral_code`는 **본인 추천인 코드**이므로, 나를 추천한 사람에게 알려줄 때 사용합니다.

**백엔드에서 하는 일**

1. 이메일 중복 검사  
2. `referral_code` 있으면 해당 유저 조회 → 없으면 400  
3. `center_id` 있으면 센터 존재 여부 확인 → 없으면 400  
4. User 생성, `referred_by` / `center_id` 설정, `is_email_verified=True` (이메일 인증 없음)  
5. 추천인 있으면 Referral 1건 + 추천인에게 Point 100 지급  

---

### 4.3 2단계: 로그인 (POST /auth/login)

**언제**: 회원가입 후, 로그인 화면에서 이메일·비밀번호 입력 후 요청.

**요청 예시**

```json
{
  "email": "user@example.com",
  "password": "mypassword123!"
}
```

**응답 예시**

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

- 이후 **모든 인증 필요 API**에는 `Authorization: Bearer <access>` 헤더로 이 값을 넣습니다.
- JWT 만료 시간은 설정값(기본 20분)에 따릅니다.

---

### 4.4 3단계: 입금 요청 (POST /deposits/request) — 로그인 필요

**언제**: USDT를 입금할 예정일 때. 네트워크(체인)와 금액만 보내면, 입금할 주소와 예상 금액을 받습니다.

**요청 예시**

```
Header: Authorization: Bearer <위에서 받은 access>
Body:
{
  "chain": "TRC20",
  "amount_usdt": 50.5
}
```

| 필드 | 설명 |
|------|------|
| chain | `TRC20` | `ERC20` | `BSC` | `Polygon` 중 하나 |
| amount_usdt | 입금 예정 USDT 금액 |

**응답 예시**

```json
{
  "id": 3,
  "user_id": 5,
  "purchase_id": null,
  "chain": "TRC20",
  "assigned_address": "TAdmin...",
  "expected_amount": 50.5,
  "actual_amount": null,
  "status": "pending",
  "admin_id": null,
  "admin_notes": null,
  "approved_at": null,
  "created_at": "2025-01-29T12:00:00"
}
```

- `assigned_address`: **여기로 USDT를 입금**하면 됩니다 (환경변수 `USDT_ADMIN_ADDRESS` 값).
- `status`: `pending` → 관리자 승인 시 `approved`, 거절 시 `rejected`.
- 현재 구현에서는 **purchase_id는 사용하지 않습니다** (선택 연동용).

**주의**: `USDT_ADMIN_ADDRESS`가 설정되지 않으면 입금 요청 시 에러가 납니다.

---

### 4.5 4단계: 내 입금 목록 조회 (GET /deposits/my) — 로그인 필요

**언제**: 마이페이지·입금 내역 화면에서 “내가 요청한 입금” 목록을 볼 때.

**요청 예시**

```
Header: Authorization: Bearer <access>
GET /deposits/my
```

**응답 예시**

```json
{
  "items": [
    {
      "id": 3,
      "user_id": 5,
      "chain": "TRC20",
      "assigned_address": "TAdmin...",
      "expected_amount": 50.5,
      "status": "approved",
      "actual_amount": 50.5,
      "created_at": "2025-01-29T12:00:00",
      ...
    },
    ...
  ]
}
```

- **status**로 UI 분기하면 됩니다.
  - `pending`: 대기 중
  - `approved`: 승인됨 (필요하면 `actual_amount` 표시)
  - `rejected`: 거절됨 (`admin_notes` 있으면 사유 표시 가능)

---

## 5. 관리자 관점: 입금 승인/거절 흐름

### 5.1 전제

- 관리자는 **role=admin**인 유저만 가능 (슈퍼관리자 또는 promote된 계정).
- 모든 `/admin/*` API는 **JWT + admin 권한**이 있어야 합니다.

### 5.2 입금 목록 조회 (GET /admin/deposits)

**요청 예시**

```
Header: Authorization: Bearer <관리자_JWT>
GET /admin/deposits
GET /admin/deposits?status=pending
GET /admin/deposits?status=approved
GET /admin/deposits?status=rejected
```

- `status` 생략: 전체 (최신 200건).
- `status=pending`: 대기 중만 보기.

**응답**: `DepositRequestOut` 배열 (id, user_id, chain, assigned_address, expected_amount, status, admin_notes 등).

---

### 5.3 입금 승인 (POST /admin/deposits/{id}/approve)

**요청 예시**

```
Header: Authorization: Bearer <관리자_JWT>
POST /admin/deposits/3/approve
Body:
{
  "actual_amount": 50.5,
  "admin_notes": "입금 확인함"
}
```

- `actual_amount`: 생략 시 `expected_amount`로 저장.
- `admin_notes`: 선택. 승인 메모.

**동작**: 해당 `deposit_request`의 `status=approved`, `actual_amount`, `admin_id`, `approved_at` 갱신.

---

### 5.4 입금 거절 (POST /admin/deposits/{id}/reject)

**요청 예시**

```
Header: Authorization: Bearer <관리자_JWT>
POST /admin/deposits/3/reject
Body:
{
  "admin_notes": "금액 불일치"
}
```

**동작**: 해당 건 `status=rejected`, `admin_id`, `admin_notes` 갱신. 이미 approved면 400.

---

## 6. 인증 불필요 API (로그인 없이 사용)

| 메서드 | 경로 | 용도 |
|--------|------|------|
| GET | /centers | 센터 목록 (회원가입 시 선택지) |
| GET | /products | 상품 목록 (구매 페이지용) |
| POST | /auth/signup | 회원가입 |
| POST | /auth/login | 로그인 |

---

## 7. 환경변수 (데이터베이스·흐름 관련)

| 변수 | 필수 | 설명 |
|------|------|------|
| DB_URL | ✅ | PostgreSQL 연결 문자열 |
| JWT_SECRET | ✅ | JWT 서명용 |
| JWT_EXPIRE_MIN | ❌ | JWT 만료(분), 기본 20 |
| USDT_ADMIN_ADDRESS | 입금 사용 시 | 입금 요청 시 할당되는 주소 (없으면 입금 요청 실패) |
| SUPER_ADMIN_EMAIL | ❌ | 슈퍼관리자 이메일 (시드용) |
| SUPER_ADMIN_PASSWORD | ❌ | 슈퍼관리자 비밀번호 (시드용) |
| CORS_ORIGINS | ❌ | 프론트 도메인, 기본 localhost:3000 |

---

## 8. 데이터 흐름 요약 (테이블 기준)

```
[회원가입]
  → users 1건 (is_email_verified=True, 이메일 인증 없음)
  → (선택) referrals 1건 + points 1건(추천인)

[로그인]
  → users 조회 + JWT 발급 (DB 쓰기 없음)

[입금 요청]
  → deposit_requests 1건 (user_id, chain, expected_amount, assigned_address, status=pending)

[관리자 승인/거절]
  → deposit_requests 갱신 (status, actual_amount, admin_id, admin_notes, approved_at)
```

- **purchases**는 현재 “상품 구매” 기록용 테이블이며, 입금 요청 API와는 **연동되어 있지 않습니다**.  
  나중에 “상품 선택 → Purchase 생성 → 입금 요청 시 purchase_id 연결” 플로우를 넣을 수 있습니다.

---

## 9. 사용 시나리오 예시 (한 번에 따라 하기)

1. **백엔드 실행**  
   - Docker로 DB·백엔드 기동 → 테이블·시드 자동 생성.
2. **센터/상품 확인**  
   - `GET /centers`, `GET /products` 로 목록 확인.
3. **회원가입**  
   - `POST /auth/signup` (username 필수, referral_code·center_id 선택).
4. **로그인**  
   - `POST /auth/login` → `access` 토큰 저장.
5. **입금 요청**  
   - `POST /deposits/request` (Authorization: Bearer + chain, amount_usdt).
6. **내 입금 보기**  
   - `GET /deposits/my` 로 status(pending/approved/rejected) 확인.
7. **관리자**  
   - 관리자 계정으로 로그인 → `GET /admin/deposits`, `POST .../approve` 또는 `.../reject`.

이 순서대로 사용하면, 현재 데이터베이스와 API 흐름을 그대로 따를 수 있습니다.
