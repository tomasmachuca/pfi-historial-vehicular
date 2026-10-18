import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../App.jsx";
import { AuthProvider } from "../contexts/AuthContext.jsx";

export const SESION = {
  token: "token-de-prueba",
  concesionariaId: "c-1",
  nombre: "Concesionaria Norte",
  walletAddress: "0x1234567890abcdef1234567890abcdef12345678",
};

export function iniciarSesion(sesion = SESION) {
  localStorage.setItem("historial0km.session", JSON.stringify(sesion));
}

/** Renderiza la aplicación completa en una ruta, con el proveedor de sesión real. */
export function renderApp(ruta = "/") {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>
  );
}

export const VEHICULOS = [
  {
    id: "v1", vin: "8AP1234567ABC8901", patente: "AB123CD", marca: "Toyota", modelo: "Corolla",
    anio: 2026, color: "Gris", km_inicial: 0, tx_hash_alta: "0x" + "a".repeat(64), anomalias_count: 1,
    creado_en: "2026-08-01T12:00:00Z",
  },
  {
    id: "v2", vin: "9BWZZZ377VT004251", patente: null, marca: "Volkswagen", modelo: "Taos",
    anio: 2025, color: null, km_inicial: 5, tx_hash_alta: null, anomalias_count: 0,
    creado_en: "2026-07-01T12:00:00Z",
  },
];

export function consulta({ anomalias = 1, verificados = true } = {}) {
  const base = {
    tipo_servicio: 1, tipo_nombre: "Service oficial", concesionaria_nombre: "Concesionaria Norte",
    descripcion: null, archivo_url: null, km_anterior: null, km_regresivo: false, verificado: verificados,
  };
  const eventos = [
    { ...base, tipo_servicio: 0, tipo_nombre: "Alta 0km", kilometraje: 0, chain_timestamp: "2026-01-10T10:00:00Z",
      hash_evidencia: "0".repeat(64), tx_hash: "0x" + "1".repeat(64) },
    { ...base, kilometraje: 10000, chain_timestamp: "2026-06-10T10:00:00Z", descripcion: "Primer service",
      hash_evidencia: "ab".repeat(32), archivo_url: "https://evidencias.test/orden.pdf", tx_hash: "0x" + "2".repeat(64) },
  ];
  for (let i = 0; i < anomalias; i += 1) {
    eventos.push({ ...base, kilometraje: 4000 + i, chain_timestamp: null, hash_evidencia: "0".repeat(64), tx_hash: null,
      km_regresivo: true, km_anterior: 10000, verificado: false });
  }
  return {
    vehiculo: { vin: "8AP1234567ABC8901", patente: "AB123CD", marca: "Toyota", modelo: "Corolla", anio: 2026,
      color: "Gris", km_inicial: 0, anomalias_count: anomalias, creado_en: "2026-01-10T10:00:00Z" },
    eventos,
    score: {
      puntaje: anomalias ? 59 : 93, nivel: anomalias ? "bajo" : "alto",
      razones: [
        { texto: "El kilometraje nunca retrocedió entre registros.", tipo: "positivo" },
        { texto: "1 de 2 registros tiene comprobante adjunto.", tipo: "neutro" },
        { texto: "Por tener anomalías de kilometraje, el puntaje se limita a 59.", tipo: "negativo" },
        { texto: "Razón sin tipo conocido.", tipo: "otro" },
      ],
      componentes: [
        { clave: "anomalias", nombre: "Ausencia de anomalías", puntos: 10, maximo: 30 },
        { clave: "evidencia", nombre: "Cobertura de evidencia", puntos: 10, maximo: 20 },
      ],
    },
    cadena: { verificado: true, tx_hash_alta: "0x" + "1".repeat(64), contrato: "0xB6B07B384265D5087497863fd12977ecf1f98Bbb",
      chain_id: 80002, cantidad_eventos_on_chain: 2, anomalias_off_chain: anomalias },
  };
}
