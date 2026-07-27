import { useAuthStore } from "../../store/authStore";

export function HomeOperador() {
  const logout = useAuthStore((state) => state.logout);

  return (
    <main className="flex min-h-screen w-full flex-col items-center justify-center gap-6 bg-white">
      <h1 className="text-3xl font-bold text-neutral-900">Hola</h1>
      <p className="text-lg text-neutral-600">Panel de operador</p>
      <button
        onClick={logout}
        className="cursor-pointer rounded-md bg-neutral-800 px-4 py-2 text-base font-semibold text-white outline-none hover:bg-neutral-700"
      >
        Cerrar sesión
      </button>
    </main>
  );
}
