import { API_BASE_URL } from "./config";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function iniciarSesion(usuario: string, password: string): Promise<TokenResponse> {
  const resp = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario, password }),
  });

  if (!resp.ok) {
    const data = await resp.json().catch(() => null);
    throw new ApiError(resp.status, data?.detail ?? "No se pudo iniciar sesión");
  }

  return resp.json();
}
