import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AnimatedBackground } from "@/components/AnimatedBackground";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "YouTube 留言多模組分析平台",
  description: "綜合、熱門主題、情緒風向、批評回饋與影片內容脈絡分析之視覺化工具",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="zh-TW"
      className={[geistSans.variable, geistMono.variable, "h-full antialiased"].join(" ")}
    >
      <body className="min-h-full bg-[#070b18] text-white" suppressHydrationWarning>
        <AnimatedBackground />
        <div className="relative z-10 flex min-h-full flex-col">{children}</div>
      </body>
    </html>
  );
}
