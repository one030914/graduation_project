/** @type {import("next").NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@prisma/adapter-pg", "pg", "postgres-array"],
};

export default nextConfig;
