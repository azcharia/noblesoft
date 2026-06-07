import type { Metadata } from 'next';
import { Montserrat, Open_Sans, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const openSans = Open_Sans({ 
  subsets: ['latin'],
  variable: '--font-open-sans',
  display: 'swap',
});

const montserrat = Montserrat({ 
  subsets: ['latin'],
  variable: '--font-montserrat',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({ 
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'NobleSoft - AI Business Management',
  description: 'B2B SaaS Enterprise AI Operating System for Indonesian UMKM',
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon.ico',
    apple: '/logo.jpg',
  },
};

import { Toaster } from 'sonner';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${openSans.variable} ${montserrat.variable} ${jetbrainsMono.variable}`}>
      <body className={openSans.className}>
        {children}
        <Toaster position="top-center" richColors />
      </body>
    </html>
  );
}
