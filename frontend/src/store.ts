import { create } from "zustand";
import { api, profileApi, setDevAccessToken, User } from "./api";

type AuthState = { user: User | null; loading: boolean; setUser: (user: User | null) => void; login: (username: string, password: string) => Promise<User>; logout: () => Promise<void>; bootstrap: () => Promise<void>; refreshProfile: () => Promise<User>; };
export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  setUser: (user) => set({ user, loading: false }),
  login: async (username, password) => { const { data } = await api.post("/auth/login", { username, password }); setDevAccessToken(data.access_token || null); set({ user: data.user, loading: false }); return data.user; },
  logout: async () => { try { await api.post("/auth/logout"); } finally { setDevAccessToken(null); set({ user: null, loading: false }); } },
  bootstrap: async () => { try { const { data } = await api.get("/auth/session"); set({ user: data, loading: false }); } catch { set({ user: null, loading: false }); } },
  refreshProfile: async () => { const { data } = await profileApi.get(); set({ user: data }); return data; },
}));
