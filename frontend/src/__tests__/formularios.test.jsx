import { describe, it, expect, vi } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { api } from "../lib/api";
import { renderApp, iniciarSesion, VEHICULOS } from "./helpers.jsx";

vi.mock("../lib/api", () => ({
  api: {
    stats: vi.fn().mockResolvedValue({}),
    misVehiculos: vi.fn(),
    estadoRed: vi.fn(),
    altaVehiculo: vi.fn(),
    registrarServicio: vi.fn(),
  },
}));

function completar(etiqueta, valor) {
  const label = screen.getByText(etiqueta, { selector: "label" });
  fireEvent.change(label.parentElement.querySelector("input, textarea, select"), { target: { value: valor } });
}

describe("alta de vehículo 0 km", () => {
  it("registra el vehículo y muestra la transacción", async () => {
    api.altaVehiculo.mockResolvedValue({ vin: "8AP1234567ABC8901", tx_hash_alta: "0x" + "c".repeat(64) });
    api.misVehiculos.mockResolvedValue(VEHICULOS);
    iniciarSesion();
    renderApp("/vehiculos/nuevo");
    completar("VIN", "8AP1234567ABC8901");
    completar("Patente", "AB123CD");
    completar("Marca", "Toyota");
    completar("Modelo", "Corolla");
    fireEvent.click(screen.getByText("Registrar en cadena"));
    expect(await screen.findByText("Vehiculo registrado en cadena")).toBeTruthy();
    const enviado = api.altaVehiculo.mock.calls[0][1];
    expect(enviado.get("vin")).toBe("8AP1234567ABC8901");

    fireEvent.click(screen.getByText("Cargar otro"));
    expect(screen.getByText("Registrar en cadena")).toBeTruthy();
  });

  it("navega a la lista tras el alta", async () => {
    api.altaVehiculo.mockResolvedValue({ vin: "8AP1234567ABC8901", tx_hash_alta: null });
    api.misVehiculos.mockResolvedValue(VEHICULOS);
    iniciarSesion();
    renderApp("/vehiculos/nuevo");
    completar("VIN", "8AP1234567ABC8901");
    completar("Patente", "AB123CD");
    completar("Marca", "Toyota");
    completar("Modelo", "Corolla");
    fireEvent.click(screen.getByText("Registrar en cadena"));
    fireEvent.click(await screen.findByText("Ir a la lista"));
    expect(await screen.findByText("Vehiculos registrados")).toBeTruthy();
  });

  it("muestra el error del backend y permite cancelar", async () => {
    api.altaVehiculo.mockRejectedValue(new Error("VIN ya registrado"));
    iniciarSesion();
    renderApp("/vehiculos/nuevo");
    completar("VIN", "8AP1234567ABC8901");
    completar("Patente", "AB123CD");
    completar("Marca", "Toyota");
    completar("Modelo", "Corolla");
    fireEvent.click(screen.getByText("Registrar en cadena"));
    expect(await screen.findByText("VIN ya registrado")).toBeTruthy();
    fireEvent.click(screen.getByText("Cancelar"));
  });
});

describe("registro de service", () => {
  it("sella un service sin comprobante", async () => {
    api.registrarServicio.mockResolvedValue({ km_regresivo: false, block_number: 99, con_evidencia: false, tx_hash: "0x" + "d".repeat(64) });
    iniciarSesion();
    renderApp("/servicios/nuevo");
    completar("VIN o patente del vehiculo", "AB123CD");
    completar("Kilometraje", "10000");
    completar("Descripcion (opcional)", "Cambio de aceite y filtros");
    fireEvent.click(screen.getByText("Sellar en blockchain"));
    expect(await screen.findByText("Service registrado en cadena")).toBeTruthy();
    expect(screen.getByText("Registrado sin comprobante adjunto.")).toBeTruthy();
    expect(api.registrarServicio.mock.calls[0][1].get("archivo")).toBeNull();
    fireEvent.click(screen.getByText("Cargar otro"));
    expect(screen.getByText("Sellar en blockchain")).toBeTruthy();
  });

  it("adjunta el comprobante cuando se elige un archivo", async () => {
    api.registrarServicio.mockResolvedValue({ km_regresivo: false, block_number: 100, con_evidencia: true, tx_hash: null });
    api.misVehiculos.mockResolvedValue(VEHICULOS);
    api.estadoRed.mockResolvedValue({ block_number: 1, chain_id: 80002, contract_address: "0xabc" });
    iniciarSesion();
    renderApp("/servicios/nuevo");
    completar("VIN o patente del vehiculo", "AB123CD");
    completar("Kilometraje", "10000");
    const archivo = new File(["orden"], "orden.pdf", { type: "application/pdf" });
    fireEvent.change(document.querySelector("input[type=file]"), { target: { files: [archivo] } });
    fireEvent.click(screen.getByText("Sellar en blockchain"));
    expect(await screen.findByText("Bloque #100")).toBeTruthy();
    expect(api.registrarServicio.mock.calls[0][1].get("archivo").name).toBe("orden.pdf");
    fireEvent.click(screen.getByText("Volver al dashboard"));
    expect(await screen.findByText("Hola, Concesionaria Norte")).toBeTruthy();
  });

  it("muestra la anomalía cuando el kilometraje es regresivo", async () => {
    api.registrarServicio.mockResolvedValue({
      km_regresivo: true, km_cargado: 18400, km_anterior: 30560, diferencia: 12160,
      advertencia: "Kilometraje regresivo: sellado en blockchain como anomalía.",
      tx_hash: "0x" + "e".repeat(64),
    });
    iniciarSesion();
    renderApp("/servicios/nuevo");
    completar("VIN o patente del vehiculo", "AB123CD");
    completar("Kilometraje", "18400");
    expect(screen.getByText("18.400 km")).toBeTruthy();
    fireEvent.click(screen.getByText("Sellar en blockchain"));
    expect(await screen.findByText("Anomalía registrada: kilometraje regresivo")).toBeTruthy();
    expect(screen.getByText("-12.160 km")).toBeTruthy();
    expect(screen.getByText(/^tx: 0xeeeeeeee/)).toBeTruthy();
  });

  it("muestra el error del backend y permite cancelar", async () => {
    api.registrarServicio.mockRejectedValue(new Error("Vehiculo no registrado"));
    iniciarSesion();
    renderApp("/servicios/nuevo");
    completar("VIN o patente del vehiculo", "ZZ999ZZ");
    fireEvent.click(screen.getByText("Sellar en blockchain"));
    expect(await screen.findByText("Vehiculo no registrado")).toBeTruthy();
    fireEvent.click(screen.getByText("Cancelar"));
  });
});
