#!/usr/bin/env node
// Autorizar la subida a tu canal. Esto se hace UNA VEZ, a mano, en tu ordenador.
//
//   node autorizar.mjs
//
// Antes, en console.cloud.google.com (gratis):
//   1. Crea un proyecto.
//   2. APIs y servicios → Biblioteca → activa "YouTube Data API v3".
//   3. Pantalla de consentimiento OAuth → Externo → pon tu correo. En "Usuarios de
//      prueba" añade TU PROPIO correo, el del canal. (Sin publicar la app, solo los
//      usuarios de prueba pueden entrar, y tú te basta.)
//   4. Credenciales → Crear → ID de cliente de OAuth → tipo "Aplicación de escritorio".
//   5. Copia el ID y el secreto aquí:
//
//        export YT_CLIENT_ID=...apps.googleusercontent.com
//        export YT_CLIENT_SECRET=...
//
// Al terminar te imprime un token largo. Ese token es el que guardas como
// YT_REFRESH_TOKEN y no caduca mientras no le quites el permiso a la app.
//
// El permiso que se pide es el mínimo: subir vídeos y ponerles portada. No puede
// leer tus datos, ni borrar nada, ni tocar vídeos que ya estén publicados.

import { createServer } from "node:http";
import { randomBytes, createHash } from "node:crypto";
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = dirname(fileURLToPath(import.meta.url));

const ID = process.env.YT_CLIENT_ID;
const SECRETO = process.env.YT_CLIENT_SECRET;
const PERMISO = "https://www.googleapis.com/auth/youtube.upload";

if (!ID || !SECRETO) {
  console.error("Faltan YT_CLIENT_ID y YT_CLIENT_SECRET. Mira las instrucciones de arriba.");
  process.exit(1);
}

// PKCE: así el código que vuelve por el navegador no sirve de nada sin este secreto.
const verificador = randomBytes(32).toString("base64url");
const reto = createHash("sha256").update(verificador).digest("base64url");
const estado = randomBytes(16).toString("hex");

const servidor = createServer();
await new Promise((listo) => servidor.listen(0, "127.0.0.1", listo));
const puerto = servidor.address().port;
const vuelta = `http://127.0.0.1:${puerto}/`;

const url =
  "https://accounts.google.com/o/oauth2/v2/auth?" +
  new URLSearchParams({
    client_id: ID,
    redirect_uri: vuelta,
    response_type: "code",
    scope: PERMISO,
    access_type: "offline",
    prompt: "consent",
    state: estado,
    code_challenge: reto,
    code_challenge_method: "S256",
  });

console.log("\nAbre esto en el navegador donde tengas la sesión del canal:\n");
console.log(url + "\n");
console.log("Esperando a que des permiso...");

const codigo = await new Promise((listo, fallo) => {
  const corta = setTimeout(() => fallo(new Error("Se han pasado 5 minutos sin respuesta.")), 300000);
  servidor.on("request", (peticion, respuesta) => {
    const q = new URL(peticion.url, vuelta).searchParams;
    const fin = (texto) => {
      respuesta.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      respuesta.end(`<meta charset="utf-8"><body style="font:16px system-ui;padding:3rem">${texto}</body>`);
    };
    if (q.get("error")) { fin("Has dicho que no. Puedes cerrar esta pestaña."); clearTimeout(corta); return fallo(new Error(q.get("error"))); }
    if (q.get("state") !== estado) { fin("Algo no cuadra. Vuelve a empezar."); return; }
    if (!q.get("code")) return;
    fin("Listo. Ya puedes cerrar esta pestaña y volver a la terminal.");
    clearTimeout(corta);
    listo(q.get("code"));
  });
}).finally(() => servidor.close());

const r = await fetch("https://oauth2.googleapis.com/token", {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({
    client_id: ID,
    client_secret: SECRETO,
    code: codigo,
    code_verifier: verificador,
    grant_type: "authorization_code",
    redirect_uri: vuelta,
  }),
});
const datos = await r.json();
if (!r.ok || !datos.refresh_token) {
  console.error("\nGoogle no ha dado el token:", JSON.stringify(datos, null, 2));
  console.error("\nSi pone 'invalid_grant', suele ser que tu correo no está en 'Usuarios de prueba'.");
  process.exit(1);
}

// Se apunta la fecha para poder avisar antes de que caduque. Aquí no va ningún
// secreto: solo el día en que se dio el permiso.
try {
  mkdirSync(join(AQUI, "canales"), { recursive: true });
  writeFileSync(join(AQUI, "canales", "autorizado.json"),
    JSON.stringify({ fecha: new Date().toISOString() }, null, 2) + "\n");
} catch { /* si no se puede escribir, no pasa nada: solo perdemos el aviso */ }

console.log("\n────────────────────────────────────────────────────────");
console.log("Guarda esto. Es la llave de la subida:\n");
console.log(`YT_REFRESH_TOKEN=${datos.refresh_token}`);
console.log("\nNo lo pegues en un chat ni lo subas al repositorio.");
console.log("────────────────────────────────────────────────────────");
console.log("\nOJO con la caducidad:");
console.log("  Si tu app sigue en modo PRUEBA en la consola de Google, este token");
console.log("  caduca a los 7 DÍAS y habrá que repetir esto. subir.mjs te avisará");
console.log("  a partir del quinto día.");
console.log("  Para que deje de caducar, publica la app (necesita una URL de página");
console.log("  principal y otra de política de privacidad).\n");
