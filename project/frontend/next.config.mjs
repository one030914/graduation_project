/** @type {import("next").NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@prisma/adapter-pg", "pg", "postgres-array"],
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        ...config.watchOptions,
        aggregateTimeout: 300,
        ignored: /node_modules/,
        poll: 1000,
      };
    }

    return config;
  },
};

export default nextConfig;
