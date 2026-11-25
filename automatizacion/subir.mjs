#!/usr/bin/env node
// Sube el vídeo a YouTube y lo deja PROGRAMADO a la hora que toque.
// Copia de la de Curiosidades Animadas, cambiada para Círculo Cerrado: sin #shorts,
// con #circulocerrado obligatorio y categoría Entretenimiento.
//
//   node subir.mjs --dir salida/canal/2026-11-24/1-publicar
//   node subir.mjs --dir ... --prueba      (no sube nada: enseña lo que enviaría)
//
// En la carpeta espera: video.mp4, portada.jpg y resumen.json.
//
// Necesita YT_CLIENT_ID, YT_CLIENT_SECRET y YT_REFRESH_TOKEN (mira autorizar.mjs).
//
// Cómo programa YouTube: no hay un estado "programado". Se sube como `private`
// con un `publishAt`, y a esa hora exacta se hace público solo. La hora la calcula
// cuando.mjs con el horario de horario.json.

import { readFileSync, statSync, existsSync, writeFileSync } from "node:fs";
import { createReadStream } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const AQUI = dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const flag = (n, d = null) => { const i = argv.indexOf(`--${n}`); return i >= 0 && i + 1 < argv.length ? argv[i + 1] : d; };
const tiene = (n) => argv.includes(`--${n}`);

const DIR = flag("dir") || process.cwd();
const PRUEBA = tiene("prueba");
const LEDGER = flag("programados", join(AQUI, "canales", `${flag("canal", "circulo-cerrado")}-programados.json`));
const CATEGORIA = flag("categoria", "24"); // 24 = Entretenimiento (historias). 27 = Educación.

// morir() corta la ejecución con código 1. No usa process.exit() a propósito:
// cortar en seco mientras hay una conexión abierta hace que Node de Windows
// escupa un "Assertion failed ... uv_handle" encima del mensaje de error.
class Fin extends Error {}
const morir = (m) => { console.error(`\nERROR: ${m}`); throw new Fin(); };
for (const evento of ["uncaughtException", "unhandledRejection"]) {
  process.on(evento, (e) => {
    if (!(e instanceof Fin)) console.error(e);
    process.exitCode = 1;
  });
}

// ── Lo que tiene que haber ───────────────────────────────────────────────────
const VIDEO = join(DIR, "video.mp4");
const PORTADA = join(DIR, "portada.jpg");
const RESUMEN = join(DIR, "resumen.json");
for (const f of [VIDEO, RESUMEN]) if (!existsSync(f)) morir(`Falta ${f}`);
if (!existsSync(PORTADA)) console.warn(`  Aviso: no hay ${PORTADA}. Se sube sin portada propia.`);

const r = JSON.parse(readFileSync(RESUMEN, "utf8"));
if (!r.titulo || !r.descripcion) morir("resumen.json necesita al menos 'titulo' y 'descripcion'.");
if (r.titulo.length > 100) morir(`El título son ${r.titulo.length} caracteres y YouTube admite 100.`);

// ── Los hashtags, con las reglas del canal ───────────────────────────────────
const tags = Array.isArray(r.hashtags) ? r.hashtags.map((h) => (h.startsWith("#") ? h : `#${h}`)) : [];
const relleno = ["#viral", "#fyp", "#parati", "#foryou"];
const problemas = [];
if (tags.length < 3 || tags.length > 5) problemas.push(`son ${tags.length} hashtags y tienen que ser de 3 a 5`);
// Círculo Cerrado: vídeos LARGOS. #shorts los mandaría al feed de shorts.
if (tags.includes("#shorts")) problemas.push("sobra #shorts: este canal es de vídeos largos");
if (!tags.includes("#circulocerrado")) problemas.push("falta #circulocerrado, el fijo del canal");
for (const t of tags) {
  if (t !== t.toLowerCase()) problemas.push(`${t} tiene mayúsculas`);
  if (/[áéíóúüñ]/i.test(t)) problemas.push(`${t} lleva tildes o eñe`);
  if (relleno.includes(t)) problemas.push(`${t} es de relleno`);
}
if (problemas.length) morir(`Los hashtags de resumen.json no cumplen el brief:\n  - ${problemas.join("\n  - ")}`);

// Las imágenes son de IA: se dice siempre (lo piden las condiciones de FLUX y es lo honrado).
const AVISO_IA = "Imágenes generadas con IA.";
const cuerpoDesc = r.descripcion.includes(AVISO_IA) ? r.descripcion.trim() : `${r.descripcion.trim()}\n${AVISO_IA}`;
const descripcion = `${cuerpoDesc}\n\n${tags.join(" ")}`;
if (descripcion.length > 5000) morir("La descripción pasa de los 5.000 caracteres de YouTube.");

// ── Cuándo sale ──────────────────────────────────────────────────────────────
const cuando = JSON.parse(
  execFileSync(process.execPath, [join(AQUI, "cuando.mjs"), "--json", "--programados", LEDGER], { encoding: "utf8" }),
);

const cuerpo = {
  snippet: {
    title: r.titulo.trim(),
    description: descripcion,
    tags: Array.isArray(r.etiquetas) ? r.etiquetas.slice(0, 30) : undefined,
    categoryId: CATEGORIA,
    defaultLanguage: "es",
    defaultAudioLanguage: "es",
  },
  status: {
    privacyStatus: "private",      // obligatorio para que publishAt valga
    publishAt: cuando.publishAt,
    selfDeclaredMadeForKids: false, // historias para adultos jóvenes, no para niños
  },
};

console.log(`\n  Vídeo:     ${VIDEO} (${(statSync(VIDEO).size / 1048576).toFixed(1)} MB)`);
console.log(`  Título:    ${cuerpo.snippet.title}`);
console.log(`  Hashtags:  ${tags.join(" ")}`);
console.log(`  Sale el:   ${cuando.dia} a las ${cuando.hora_madrid} (${cuando.franja}) → ${cuando.publishAt}`);
console.log(`  Portada:   ${existsSync(PORTADA) ? PORTADA : "ninguna"}`);

if (PRUEBA) {
  console.log("\n--prueba: no se sube nada. Esto es lo que se enviaría:\n");
  console.log(JSON.stringify(cuerpo, null, 2));
  process.exit(0);
}

// ── Entrar ───────────────────────────────────────────────────────────────────
const { YT_CLIENT_ID: ID, YT_CLIENT_SECRET: SECRETO, YT_REFRESH_TOKEN: REFRESCO } = process.env;
if (!ID || !SECRETO || !REFRESCO) morir("Faltan YT_CLIENT_ID, YT_CLIENT_SECRET o YT_REFRESH_TOKEN (mira autorizar.mjs).");

// Si la app sigue en modo "Prueba" en la consola de Google, el permiso caduca a
// los 7 días. Avisamos antes de que reviente, no después.
const CADUCA_DIAS = 7;
try {
  const { fecha, publicada } = JSON.parse(readFileSync(join(AQUI, "canales", "autorizado.json"), "utf8"));
  const dias = (Date.now() - new Date(fecha).getTime()) / 86400000;
  // Con la app publicada en la consola de Google, el permiso no caduca: no hay
  // nada de lo que avisar.
  if (!publicada && dias >= CADUCA_DIAS - 2) {
    console.warn(`\n  ⚠ El permiso de YouTube se dio hace ${dias.toFixed(1)} días.`);
    console.warn(`    Si tu app está en modo "Prueba", caduca a los ${CADUCA_DIAS}.`);
    console.warn("    Vuelve a lanzar:  node automatizacion/autorizar.mjs");
  }
} catch { /* sin fecha apuntada, no hay aviso que dar */ }

const tk = await fetch("https://oauth2.googleapis.com/token", {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({ client_id: ID, client_secret: SECRETO, refresh_token: REFRESCO, grant_type: "refresh_token" }),
});
const tkd = await tk.json();
if (!tk.ok || !tkd.access_token) {
  if (tkd.error === "invalid_grant") {
    morir(`El permiso de YouTube ya no vale.

  La causa casi segura: tu app está en modo "Prueba" en la consola de Google y
  esos permisos CADUCAN A LOS 7 DÍAS. No es que hayas hecho nada mal.

  Para arreglarlo ahora (dos minutos):
      node ${join(AQUI, "autorizar.mjs")}
    y guarda el token nuevo en YT_REFRESH_TOKEN.

  Para que no vuelva a pasar: publica la app en la consola de Google. Te pedirá
  una URL de página principal y otra de política de privacidad; con una página
  sencilla en GitHub Pages vale, y el permiso deja de caducar.

  El vídeo está hecho y a salvo en su carpeta: no se ha perdido nada.`);
  }
  morir(`No he podido entrar en tu cuenta: ${JSON.stringify(tkd)}`);
}
const AUT = { Authorization: `Bearer ${tkd.access_token}` };

// ── Subir el vídeo (reanudable: si se corta la red, no se pierde entero) ─────
const bytes = statSync(VIDEO).size;
const inicio = await fetch(
  "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
  {
    method: "POST",
    headers: { ...AUT, "Content-Type": "application/json", "X-Upload-Content-Length": String(bytes), "X-Upload-Content-Type": "video/mp4" },
    body: JSON.stringify(cuerpo),
  },
);
if (!inicio.ok) morir(`YouTube ha rechazado los datos del vídeo: ${inicio.status} ${await inicio.text()}`);
const destino = inicio.headers.get("location");
if (!destino) morir("YouTube no ha dado la dirección de subida.");

console.log("\n  Subiendo...");
const sub = await fetch(destino, {
  method: "PUT",
  headers: { "Content-Length": String(bytes), "Content-Type": "video/mp4" },
  body: createReadStream(VIDEO),
  duplex: "half",
});
if (!sub.ok) morir(`La subida ha fallado: ${sub.status} ${await sub.text()}`);
const video = await sub.json();
console.log(`  Subido: https://youtu.be/${video.id}`);

// ── La portada ───────────────────────────────────────────────────────────────
if (existsSync(PORTADA)) {
  const p = await fetch(`https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId=${video.id}`, {
    method: "POST",
    headers: { ...AUT, "Content-Type": "image/jpeg", "Content-Length": String(statSync(PORTADA).size) },
    body: createReadStream(PORTADA),
    duplex: "half",
  });
  if (p.ok) console.log("  Portada puesta.");
  else {
    const t = await p.text();
    console.warn(`  AVISO: la portada no se ha podido poner (${p.status}). El vídeo está bien igualmente.`);
    if (/unauthorized|forbidden/i.test(t)) console.warn("  Suele ser que el canal no está verificado: youtube.com/verify");
  }
}

// ── Apuntar el hueco, para que mañana no se pise ─────────────────────────────
let ledger = [];
try { ledger = JSON.parse(readFileSync(LEDGER, "utf8")); } catch { ledger = []; }
ledger.push({ publishAt: cuando.publishAt, videoId: video.id, titulo: cuerpo.snippet.title });
ledger = ledger.filter((x) => new Date(x.publishAt).getTime() > Date.now() - 30 * 86400000); // 30 días de memoria
writeFileSync(LEDGER, JSON.stringify(ledger, null, 2) + "\n");

console.log(`\n  Listo. Sale solo el ${cuando.dia} a las ${cuando.hora_madrid}.`);
console.log(`  Hasta entonces está privado: https://studio.youtube.com/video/${video.id}/edit\n`);
