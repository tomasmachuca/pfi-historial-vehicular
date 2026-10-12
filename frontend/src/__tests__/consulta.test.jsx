import { describe, it, expect, vi } from "vitest";
import { screen, fireEvent, render } from "@testing-library/react";
import { api } from "../lib/api";
import ScoreCard from "../components/ScoreCard.jsx";
import KilometrajeChart from "../components/KilometrajeChart.jsx";
import ServiciosChart from "../components/ServiciosChart.jsx";
import { renderApp, consulta } from "./helpers.jsx";

vi.mock("../lib/api", () => ({
  api: { stats: vi.fn().mockResolvedValue({}), consultaPublica: vi.fn() },
}));

function buscar(texto) {
  fireEvent.change(screen.getByPlaceholderText("VIN o patente (ej. AB123CD)"), { target: { value: texto } });
  fireEvent.click(screen.getByRole("button", { name: /Buscar/ }));
}

describe("consulta pública", () => {
  it("muestra el historial, el puntaje y la anomalía", async () => {
    api.consultaPublica.mockResolvedValue(consulta({ anomalias: 1 }));
    renderApp("/consulta");
    expect(screen.getByText("El historial se reconstruye leyendo los eventos sellados en Polygon.")).toBeTruthy();
    buscar(" ab123cd ");
    expect(await screen.findByText("Historial con 1 anomalía de kilometraje")).toBeTruthy();
    expect(api.consultaPublica).toHaveBeenCalledWith("AB123CD");
    expect(screen.getByText("59")).toBeTruthy();
    expect(screen.getByText("Confiabilidad baja")).toBeTruthy();
    expect(screen.getByText("Verificado on-chain")).toBeTruthy();
    expect(screen.getByText("Primer service")).toBeTruthy();
    expect(screen.getByText("Evidencia")).toBeTruthy();
    expect(screen.getAllByText("Sin comprobante adjunto").length).toBe(2);
    expect(screen.getByText("Sin sellado on-chain")).toBeTruthy();
    expect(screen.getByText("6.000 km por debajo del último kilometraje registrado (10.000 km).")).toBeTruthy();
    expect(screen.getByText("3 eventos")).toBeTruthy();
  });

  it("pluraliza varias anomalías y avisa si nada está verificado", async () => {
    api.consultaPublica.mockResolvedValue(consulta({ anomalias: 2, verificados: false }));
    renderApp("/consulta");
    buscar("AB123CD");
    expect(await screen.findByText("Historial con 2 anomalías de kilometraje")).toBeTruthy();
    expect(screen.getByText("Sin registro en el contrato actual")).toBeTruthy();
    expect(screen.getAllByText("No confirmado en el contrato actual").length).toBe(2);
  });

  it("muestra un historial sin anomalías con confiabilidad alta", async () => {
    api.consultaPublica.mockResolvedValue(consulta({ anomalias: 0 }));
    renderApp("/consulta");
    buscar("AB123CD");
    expect(await screen.findByText("Confiabilidad alta")).toBeTruthy();
    expect(screen.queryByText(/Historial con/)).toBeNull();
  });

  it("informa que el vehículo no existe", async () => {
    api.consultaPublica.mockRejectedValue(new Error("Vehiculo no encontrado"));
    renderApp("/consulta");
    buscar("NOEXISTE");
    expect(await screen.findByText("Vehiculo no encontrado")).toBeTruthy();
  });
});

describe("componentes de la consulta", () => {
  it("ScoreCard no muestra nada sin puntaje", () => {
    const { container } = render(<ScoreCard score={null} />);
    expect(container.innerHTML).toBe("");
  });

  it("los gráficos no se dibujan sin eventos", () => {
    expect(render(<KilometrajeChart eventos={[]} />).container.innerHTML).toBe("");
    expect(render(<ServiciosChart eventos={[]} />).container.innerHTML).toBe("");
  });
});
