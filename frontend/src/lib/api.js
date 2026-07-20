const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function buildHeaders(extra = {}, token) {
  const h = { ...extra };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function handle(res) {
  if (!res.ok) {
    let detail = "Error de servidor";
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      // El cuerpo no era JSON (502, timeout, HTML de proxy): queda el mensaje por defecto.
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  baseUrl: API_URL,

  async login(email, password) {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    return handle(res);
  },

  async me(token) {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: buildHeaders({}, token),
    });
    return handle(res);
  },

  async misVehiculos(token) {
    const res = await fetch(`${API_URL}/vehiculos/mios`, {
      headers: buildHeaders({}, token),
    });
    return handle(res);
  },

  async altaVehiculo(token, formData) {
    const res = await fetch(`${API_URL}/vehiculos`, {
      method: "POST",
      headers: buildHeaders({}, token),
      body: formData,
    });
    return handle(res);
  },

  async registrarServicio(token, formData) {
    const res = await fetch(`${API_URL}/servicios`, {
      method: "POST",
      headers: buildHeaders({}, token),
      body: formData,
    });
    return handle(res);
  },

  async consultaPublica(identificador) {
    const res = await fetch(`${API_URL}/publico/vehiculo/${encodeURIComponent(identificador)}`);
    return handle(res);
  },

  async stats() {
    const res = await fetch(`${API_URL}/publico/stats`);
    return handle(res);
  },

  async estadoRed() {
    const res = await fetch(`${API_URL}/publico/red`);
    return handle(res);
  },
};
