import { jwtDecode } from "jwt-decode";
import { create } from "zustand";

export type Rol = "operador" | "administrador";

interface TokenPayload {
  sub: string;
  uid: number;
  rol: Rol;
  exp: number;
}

interface AuthState {
  token: string | null;
  usuario: string | null;
  rol: Rol | null;
  login: (token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  usuario: null,
  rol: null,
  login: (token) => {
    const payload = jwtDecode<TokenPayload>(token);
    set({ token, usuario: payload.sub, rol: payload.rol });
  },
  logout: () => set({ token: null, usuario: null, rol: null }),
}));
