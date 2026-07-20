export const EXPLORER = import.meta.env.VITE_EXPLORER_URL || "https://amoy.polygonscan.com";

export function txUrl(hash) {
  if (!hash) return null;
  return `${EXPLORER}/tx/${hash}`;
}

export function shorten(addr, lead = 6, tail = 4) {
  if (!addr) return "";
  if (addr.length <= lead + tail) return addr;
  return `${addr.slice(0, lead)}...${addr.slice(-tail)}`;
}

export function fmtNumber(n) {
  if (n === null || n === undefined) return "-";
  return new Intl.NumberFormat("es-AR").format(n);
}

export function fmtDate(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleDateString("es-AR", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}
