#!/usr/bin/env node
// A qué hora sale el vídeo: el siguiente hueco libre del horario.
//
//   node cuando.mjs                                  → 2026-11-24T18:00:00+01:00
//   node cuando.mjs --json
//   node cuando.mjs --ahora 2026-11-28T19:00:00+01:00   (para probar)
//
// Reglas:
//  - De cada día se prueba primero "mejor" y luego "segunda".
//  - Un hueco vale si falta más del margen (30 min por defecto) y no está ya cogido.
//  - Si no queda ninguno hoy, se pasa al día siguiente, hasta 14 días.
//
// El desfase de Madrid (+01:00 en invierno, +02:00 en verano) se calcula para la
// fecha de salida, no para hoy. Esto importa: un vídeo que se programa el 25 de
// marzo para el 30 cruza el cambio de hora, y si se escribe el desfase de hoy
// sale publicado una hora antes.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = dirname(fileURLToPath(import.meta.url));
const DIAS = ["domingo", "lunes", "martes", "miercoles", "jueves", "viernes", "sabado"];

const argv = process.argv.slice(2);
const flag = (n, def = null) => {
  const i = argv.indexOf(`--${n}`);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : def;
};
const tiene = (n) => argv.includes(`--${n}`);

const horario = JSON.parse(readFileSync(flag("horario", join(AQUI, "horario.json")), "utf8"));
const ZONA = horario.zona || "Europe/Madrid";
const MARGEN = Number(flag("margen", 30)); // minutos
const ahora = flag("ahora") ? new Date(flag("ahora")) : new Date();
if (Number.isNaN(ahora.getTime())) {
  console.error(`--ahora no es una fecha válida: ${flag("ahora")}`);
  process.exit(1);
}

// Huecos ya cogidos, para no programar dos vídeos a la misma hora.
let cogidos = [];
const fichero = flag("programados");
if (fichero) {
  try {
    cogidos = JSON.parse(readFileSync(fichero, "utf8"))
      .map((x) => new Date(typeof x === "string" ? x : x.publishAt).getTime())
      .filter((t) => !Number.isNaN(t));
  } catch {
    cogidos = []; // todavía no existe: no hay nada cogido
  }
}

// ── La zona horaria, sin librerías ───────────────────────────────────────────
// Cuánto se adelanta la zona respecto a UTC en ese instante exacto.
function desfase(instante) {
  const f = new Intl.DateTimeFormat("en-US", {
    timeZone: ZONA, hour12: false,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
  const p = Object.fromEntries(
    f.formatToParts(instante).filter((x) => x.type !== "literal").map((x) => [x.type, x.value]),
  );
  const h = Number(p.hour) % 24; // en-US con hour12:false puede dar "24"
  const comoUTC = Date.UTC(+p.year, +p.month - 1, +p.day, h, +p.minute, +p.second);
  return (comoUTC - instante.getTime()) / 60000;
}

// La hora de reloj de Madrid (Y-M-D H:M) → el instante real.
// Se itera porque el propio desfase depende del instante que estamos buscando.
function deRelojAInstante(a, m, d, hh, mm) {
  const base = Date.UTC(a, m - 1, d, hh, mm, 0);
  let t = base;
  for (let i = 0; i < 3; i++) {
    const siguiente = base - desfase(new Date(t)) * 60000;
    if (siguiente === t) break;
    t = siguiente;
  }
  return new Date(t);
}

// El día de reloj de Madrid de un instante.
function relojDe(instante) {
  const off = desfase(instante);
  const l = new Date(instante.getTime() + off * 60000);
  return { a: l.getUTCFullYear(), m: l.getUTCMonth() + 1, d: l.getUTCDate(), semana: l.getUTCDay() };
}

function rfc3339(instante) {
  const off = desfase(instante);
  const l = new Date(instante.getTime() + off * 60000);
  const p = (n) => String(n).padStart(2, "0");
  const s = off >= 0 ? "+" : "-";
  const abs = Math.abs(off);
  return (
    `${l.getUTCFullYear()}-${p(l.getUTCMonth() + 1)}-${p(l.getUTCDate())}` +
    `T${p(l.getUTCHours())}:${p(l.getUTCMinutes())}:00${s}${p(Math.floor(abs / 60))}:${p(abs % 60)}`
  );
}

// ── Buscar el hueco ──────────────────────────────────────────────────────────
const hoy = relojDe(ahora);
const limite = ahora.getTime() + MARGEN * 60000;

let elegido = null;
for (let salto = 0; salto < 14 && !elegido; salto++) {
  // Se avanza sobre el calendario de Madrid, no sumando 24 h: el día del cambio
  // de hora dura 23 o 25 horas y sumar milisegundos se desvía.
  const dia = new Date(Date.UTC(hoy.a, hoy.m - 1, hoy.d + salto));
  const nombre = DIAS[dia.getUTCDay()];
  const franjas = horario.dias[nombre];
  if (!franjas) continue;

  for (const cual of ["mejor", "segunda"]) {
    const hhmm = franjas[cual];
    if (!hhmm) continue;
    const [hh, mm] = String(hhmm).split(":").map(Number);
    const cuando = deRelojAInstante(
      dia.getUTCFullYear(), dia.getUTCMonth() + 1, dia.getUTCDate(), hh, mm,
    );
    if (cuando.getTime() < limite) continue;          // ya ha pasado o está encima
    if (cogidos.includes(cuando.getTime())) continue; // ya hay un vídeo ahí
    elegido = { cuando, dia: nombre, cual, hhmm };
    break;
  }
}

if (!elegido) {
  console.error("No queda ningún hueco libre en los próximos 14 días. Mira horario.json.");
  process.exit(1);
}

const salida = {
  publishAt: rfc3339(elegido.cuando),
  dia: elegido.dia,
  franja: elegido.cual,
  hora_madrid: elegido.hhmm,
  desfase: rfc3339(elegido.cuando).slice(-6),
};

console.log(tiene("json") ? JSON.stringify(salida, null, 2) : salida.publishAt);
