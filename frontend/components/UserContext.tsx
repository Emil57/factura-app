"use client";

import { createContext, useContext } from "react";
import type { Usuario } from "@/lib/api";

export const UserContext = createContext<Usuario | null>(null);
export const useUser = () => useContext(UserContext);

export function hasRole(user: Usuario | null, ...roles: string[]) {
  if (!user) return false;
  return user.role_names.includes("Admin") || roles.some((r) => user.role_names.includes(r));
}
