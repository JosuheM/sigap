"use strict";
const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"']/g,
  (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));

async function api(ruta, metodo = "GET", cuerpo) {
  const r = await fetch("/api" + ruta, {
    method: metodo,
    headers: cuerpo ? {"Content-Type": "application/json"} : {},
    body: cuerpo ? JSON.stringify(cuerpo) : undefined,
  });
  const datos = await r.json();
  if (!r.ok) throw new Error(datos.error || "Error");
  return datos;
}
function aviso(texto, error = false) {
  const a = $("#aviso");
  a.textContent = texto;
  a.className = error ? "error" : "ok";
}
const tabla = (cab, filas) => "<table><tr>" + cab.map((c) => `<th>${c}</th>`).join("")
  + "</tr>" + filas.map((f) => "<tr>" + f.map((c) => `<td>${c}</td>`).join("") + "</tr>").join("")
  + "</table>";

const vistas = {
  async stock() {
    const s = await api("/stock");
    const al = await api("/alertas");
    $("#t-stock").innerHTML = "<h2>Inventario disponible</h2>" + tabla(
      ["Producto", "Disponible (kg)", "Mínimo (kg)", "Estado"],
      s.map((x) => [esc(x.producto), x.disponible_kg, x.stock_minimo,
        x.bajo ? '<span class="bajo">Stock bajo</span>' : "Normal"]))
      + "<h3>Alertas recientes</h3>" + (al.length ? "<ul>" + al.slice(-5).map(
        (a) => `<li>${esc(a.mensaje)}</li>`).join("") + "</ul>" : "<p>Sin alertas.</p>");
  },
  async productores() {
    const p = await api("/productores");
    $("#t-productores").innerHTML = "<h2>Productores</h2>" + tabla(
      ["Código", "Nombre", "Comunidad", "Activo"],
      p.map((x) => [esc(x.codigo), esc(x.nombre), esc(x.comunidad), x.activo ? "Sí" : "No"]))
      + `<h3>Nuevo productor</h3><form id="f-prod" class="fila">
      <label>Código (P-0000)<input name="codigo" required></label>
      <label>Nombre<input name="nombre" required></label>
      <label>Comunidad<input name="comunidad" required></label>
      <label>Teléfono<input name="telefono"></label><button>Guardar</button></form>`;
    $("#f-prod").onsubmit = (e) => enviar(e, "/productores", "Productor registrado", "productores");
  },
  async lotes() {
    const [prod, pr] = await Promise.all([api("/productos"), api("/productores")]);
    let parcelas = [];
    for (const x of pr) {
      const d = await api("/productores/" + x.id);
      parcelas = parcelas.concat(d.parcelas.map((q) => ({...q, cod: x.codigo})));
    }
    const op = (l, f) => l.map((x) => `<option value="${x.id}">${esc(f(x))}</option>`).join("");
    $("#t-lotes").innerHTML = `<h2>Registrar lote de cosecha</h2><form id="f-lote" class="fila">
      <label>Producto<select name="producto_id">${op(prod, (x) => x.nombre)}</select></label>
      <label>Parcela<select name="parcela_id">${op(parcelas, (x) => x.cod + " – " + x.nombre)}</select></label>
      <label>Fecha de cosecha<input name="fecha_cosecha" type="date" required></label>
      <label>Cantidad (kg)<input name="cantidad_kg" type="number" step="0.1" min="0.1" required></label>
      <label>Calidad<select name="calidad"><option>A</option><option>B</option><option>C</option></select></label>
      <button>Registrar</button></form>`;
    $("#f-lote").onsubmit = (e) => enviar(e, "/lotes", "Lote registrado", "stock");
  },
  async pedidos() {
    const [ped, cli, prod] = await Promise.all([api("/pedidos"), api("/clientes"), api("/productos")]);
    const op = (l, f) => l.map((x) => `<option value="${x.id}">${esc(f(x))}</option>`).join("");
    $("#t-pedidos").innerHTML = "<h2>Pedidos</h2>" + tabla(
      ["N.º", "Fecha", "Estado", "Total (S/)", "Acciones"],
      ped.map((x) => [x.id, x.fecha, x.estado, x.total.toFixed(2),
        (x.estado === "pendiente" ? `<button data-a="confirmar" data-id="${x.id}">Confirmar</button> ` : "")
        + (x.estado === "confirmado" ? `<button data-a="despachar" data-id="${x.id}">Despachar</button> ` : "")
        + (["pendiente", "confirmado"].includes(x.estado) ? `<button data-a="cancelar" data-id="${x.id}">Cancelar</button>` : "")]))
      + `<h3>Nuevo pedido</h3><form id="f-ped" class="fila">
      <label>Cliente<select name="cliente_id">${op(cli, (x) => x.razon_social + " (" + x.tipo + ")")}</select></label>
      <label>Producto<select name="producto_id">${op(prod, (x) => x.nombre)}</select></label>
      <label>Cantidad (kg)<input name="cantidad_kg" type="number" step="0.1" min="0.1" required></label>
      <button>Crear pedido</button></form>`;
    document.querySelectorAll("#t-pedidos [data-a]").forEach((b) => {
      b.onclick = async () => {
        try { await api(`/pedidos/${b.dataset.id}/${b.dataset.a}`, "POST", {}); aviso("Pedido actualizado"); vistas.pedidos(); }
        catch (err) { aviso(err.message, true); }
      };
    });
    $("#f-ped").onsubmit = async (e) => {
      e.preventDefault();
      const f = Object.fromEntries(new FormData(e.target));
      try {
        await api("/pedidos", "POST", {cliente_id: +f.cliente_id,
          items: [{producto_id: +f.producto_id, cantidad_kg: +f.cantidad_kg}]});
        aviso("Pedido creado"); vistas.pedidos();
      } catch (err) { aviso(err.message, true); }
    };
  },
  async reportes() {
    const v = await api("/reportes/ventas");
    $("#t-reportes").innerHTML = "<h2>Ventas por producto</h2>" + (v.length ? tabla(
      ["Producto", "Kg vendidos", "Monto (S/)"], v.map((x) => [esc(x.producto), x.kg, x.monto.toFixed(2)]))
      : "<p>No hay ventas confirmadas.</p>")
      + `<h3>Trazabilidad de un pedido</h3><form id="f-traz" class="fila">
      <label>N.º de pedido<input name="id" type="number" min="1" required></label><button>Consultar</button></form><div id="traz"></div>`;
    $("#f-traz").onsubmit = async (e) => {
      e.preventDefault();
      try {
        const t = await api("/reportes/trazabilidad/" + new FormData(e.target).get("id"));
        $("#traz").innerHTML = tabla(["Lote", "Productor", "Parcela", "Cosecha", "Calidad", "Kg"],
          t.lotes.map((l) => [l.lote_id, esc(l.productor), esc(l.parcela), l.fecha_cosecha, l.calidad, l.kg]));
      } catch (err) { aviso(err.message, true); }
    };
  },
};

async function enviar(e, ruta, ok, vista) {
  e.preventDefault();
  const d = Object.fromEntries(new FormData(e.target));
  for (const k of ["producto_id", "parcela_id", "cantidad_kg"]) if (k in d) d[k] = +d[k];
  try { await api(ruta, "POST", d); aviso(ok); mostrar(vista); }
  catch (err) { aviso(err.message, true); }
}
function mostrar(t) {
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.t === t));
  document.querySelectorAll("#app section").forEach((s) => (s.hidden = s.id !== "t-" + t));
  vistas[t]().catch((err) => aviso(err.message, true));
}
document.querySelectorAll("#tabs button").forEach((b) => (b.onclick = () => { aviso(""); mostrar(b.dataset.t); }));
$("#f-login").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const u = await api("/auth/login", "POST", Object.fromEntries(new FormData(e.target)));
    $("#login").hidden = true; $("#app").hidden = false; $("#sesion").hidden = false;
    $("#quien").textContent = u.username + " (" + u.rol + ")";
    mostrar("stock");
  } catch (err) { $("#msg-login").textContent = err.message; }
};
$("#salir").onclick = async () => { await api("/auth/logout", "POST", {}); location.reload(); };
