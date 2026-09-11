"use client";

import { useEffect, useState } from "react";
import type { AuthorRole } from "./api";

export interface Identity {
  name: string;
  role: AuthorRole;
}

const STORAGE_KEY = "contract-review-identity";

export function useIdentity(): [Identity, (id: Identity) => void] {
  const [identity, setIdentityState] = useState<Identity>({
    name: "",
    role: "legal",
  });

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setIdentityState(JSON.parse(raw));
    } catch {
      // ignore
    }
  }, []);

  const setIdentity = (id: Identity) => {
    setIdentityState(id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(id));
  };

  return [identity, setIdentity];
}

export function roleLabel(role: string): string {
  return role === "legal" ? "法务" : "业务";
}

export function roleBadgeClass(role: string): string {
  return role === "legal"
    ? "bg-blue-100 text-blue-700"
    : "bg-emerald-100 text-emerald-700";
}
