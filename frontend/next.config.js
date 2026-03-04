/** @type {import('next').NextConfig} */
const nextConfig = {
  // Next 정적 사이트 export
  output: "export",

  // static export에서 이미지 최적화 서버가 없기 때문에 필요
  images: {
    unoptimized: true,
  },

  // 선택 (URL 뒤에 / 붙이고 싶으면 true)
  // trailingSlash: true,
};

module.exports = nextConfig;
