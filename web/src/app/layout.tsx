import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Spectre",
  description: "马克思主义政治经济学智能问答系统",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
