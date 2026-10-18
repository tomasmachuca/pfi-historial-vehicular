import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import { api } from "../lib/api";
import { renderApp, iniciarSesion, VEHICULOS } from "./helpers.jsx";

vi.mock("../lib/api", () => ({
  api: {
    stats: vi.fn(),
    login: vi.fn(),
    misVehiculos: vi.fn(),
    estadoRed: vi.fn(),
    bajaCuenta: vi.fn(),
  },
}));

beforeEach(() => {
  api.stats.mockResolvedValue({ vehiculos_registrados: 12, servicios_registrados: 40, concesionarias_activas: 3 });
  api.misVehiculos.mockResolvedValue(VEHICULOS);
  api.estadoRed.mockResolvedValue({ block_number: 4567, chain_id: 80002, contract_address: "0xB6B07B384265D5087497863fd12977ecf1f98Bbb" });
});

describe("navegación y sesión", () => {
  it("muestra la portada con las estadísticas del sistema", async () => {
    renderApp("/");
    expect(await screen.findByText("40")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ingresar" })).toBeTruthy();
  });

  it("tolera que las estadísticas no estén disponibles", async () => {
    api.stats.mockRejectedValue(new Error("sin red"));
    renderApp("/");
    await waitFor(() => expect(api.stats).toHaveBeenCalled());
    expect(screen.getAllByText("Trazarg").length).toBeGreaterThan(0);
  });

  it("redirige al login si una ruta privada no tiene sesión", async () => {
    renderApp("/dashboard");
    expect(await screen.findByText("Acceso concesionaria")).toBeTruthy();
  });

  it("redirige a la portada una ruta inexistente", async () => {
    renderApp("/no-existe");
    expect(await screen.findByText("40")).toBeTruthy();
  });

  it("ignora una sesión guardada corrupta", async () => {
    localStorage.setItem("historial0km.session", "{no es json");
    renderApp("/dashboard");
    expect(await screen.findByText("Acceso concesionaria")).toBeTruthy();
  });

  it("inicia sesión y vuelve a la ruta pedida", async () => {
    api.login.mockResolvedValue({ access_token: "t", concesionaria_id: "c-1", nombre: "Concesionaria Norte", wallet_address: "0xabc" });
    renderApp("/login");
    fireEvent.change(screen.getByPlaceholderText("ventas@concesionaria.com"), { target: { value: "norte@example.com" } });
    fireEvent.change(document.querySelector("input[type=password]"), { target: { value: "clave" } });
    fireEvent.click(screen.getByRole("button", { name: "Ingresar" }));
    expect(await screen.findByText("Hola, Concesionaria Norte")).toBeTruthy();
    expect(api.login).toHaveBeenCalledWith("norte@example.com", "clave");
  });

  it("informa credenciales inválidas", async () => {
    api.login.mockRejectedValue(new Error("Credenciales invalidas"));
    renderApp("/login");
    fireEvent.change(screen.getByPlaceholderText("ventas@concesionaria.com"), { target: { value: "x@example.com" } });
    fireEvent.change(document.querySelector("input[type=password]"), { target: { value: "mal" } });
    fireEvent.click(screen.getByRole("button", { name: "Ingresar" }));
    expect(await screen.findByText("Credenciales invalidas")).toBeTruthy();
  });

  it("cierra la sesión desde la barra de navegación", async () => {
    iniciarSesion();
    renderApp("/dashboard");
    fireEvent.click(await screen.findByTitle("Cerrar sesion"));
    expect(await screen.findByRole("link", { name: "Ingresar" })).toBeTruthy();
    expect(localStorage.getItem("historial0km.session")).toBeNull();
  });
});

describe("tablero de la concesionaria", () => {
  it("lista los vehículos y marca los que tienen anomalías", async () => {
    iniciarSesion();
    renderApp("/dashboard");
    expect(await screen.findByText("8AP1234567ABC8901")).toBeTruthy();
    expect(screen.getByTitle("1 service(s) con kilometraje regresivo")).toBeTruthy();
    expect(screen.getByText("4.567")).toBeTruthy();
  });

  it("invita a cargar el primer vehículo si no hay ninguno", async () => {
    api.misVehiculos.mockResolvedValue([]);
    iniciarSesion();
    renderApp("/dashboard");
    expect(await screen.findByText("Crear el primero")).toBeTruthy();
  });

  it("da de baja la cuenta con la contraseña y cierra la sesión", async () => {
    api.bajaCuenta.mockResolvedValue({ ok: true });
    iniciarSesion();
    renderApp("/dashboard");
    fireEvent.click(await screen.findByText("Dar de baja la cuenta"));
    fireEvent.change(screen.getByLabelText("Confirmá con tu contraseña"), { target: { value: "clave" } });
    fireEvent.click(screen.getByText("Confirmar baja"));
    expect(await screen.findByRole("link", { name: "Ingresar" })).toBeTruthy();
    expect(api.bajaCuenta).toHaveBeenCalledWith("token-de-prueba", "clave");
  });

  it("informa el error de la baja y permite cancelar", async () => {
    api.bajaCuenta.mockRejectedValue(new Error("Contraseña incorrecta"));
    iniciarSesion();
    renderApp("/dashboard");
    fireEvent.click(await screen.findByText("Dar de baja la cuenta"));
    fireEvent.change(screen.getByLabelText("Confirmá con tu contraseña"), { target: { value: "mal" } });
    fireEvent.click(screen.getByText("Confirmar baja"));
    expect(await screen.findByText("Contraseña incorrecta")).toBeTruthy();
    fireEvent.click(screen.getByText("Cancelar"));
    expect(screen.getByText("Dar de baja la cuenta")).toBeTruthy();
  });
});

describe("vehículos de la concesionaria", () => {
  it("filtra la lista por VIN, patente o modelo", async () => {
    iniciarSesion();
    renderApp("/vehiculos");
    expect(await screen.findByText("9BWZZZ377VT004251")).toBeTruthy();
    expect(screen.getByText("pending")).toBeTruthy();
    fireEvent.change(screen.getByPlaceholderText("Filtrar por VIN, patente o modelo..."), { target: { value: "taos" } });
    expect(screen.queryByText("8AP1234567ABC8901")).toBeNull();
    expect(screen.getByText("9BWZZZ377VT004251")).toBeTruthy();
  });
});
