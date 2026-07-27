import { HomeAdministrador } from "./screens/administrador/HomeAdministrador";
import { LoginScreen } from "./screens/login/LoginScreen";
import { HomeOperador } from "./screens/operador/HomeOperador";
import { useAuthStore } from "./store/authStore";
import "./App.css";

function App() {
  const token = useAuthStore((state) => state.token);
  const rol = useAuthStore((state) => state.rol);

  if (token === null) {
    return <LoginScreen />;
  }

  return rol === "administrador" ? <HomeAdministrador /> : <HomeOperador />;
}

export default App;
