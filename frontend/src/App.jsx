import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import MisVehiculos from "./pages/MisVehiculos";
import AltaVehiculo from "./pages/AltaVehiculo";
import RegistrarServicio from "./pages/RegistrarServicio";
import ConsultaPublica from "./pages/ConsultaPublica";

export default function App() {
  return (
    <Layout>
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
    </Layout>
  );
}
