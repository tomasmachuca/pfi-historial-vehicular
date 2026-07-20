import { useId } from "react";

/**
 * Marca Trazarg: el bloque contiene al auto, calado en negativo.
 * El auto vive dentro del bloque, que es lo que hace el sistema.
 */
export function LogoMark({ size = 28, className = "" }) {
  // Sin id unico, dos marcas en la misma pagina comparten la mascara.
  // useId devuelve ":r1:" y los dos puntos rompen url(#...) en algunos navegadores.
  const maskId = `trz-${useId().replace(/:/g, "")}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <mask id={maskId}>
          <rect width="32" height="32" fill="#fff" />
          <path
            d="M7 20.4v-3.2c0-.75.52-1.4 1.25-1.57l3.05-.72 2.5-3.3c.42-.56 1.08-.89 1.78-.89h4.9c.72 0 1.4.35 1.82.95l2.2 3.24 2.6.64"
            stroke="#000"
            strokeWidth="2.1"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
          <circle cx="11.6" cy="20.6" r="2.2" fill="#000" />
          <circle cx="21.4" cy="20.6" r="2.2" fill="#000" />
        </mask>
      </defs>
      <rect
        x="2"
        y="2"
        width="28"
        height="28"
        rx="8"
        fill="currentColor"
        mask={`url(#${maskId})`}
      />
    </svg>
  );
}

export default function Logo({
  size = 28,
  className = "",
  markClassName = "text-brand-900",
  wordClassName = "text-slate-900",
  showWord = true,
}) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <LogoMark size={size} className={markClassName} />
      {showWord && (
        <span className={`font-semibold tracking-tight text-[1.05rem] ${wordClassName}`}>
          Trazarg
        </span>
      )}
    </span>
  );
}
