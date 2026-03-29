"use client";
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SectorDashboardRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/admin/dashboard'); }, []);
  return null;
}
