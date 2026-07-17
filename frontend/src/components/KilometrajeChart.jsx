import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function KilometrajeChart({ eventos }) {
  const data = eventos.map((e) => ({
    fecha: new Date(e.chain_timestamp).toLocaleDateString("es-AR", {
      year: "2-digit",
      month: "short",
    }),
    km: e.kilometraje,
    tipo: e.tipo_nombre,
  }));

  if (data.length === 0) return null;

  return (
    <div className="card p-5">
      <h3 className="text-sm font-medium text-slate-600 mb-4">
        Evolucion de kilometraje
      </h3>
      <div style={{ width: "100%", height: 240 }}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="fecha" stroke="#64748b" fontSize={12} />
            <YAxis stroke="#64748b" fontSize={12} />
            <Tooltip
              contentStyle={{
                background: "white",
                border: "1px solid #e2e8f0",
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(value, _, p) => [
                `${value.toLocaleString("es-AR")} km`,
                p.payload.tipo,
              ]}
            />
            <Line
              type="monotone"
              dataKey="km"
              stroke="#1f4f83"
              strokeWidth={2.5}
              dot={{ r: 4, fill: "#1f4f83" }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
