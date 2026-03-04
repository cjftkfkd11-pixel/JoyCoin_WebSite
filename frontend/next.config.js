/** @type {import('next').NextConfig} */
const nextConfig = {
  // 정적 export 결과물이 out/ 폴더로 생성되게 함 (Next 13+)
  output: "export",

  // 정적 export에서는 next/image 최적화 서버가 없어서 이 옵션이 거의 필수
  images: { unoptimized: true },

  // (선택) trailingSlash가 필요하면 true로
  // trailingSlash: true,
};

module.exports = nextConfig;
