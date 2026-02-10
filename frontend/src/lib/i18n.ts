// frontend/src/lib/i18n.ts

export type Locale = "en" | "ko";

export const translations = {
  en: {
    // Common
    home: "Home",
    login: "Login",
    logout: "Logout",
    signup: "Sign Up",
    myPage: "My Page",
    buy: "Buy",
    admin: "Admin",
    loading: "Loading...",
    confirm: "Confirm",
    cancel: "Cancel",
    save: "Save",
    close: "Close",
    copy: "Copy",
    copied: "Copied!",

    // Auth
    email: "Email",
    password: "Password",
    confirmPassword: "Confirm Password",
    username: "Username",
    center: "Center",
    selectCenter: "Select Center",
    referralCode: "Referral Code",
    optional: "Optional",
    loginSuccess: "Login successful",
    loginFailed: "Invalid email or password",
    signupSuccess: "Registration successful",
    passwordMinLength: "Password must be at least 12 characters",
    passwordMismatch: "Passwords do not match",
    usernameRequired: "Username is required",
    alreadyHaveAccount: "Already have an account?",
    dontHaveAccount: "Don't have an account?",

    // Buy
    buyJoycoin: "Buy JOYCOIN",
    fixedRate: "Fixed Rate",
    selectAmount: "Select Amount",
    addAmount: "Add Amount",
    orderSummary: "Order Summary",
    quantity: "Quantity",
    pricePerJoy: "Price per JOY",
    total: "Total",
    proceedPayment: "Proceed to Payment",
    senderName: "Sender Name (Wallet Name)",
    senderNamePlaceholder: "Enter the name on your wallet",
    senderNameHelp: "Enter the name that will appear when you send USDT",

    // Deposit
    depositPending: "Deposit Pending",
    depositApproved: "Deposit Approved",
    depositRejected: "Deposit Rejected",
    depositHistory: "Deposit History",
    noDeposits: "No deposit history",
    totalDeposits: "Total Deposits",
    totalAmount: "Total Amount",
    completedTx: "Completed",
    pending: "Pending",
    approved: "Approved",
    rejected: "Rejected",
    chain: "Chain",
    address: "Address",
    amount: "Amount",
    requestTime: "Request Time",
    status: "Status",

    // Payment Modal
    paymentConfirm: "Payment Confirmation",
    sendUsdtTo: "Send USDT to this address",
    requestId: "Request ID",
    confirmed: "I have sent the payment",
    paymentNote: "After sending, the admin will verify and approve your deposit.",

    // My Page
    myInfo: "My Info",
    myReferralCode: "My Referral Code",
    totalJoy: "Total JOY",
    totalPoints: "Total Points",
    referralRewardRemaining: "Referral Rewards Left",
    referralRewardDesc: "10% bonus points on your next purchase",
    quickMenu: "Quick Menu",

    // Notifications
    notifications: "Notifications",
    noNotifications: "No notifications",
    markAllRead: "Mark all as read",

    // Admin
    adminPanel: "Admin Panel",
    depositManagement: "Deposit Management",
    approve: "Approve",
    reject: "Reject",
    user: "User",
    adminNotes: "Admin Notes",

    // Footer
    footer: "© 2024 JOYCOIN GLOBAL FOUNDATION • SECURED BY BLOCKCHAIN",
  },

  ko: {
    // Common
    home: "홈",
    login: "로그인",
    logout: "로그아웃",
    signup: "회원가입",
    myPage: "마이페이지",
    buy: "구매하기",
    admin: "관리자",
    loading: "로딩 중...",
    confirm: "확인",
    cancel: "취소",
    save: "저장",
    close: "닫기",
    copy: "복사",
    copied: "복사됨!",

    // Auth
    email: "이메일",
    password: "비밀번호",
    confirmPassword: "비밀번호 확인",
    username: "이름 / 닉네임",
    center: "센터",
    selectCenter: "센터 선택",
    referralCode: "추천인 코드",
    optional: "선택",
    loginSuccess: "로그인 성공",
    loginFailed: "이메일 또는 비밀번호가 올바르지 않습니다",
    signupSuccess: "회원가입이 완료되었습니다",
    passwordMinLength: "비밀번호는 12자 이상이어야 합니다",
    passwordMismatch: "비밀번호가 일치하지 않습니다",
    usernameRequired: "이름을 입력해 주세요",
    alreadyHaveAccount: "이미 계정이 있으신가요?",
    dontHaveAccount: "계정이 없으신가요?",

    // Buy
    buyJoycoin: "조이코인 구매",
    fixedRate: "고정 환율",
    selectAmount: "시작 수량 선택",
    addAmount: "수량 추가",
    orderSummary: "주문 요약",
    quantity: "수량",
    pricePerJoy: "JOY당 가격",
    total: "총액",
    proceedPayment: "결제 진행하기",
    senderName: "입금자명 (지갑 실명)",
    senderNamePlaceholder: "지갑에 등록된 이름을 입력하세요",
    senderNameHelp: "USDT 전송 시 표시되는 이름을 입력하세요",

    // Deposit
    depositPending: "입금 대기중",
    depositApproved: "입금 완료",
    depositRejected: "입금 거부됨",
    depositHistory: "입금 내역",
    noDeposits: "입금 내역이 없습니다",
    totalDeposits: "총 입금 건수",
    totalAmount: "총 입금액",
    completedTx: "완료된 거래",
    pending: "대기중",
    approved: "입금완료",
    rejected: "거부됨",
    chain: "체인",
    address: "주소",
    amount: "금액",
    requestTime: "요청시간",
    status: "상태",

    // Payment Modal
    paymentConfirm: "입금 확인",
    sendUsdtTo: "USDT를 이 주소로 전송하세요",
    requestId: "요청번호",
    confirmed: "입금했습니다",
    paymentNote: "관리자가 입금을 확인하면 상태가 '입금완료'로 변경됩니다.",

    // My Page
    myInfo: "내 정보",
    myReferralCode: "내 추천인 코드",
    totalJoy: "보유 JOY",
    totalPoints: "보유 포인트",
    referralRewardRemaining: "남은 추천 보상",
    referralRewardDesc: "다음 구매 시 결제금액의 10% 포인트 적립",
    quickMenu: "빠른 메뉴",

    // Notifications
    notifications: "알림",
    noNotifications: "알림이 없습니다",
    markAllRead: "모두 읽음",

    // Admin
    adminPanel: "관리자 패널",
    depositManagement: "입금 관리",
    approve: "승인",
    reject: "거부",
    user: "사용자",
    adminNotes: "관리자 메모",

    // Footer
    footer: "© 2024 JOYCOIN GLOBAL FOUNDATION • SECURED BY BLOCKCHAIN",
  },
};

export type TranslationKey = keyof typeof translations.en;

export function getTranslation(locale: Locale, key: TranslationKey): string {
  return translations[locale][key] || translations.en[key] || key;
}
