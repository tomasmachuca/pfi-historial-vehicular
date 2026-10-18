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

  it("distingue la anomalía sellada en cadena", async () => {
    const datos = consulta({ anomalias: 1 });
    const anomalia = datos.eventos[2];
    Object.assign(anomalia, { verificado: true, tx_hash: "0x" + "3".repeat(64), chain_timestamp: "2026-09-01T10:00:00Z" });
    api.consultaPublica.mockResolvedValue(datos);
    renderApp("/consulta");
    buscar("AB123CD");
    expect(await screen.findByText("Anomalía sellada en cadena")).toBeTruthy();
    expect(screen.queryByText("Sin sellado on-chain")).toBeNull();
    expect(screen.getAllByText("Ver transacción en Polygonscan").length).toBe(3);
  });

  it("abre el historial desde un enlace compartido", async () => {
    api.consultaPublica.mockResolvedValue(consulta({ anomalias: 0 }));
    renderApp("/consulta?q=ab123cd");
    expect(await screen.findByText("Confiabilidad alta")).toBeTruthy();
    expect(api.consultaPublica).toHaveBeenCalledWith("AB123CD");
  });

  it("comparte el enlace, lo copia si no hay menú de compartir y descarga el PDF", async () => {
    api.consultaPublica.mockResolvedValue(consulta({ anomalias: 0 }));
    renderApp("/consulta");
    buscar("AB123CD");
    await screen.findByText("Confiabilidad alta");

    const whatsapp = screen.getByText("WhatsApp").closest("a");
    expect(decodeURIComponent(whatsapp.getAttribute("href"))).toContain("/consulta?q=AB123CD");

    const share = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "share", { value: share, configurable: true });
    fireEvent.click(screen.getByText("Compartir enlace"));
    await vi.waitFor(() => expect(share).toHaveBeenCalled());
    expect(share.mock.calls[0][0].url).toContain("/consulta?q=AB123CD");

    share.mockRejectedValueOnce(new Error("cancelado"));
    fireEvent.click(screen.getByText("Compartir enlace"));
    await vi.waitFor(() => expect(share).toHaveBeenCalledTimes(2));

    delete navigator.share;
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    fireEvent.click(screen.getByText("Compartir enlace"));
    expect(await screen.findByText("Enlace copiado")).toBeTruthy();

    writeText.mockRejectedValueOnce(new Error("sin permiso"));
    fireEvent.click(screen.getByText("Compartir enlace"));
    expect(await screen.findByText(/consulta\?q=AB123CD/)).toBeTruthy();

    const imprimir = vi.spyOn(window, "print").mockImplementation(() => {});
    fireEvent.click(screen.getByText("Descargar PDF"));
    expect(imprimir).toHaveBeenCalled();
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
