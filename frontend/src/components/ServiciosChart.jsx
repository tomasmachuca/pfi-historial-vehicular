import {
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const COLORS = ["#1f4f83", "#2d6cb1", "#3a8ad9", "#5aa6e6", "#86c2ee"];

export default function ServiciosChart({ eventos }) {
  const counts = {};
  eventos.forEach((e) => {
    counts[e.tipo_nombre] = (counts[e.tipo_nombre] || 0) + 1;
  });
  const data = Object.entries(counts).map(([tipo, cantidad]) => ({ tipo, cantidad }));

  if (data.length === 0) return null;

  return (
    <div className="card p-5">
      <h3 className="text-sm font-medium text-slate-600 mb-4">
        Tipos de eventos registrados
      </h3>
      <div style={{ width: "100%", height: 240 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="tipo" stroke="#64748b" fontSize={11} interval={0} angle={-15} textAnchor="end" height={60} />
            <YAxis allowDecimals={false} stroke="#64748b" fontSize={12} />
            <Tooltip
              contentStyle={{
                background: "white",
                border: "1px solid #e2e8f0",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Bar dataKey="cantidad" radius={[6, 6, 0, 0]}>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
