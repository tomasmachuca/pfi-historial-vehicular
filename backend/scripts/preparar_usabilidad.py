"""Prepara los historiales de demostración de la prueba de usabilidad.

Crea, contra el sistema desplegado, los tres vehículos que pide el protocolo:

- Vehículo A (tareas T1, T2 y T4): alta y dos services con comprobante, cargados
  por dos concesionarias distintas. Puntaje alto.
- Vehículo B (tarea T3): alta, tres services y un intento de kilometraje regresivo,
  que el contrato sella como anomalía. Puntaje limitado a 59.
- Vehículo C (tarea T5): alta y service de 10.000 km; el participante registra el
  de 20.000 km durante la prueba.

Genera además el comprobante ficticio en PDF, sin datos personales, que el
participante adjunta en la tarea T5. Las credenciales van por variables de entorno:

    set TRAZARG_API=https://<backend>
    set TRAZARG_EMAIL_1=<correo de la concesionaria 1>
    set TRAZARG_PASSWORD_1=<contraseña>
    set TRAZARG_EMAIL_2=<correo de la concesionaria 2>
    set TRAZARG_PASSWORD_2=<contraseña>
    python scripts/preparar_usabilidad.py
"""
import os
import random
import string
import sys

import requests

API = os.environ.get("TRAZARG_API", "").rstrip("/")


def _pdf(texto: str) -> bytes:
    """PDF mínimo de una página con una línea de texto (comprobante ficticio)."""
    contenido = f"BT /F1 14 Tf 60 760 Td ({texto}) Tj ET".encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
         b"/Resources << /Font << /F1 5 0 R >> >> >>"),
        b"<< /Length " + str(len(contenido)).encode() + b" >>\nstream\n" + contenido + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    salida, offsets = b"%PDF-1.4\n", []
    for i, obj in enumerate(objetos, start=1):
        offsets.append(len(salida))
        salida += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    salida += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return salida


def _sesion(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=120)
    r.raise_for_status()
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


def _identificadores() -> tuple[str, str]:
    letras = random.choices(string.ascii_uppercase, k=4)
    patente = f"{letras[0]}{letras[1]}{random.randint(100, 999)}{letras[2]}{letras[3]}"
    vin = "8AP" + "".join(random.choices(string.ascii_uppercase + string.digits, k=14))
    return vin, patente


def _alta(s, marca, modelo, color) -> str:
    vin, patente = _identificadores()
    r = s.post(f"{API}/vehiculos", timeout=300, data={
        "vin": vin, "patente": patente, "marca": marca, "modelo": modelo, "anio": "2026",
        "color": color, "km_inicial": "0",
    }, files={"archivo": ("factura-0km.pdf", _pdf(f"Factura de venta 0 km - {marca} {modelo}"), "application/pdf")})
    r.raise_for_status()
    return patente


def _service(s, patente, km, tipo, comprobante=True) -> dict:
    files = None
    if comprobante:
        files = {"archivo": (f"orden-{km}.pdf", _pdf(f"Orden de trabajo - service {km} km"), "application/pdf")}
    r = s.post(f"{API}/servicios", timeout=300, files=files, data={
        "vin": patente, "tipo_servicio": str(tipo), "kilometraje": str(km), "descripcion": f"Service de {km} km",
    })
    r.raise_for_status()
    return r.json()


def main() -> int:
    faltan = [v for v in ("TRAZARG_API", "TRAZARG_EMAIL_1", "TRAZARG_PASSWORD_1",
                          "TRAZARG_EMAIL_2", "TRAZARG_PASSWORD_2") if not os.environ.get(v)]
    if faltan:
        print("Faltan variables de entorno:", ", ".join(faltan), file=sys.stderr)
        return 1
    s1 = _sesion(os.environ["TRAZARG_EMAIL_1"], os.environ["TRAZARG_PASSWORD_1"])
    s2 = _sesion(os.environ["TRAZARG_EMAIL_2"], os.environ["TRAZARG_PASSWORD_2"])

    a = _alta(s1, "Toyota", "Corolla", "Gris")
    _service(s1, a, 10_000, 1)
    _service(s2, a, 20_000, 2)

    b = _alta(s1, "Volkswagen", "Gol", "Blanco")
    _service(s1, b, 10_000, 1)
    _service(s1, b, 20_000, 2, comprobante=False)
    _service(s2, b, 30_560, 3)
    anomalia = _service(s2, b, 18_400, 2, comprobante=False)

    c = _alta(s1, "Peugeot", "208", "Rojo")
    _service(s1, c, 10_000, 1)

    with open("comprobante_T5.pdf", "wb") as f:
        f.write(_pdf("Orden de trabajo ficticia - service 20.000 km - sin datos personales"))

    for patente, etiqueta in ((a, "A, tareas T1, T2 y T4"), (b, "B, tarea T3"), (c, "C, tarea T5")):
        p = requests.get(f"{API}/publico/vehiculo/{patente}", timeout=120).json()
        print(f"Vehículo {etiqueta}: patente {patente}, puntaje {p['score']['puntaje']} ({p['score']['nivel']}), "
              f"anomalías en cadena {p['cadena']['anomalias_on_chain']}")
    print(f"Anomalía sellada en la transacción {anomalia['tx_hash']}")
    print("Comprobante para T5: comprobante_T5.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
