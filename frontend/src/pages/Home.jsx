import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, ShieldCheck, FileLock2, Building2, Car, Wrench, ArrowRight } from "lucide-react";
import StatCard from "../components/StatCard";
import { api } from "../lib/api";
import { fmtNumber } from "../lib/format";

export default function Home() {
  const [stats, setStats] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    api.stats()
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setCargando(false));
  }, []);

  return (
    <div>
      <section className="hero-bg relative">
        {/* El clip vive en una capa propia: si envuelve al hero recorta las stat cards */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute inset-0 hero-asfalto" />
          <div className="estela estela-faro-1" />
          <div className="estela estela-faro-2" />
          <div className="estela estela-fria" />
          <div className="estela estela-freno-1" />
          <div className="estela estela-freno-2" />
          <div className="absolute inset-0 hero-vineta" />
        </div>
        <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />

        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-20 sm:py-28 text-center">
          <span className="badge bg-white/[0.08] text-[#ffd98a] border border-white/15 backdrop-blur-sm animate-fade-up">
            <ShieldCheck size={14} /> Verificable on-chain
          </span>

          <h1 className="mt-5 text-4xl sm:text-6xl font-semibold tracking-tight text-white animate-fade-up [animation-delay:60ms]">
            Historial vehicular oficial,
            <br />
            <span className="bg-gradient-to-r from-[#ffd98a] to-white bg-clip-text text-transparent">
              inmutable desde los 0km.
            </span>
          </h1>

          <p className="mt-6 text-lg text-slate-300 leading-relaxed max-w-2xl mx-auto animate-fade-up [animation-delay:120ms]">
            Cada service oficial se sella en blockchain por la red de concesionarias
            autorizadas. Sin papeles, sin alteraciones, sin ambiguedad.
          </p>

          <div className="mt-9 flex flex-wrap items-center justify-center gap-3 animate-fade-up [animation-delay:180ms]">
            <Link to="/consulta" className="btn-primary shadow-lg shadow-black/50">
              <Search size={16} /> Consultar un vehiculo
            </Link>
            <Link to="/login" className="btn-ghost-light">
              <Building2 size={16} /> Acceso concesionarias
            </Link>
          </div>
        </div>

      </section>

      {/* Metricas montadas sobre el borde del hero, ya fuera de su capa de clip */}
      <div className="relative z-10 -mt-10 sm:-mt-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard
              icon={<Car size={18} />}
              label="Vehiculos registrados"
              value={fmtNumber(stats?.vehiculos_registrados ?? 0)}
              hint="Altas oficiales certificadas"
              loading={cargando}
            />
            <StatCard
              icon={<Wrench size={18} />}
              label="Eventos en cadena"
              value={fmtNumber(stats?.servicios_registrados ?? 0)}
              hint="Servicios sellados en Polygon"
              loading={cargando}
            />
            <StatCard
              icon={<Building2 size={18} />}
              label="Concesionarias activas"
              value={fmtNumber(stats?.concesionarias_activas ?? 0)}
              hint="Wallets autorizadas en el contrato"
              loading={cargando}
            />
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 pt-24 pb-20">
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">
            Por que un historial en Trazarg no se puede adulterar
          </h2>
          <p className="mt-3 text-slate-600">
            La garantia no depende de la buena fe de nadie: la impone el contrato.
          </p>
        </div>

        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
          <Feature
            icon={<FileLock2 size={20} />}
            title="Evidencia hasheada"
            desc="La orden de trabajo se almacena cifrada y su hash SHA-256 viaja a la blockchain. Cualquier alteracion del archivo rompe la prueba."
          />
          <Feature
            icon={<ShieldCheck size={20} />}
            title="Solo concesionarias oficiales"
            desc="Unicamente wallets autorizadas en el contrato pueden registrar eventos. Talleres particulares y dueños no pueden adulterar el linaje."
          />
          <Feature
            icon={<Search size={20} />}
            title="Consulta sin cuenta"
            desc="Cualquier comprador puede ingresar el VIN o la patente y obtener el historial completo verificado en cadena."
          />
        </section>

        <div className="mt-14 text-center">
          <Link
            to="/consulta"
            className="inline-flex items-center gap-1.5 text-brand-500 hover:text-brand-600 font-medium transition"
          >
            Probar con un VIN real <ArrowRight size={16} />
          </Link>
        </div>
      </div>
    </div>
  );
}

function Feature({ icon, title, desc }) {
  return (
    <div className="card card-hover p-6">
      <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-brand-50 text-brand-500 mb-4">
        {icon}
      </div>
      <h3 className="font-semibold text-slate-900">{title}</h3>
      <p className="text-sm text-slate-600 mt-2 leading-relaxed">{desc}</p>
    </div>
  );
}
