import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Marx AI",
  description: "马克思主义政治经济学AI知识库",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
