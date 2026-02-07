import type { Metadata } from "next";
import "./globals.css";
import { LanguageProvider } from "@/lib/LanguageContext";
import { AuthProvider } from "@/lib/AuthContext";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "JOYCOIN",
  description: "JoyCoin Website",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-screen flex flex-col relative overflow-hidden">
        <LanguageProvider>
          <AuthProvider>
            <div className="liquid-bg">
              <div className="liquid-drop"></div>
            </div>

            <Header />

            <main className="flex-1 flex flex-col relative z-10 pt-20">
              {children}
            </main>

            <Footer />
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
