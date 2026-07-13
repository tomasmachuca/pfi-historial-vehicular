import { calcularScore } from "./utils.js";

export default function App() {
  const score = calcularScore(5, 5);
  return (
    <main>
      <h1>Historial Vehicular</h1>
      <p>Puntaje de confiabilidad de ejemplo: {score}</p>
    </main>
  );
}
