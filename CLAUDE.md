# JoyCoin Project - Development Notes

## 최근 작업 (2026-02-04)

### 페이지 구조 정리 완료
1. **통합 및 개선**
   - `/mypage` 페이지를 완전한 마이페이지로 개선
   - 유저 정보, 잔액, 입금 내역 모두 통합
   - 로그아웃 기능 추가 (API 연동)

2. **중복 페이지 제거**
   - `/deposits` 폴더 삭제 (mypage와 중복)
   - `/purchase` 폴더 삭제 (buy로 통합)

3. **라우팅 일관성 확보**
   - 마이페이지: `/mypage` (통일)
   - 구매 페이지: `/buy` (통일)

4. **인증 방식 통일**
   - `admin/dashboard` 인증을 HttpOnly 쿠키로 변경
   - 모든 페이지에서 `credentials: 'include'` 사용
   - `getCookie`, `deleteCookie` 함수 제거 (불필요)

### 현재 페이지 구조
```
frontend/src/app/
  ├── auth/
  │   ├── login/        - 사용자 로그인
  │   └── signup/       - 사용자 회원가입
  ├── admin/
  │   ├── login/        - 관리자 로그인
  │   ├── signup/       - 관리자 회원가입
  │   ├── dashboard/    - 관리자 대시보드 (실제 API 연동)
  │   └── referrers/    - 추천인 관리
  ├── buy/              - 패키지 구매 (QR 코드 + 입금 주소 표시)
  ├── mypage/           - 마이페이지 (유저 정보 + 잔액 + 입금 내역)
  └── page.tsx          - 메인 페이지
```

---

### 2차 작업: 핵심 기능 구현 완료

1. **관리자 대시보드 실제 API 연동**
   - `GET /admin/deposits` - 입금 요청 목록 조회
   - `POST /admin/deposits/{id}/approve` - 승인 (유저 잔액 자동 충전)
   - `POST /admin/deposits/{id}/reject` - 거절
   - 실시간 통계 (대기중/승인완료/거절됨 카운트)
   - 이메일 마스킹 (개인정보 보호)

2. **QR 코드 및 입금 주소 표시**
   - 입금 요청 성공 시 모달로 QR 코드 표시
   - `assigned_address` 표시 (복사 가능)
   - 입금 금액 및 네트워크 정보 표시
   - 주의사항 안내

3. **텔레그램 알림 시스템**
   - `backend/app/services/telegram.py` 추가
   - 입금 요청 시 관리자에게 알림
   - 승인 완료 시 알림
   - 환경변수 설정: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - 알림 실패 시에도 서비스는 정상 작동 (비동기)

### 환경변수 설정 필요

```env
# backend/.env
USDT_ADMIN_ADDRESS=입금받을주소
TELEGRAM_BOT_TOKEN=봇토큰
TELEGRAM_CHAT_ID=채팅ID
```

---

### 3차 작업: 프론트엔드 환경 설정 및 보안 패치

1. **Node.js 환경 구성**
   - Windows 환경에서 Node.js 설치 필요
   - PowerShell 실행 정책 문제 → CMD 사용 권장
   - `npm install`로 의존성 설치 완료

2. **TypeScript 환경 설정**
   - `@types/node` 패키지 설치로 TypeScript 오류 해결
   - `node_modules` 생성으로 타입 정의 파일 인식

3. **Next.js 보안 패치**
   - Next.js 14.2.5 → 14.2.35로 업그레이드
   - Critical 보안 취약점 해결:
     - Cache Poisoning
     - DoS (Denial of Service)
     - SSRF (Server-Side Request Forgery)
     - Authorization Bypass
   - 커밋: `e6d449d` - "fix: Next.js 보안 패치"

4. **트러블슈팅 기록**
   - Windows에서 npm 명령어 인식 안 됨 → Node.js 설치 필요
   - PowerShell 실행 정책 오류 → CMD 터미널 사용
   - ESLint 관련 취약점 4개 남음 (개발용 도구, 프로덕션 무관)

---

## API Schemas

### Backend Centers API Response
```json
[
  {"id": 1, "name": "센터명", "region": "지역명"}
]
```

### Backend Auth Signup Request
```json
{
  "email": "string (required)",
  "password": "string (required, min 12 chars)",
  "username": "string (required)",
  "center_id": "number (optional)",
  "referral_code": "string (optional)"
}
```

## Common Mistakes to Avoid

### Frontend
1. **TypeScript 타입 불일치**: API 응답과 프론트엔드 타입을 항상 일치시킬 것
   - Centers: `{id: number; name: string; region: string}`
   - 잘못된 예: `{id: number, name: string}` (region 누락)
   - **수정됨 (2026-02-03)**: signup/page.tsx에서 centers 타입에 region 추가

2. **API 필드명 불일치**: 백엔드 스키마와 프론트엔드 요청 필드명 일치 필수
   - 올바른 예: `email`, `password`, `username`, `center_id`, `referral_code`
   - 잘못된 예: `username`에 이메일 값 전송
   - **수정됨 (2026-02-03)**: admin/signup/page.tsx에서 email/username 필드 수정

3. **HttpOnly 쿠키 사용시**: `credentials: 'include'` 필수
   - **수정됨 (2026-02-04)**: admin/dashboard에서 getCookie 제거, credentials: 'include'로 통일

4. **페이지 중복 금지**: 비슷한 기능의 페이지는 하나로 통합
   - **수정됨 (2026-02-04)**: /deposits와 /mypage 통합, /purchase와 /buy 통합

### Backend
1. **SQLAlchemy 관계**: foreign_keys 명시 필요한 경우 양쪽 모두 설정
2. **Enum 검증**: role, status 등에 validator 사용

### Docker (Windows)
1. **PostgreSQL 볼륨**: Windows에서 바인드 마운트 대신 네임드 볼륨 사용
   - 잘못된 예: `./docker-data/postgres:/var/lib/postgresql/data`
   - 올바른 예: `postgres_data:/var/lib/postgresql/data` + volumes 섹션 정의

## File Structure
```
backend/
  app/
    api/auth.py       - 인증 API (signup, login, me)
    schemas/auth.py   - Pydantic 스키마
    models/user.py    - User 모델
    core/enums.py     - Enum 정의 (UserRole, DepositStatus 등)

frontend/
  src/app/
    auth/signup/      - 회원가입 페이지
    auth/login/       - 로그인 페이지
    admin/            - 관리자 페이지
```
