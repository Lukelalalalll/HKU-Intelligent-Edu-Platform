import { create } from "zustand";
import { api, User } from "./api";

type AuthState = { user: User | null; loading: boolean; setUser: (user: User | null) => void; login: (username: string, password: string) => Promise<User>; logout: () => Promise<void>; bootstrap: () => Promise<void> };
export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  setUser: (user) => set({ user, loading: false }),
  login: async (username, password) => { const { data } = await api.post("/auth/login", { username, password }); set({ user: data.user, loading: false }); return data.user; },
  logout: async () => { await api.post("/auth/logout"); set({ user: null, loading: false }); },
  bootstrap: async () => { try { const { data } = await api.get("/auth/session"); set({ user: data, loading: false }); } catch { set({ user: null, loading: false }); } },
}));

