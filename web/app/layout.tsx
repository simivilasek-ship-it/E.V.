import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'JARVIS — AI Asistent',
  description: 'Lokální AI asistent — hlasové a textové ovládání PC',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="cs" data-theme="dark" className="h-full">
      <body className="h-full overflow-hidden">{children}</body>
    </html>
  )
}
