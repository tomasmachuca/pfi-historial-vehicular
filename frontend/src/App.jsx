import { lazy, Suspense, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { despertarServidor } from "./lib/despertar";

import Home from "./pages/Home";
import Login from "./pages/Login";
import ConsultaPublica from "./pages/ConsultaPublica";

// El panel de la concesionaria se carga aparte: quien solo consulta un historial,
// casi siempre desde el celular, no descarga su código.
const Dashboard = lazy(() => import("./pages/Dashboard"));
const MisVehiculos = lazy(() => import("./pages/MisVehiculos"));
const AltaVehiculo = lazy(() => import("./pages/AltaVehiculo"));
const RegistrarServicio = lazy(() => import("./pages/RegistrarServicio"));

export default function App() {
  useEffect(() => {
    despertarServidor();
  }, []);

  return (
    <Layout>
      <Suspense fallback={<div className="max-w-5xl mx-auto px-6 py-12 text-sm text-slate-500">Cargando...</div>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/consulta" element={<ConsultaPublica />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/vehiculos"
          element={
            <ProtectedRoute>
              <MisVehiculos />
            </ProtectedRoute>
          }
        />
        <Route
          path="/vehiculos/nuevo"
          element={
            <ProtectedRoute>
              <AltaVehiculo />
            </ProtectedRoute>
          }
        />
        <Route
          path="/servicios/nuevo"
          element={
            <ProtectedRoute>
              <RegistrarServicio />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
    </Layout>
  );
}
