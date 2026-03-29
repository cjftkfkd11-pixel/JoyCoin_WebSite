"use client";
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SectorLoginRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/admin/login'); }, []);
  return null;
}
