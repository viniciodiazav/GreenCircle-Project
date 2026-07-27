import { useState } from "react";
import { ApiError, iniciarSesion } from "../../api/client";
import { useAuthStore } from "../../store/authStore";

export function LoginScreen() {
  const login = useAuthStore((state) => state.login);
  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      const { access_token } = await iniciarSesion(usuario, password);
      login(access_token);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("No se pudo conectar con el servidor");
      }
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center gap-8 bg-white">
      <h1 className="text-5xl font-bold text-neutral-900">GreenCircle</h1>
      <div className="w-80 rounded-lg bg-stone-100 p-8 shadow-sm">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            placeholder="Usuario"
            value={usuario}
            onChange={(e) => setUsuario(e.currentTarget.value)}
            autoFocus
            className="w-full rounded-md border-none bg-white px-3.5 py-2.5 text-base text-neutral-900 outline-none"
          />
          <input
            type="password"
            placeholder="Contraseña"
            value={password}
            onChange={(e) => setPassword(e.currentTarget.value)}
            className="w-full rounded-md border-none bg-white px-3.5 py-2.5 text-base text-neutral-900 outline-none"
          />
          <button
            type="submit"
            disabled={cargando}
            className="w-full cursor-pointer rounded-md bg-neutral-800 px-3.5 py-3 text-base font-semibold text-white outline-none hover:bg-neutral-700 disabled:cursor-not-allowed disabled:bg-neutral-400"
          >
            {cargando ? "Entrando..." : "Iniciar sesión"}
          </button>
        </form>
        {error && <p className="mt-4 text-center text-sm text-red-700">{error}</p>}
      </div>
    </div>
  );
}
