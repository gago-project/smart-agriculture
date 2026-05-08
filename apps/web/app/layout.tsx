import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '苏农云指挥调度智能',
  description: '苏农云指挥调度智能墒情问答工作台',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
