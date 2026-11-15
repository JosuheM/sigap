"use strict";
(() => {
  // ------------------------------------------------------------ utilidades
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (t) => String(t ?? "").replace(/[&<>"']/g,
    (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const nf = new Intl.NumberFormat("es-PE", {maximumFractionDigits: 2});
  const mf = new Intl.NumberFormat("es-PE", {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const kgf = (n) => nf.format(n) + " kg";
  const sol = (n) => "S/ " + mf.format(n);
  const fecha = (s) => (s ? s.slice(8, 10) + "/" + s.slice(5, 7) + "/" + s.slice(0, 4) : "");
  const hora = (s) => (s && s.length > 10 ? s.slice(11, 16) : "");
  const hoy = () => {
    const d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0")
      + "-" + String(d.getDate()).padStart(2, "0");
  };
  const cap = (t) => t.charAt(0).toUpperCase() + t.slice(1);

  const ICONOS = {
    box: "M3 7l9-4 9 4v10l-9 4-9-4V7zM3 7l9 4 9-4M12 11v10",
    users: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2 20c0-3.5 3-6 7-6s7 2.5 7 6M17 5a3 3 0 0 1 0 6M19 14c2 .8 3 2.6 3 5",
    plus: "M12 5v14M5 12h14",
    clip: "M9 4h6v3H9zM7 5.5H6a2 2 0 0 0-2 2V20a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5a2 2 0 0 0-2-2h-1M8 12h8M8 16h5",
    store: "M3 9l2-5h14l2 5v1a3 3 0 0 1-6 0 3 3 0 0 1-6 0 3 3 0 0 1-6 0V9zM5 13v8h14v-8",
    chart: "M4 20V10M10 20V4M16 20v-7M2 20h20",
    leaf: "M5 19C5 10 10 5 20 4c0 10-5 15-14 15M5 19c2-4 5-7 9-9",
    key: "M15 7a4 4 0 1 0-3.4 4L4 18.6V21h3v-2h2v-2h2l2.6-2.6",
    out: "M10 4H5v16h5M15 8l4 4-4 4M19 12H9",
    warn: "M12 3l10 18H2L12 3zM12 10v4.5M12 18h.01",
    x: "M6 6l12 12M18 6L6 18",
  };
  const ic = (n) => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONOS[n]}"/></svg>`;
  const etq = (tipo, texto) => `<span class="etq ${tipo}">${esc(texto)}</span>`;
  const ESTADOS = {pendiente: "Pendiente", confirmado: "Confirmado", despachado: "Despachado", cancelado: "Cancelado"};
  const ROLES = {admin: "Administrador", acopiador: "Acopiador", vendedor: "Vendedor"};

  const dlg = $("#dlg");

  // --------------------------------------------------------------- estado
  let sesion = null;
  let token = 0;
  let filtroPedidos = "todos";
  let ultimoLote = {};
  class ErrorSesion extends Error {}

  const puede = (...roles) => !!sesion && roles.includes(sesion.rol);
  const NAV = [
    {id: "inicio", t: "Inventario", i: "box"},
    {id: "productores", t: "Productores", i: "users"},
    {id: "lotes", t: "Registrar lote", i: "plus", roles: ["admin", "acopiador"]},
    {id: "pedidos", t: "Pedidos", i: "clip"},
    {id: "clientes", t: "Clientes", i: "store", roles: ["admin", "vendedor"]},
    {id: "reportes", t: "Reportes", i: "chart", roles: ["admin", "vendedor"]},
    {id: "productos", t: "Productos", i: "leaf", roles: ["admin"]},
    {id: "usuarios", t: "Usuarios", i: "key", roles: ["admin"]},
  ];

  async function api(ruta, metodo = "GET", cuerpo) {
    let r;
    try {
      r = await fetch("/api" + ruta, {
        method: metodo,
        headers: cuerpo !== undefined ? {"Content-Type": "application/json"} : {},
        body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
      });
    } catch {
      throw new Error("No hay conexión con el servidor. Comprueba que SIGAP siga en ejecución.");
    }
    let datos = null;
    try { datos = await r.json(); } catch { datos = null; }
    if (r.status === 401 && ruta !== "/auth/login") {
      cerrarSesion("Tu sesión terminó. Ingresa de nuevo.");
      throw new ErrorSesion("Sesión terminada");
    }
    if (!r.ok) throw new Error((datos && datos.error) || "No se pudo completar la operación");
    return datos;
  }

  function toast(texto, tipo = "ok") {
    const t = document.createElement("div");
    t.className = "toast" + (tipo === "error" ? " error" : "");
    t.textContent = texto;
    // Un diálogo modal tapa todo lo que no esté dentro de él: el aviso va dentro.
    let host = $("#toasts");
    if (dlg.open) {
      host = $(".toasts", dlg);
      if (!host) { host = document.createElement("div"); host.className = "toasts"; dlg.append(host); }
    }
    host.append(t);
    setTimeout(() => t.remove(), tipo === "error" ? 7000 : 4000);
  }
  const fallo = (ex) => { if (!(ex instanceof ErrorSesion)) toast(ex.message, "error"); };

  // ------------------------------------------------------------- diálogos
  function abrir(titulo, html, ancho = false) {
    dlg.className = ancho ? "ancho" : "";
    dlg.innerHTML = `<div class="dlg-cab"><h2 id="dlg-t">${esc(titulo)}</h2>`
      + `<button type="button" class="icono" data-a="cerrar" aria-label="Cerrar">${ic("x")}</button></div>${html}`;
    if (!dlg.open) dlg.showModal();
    dlg.scrollTop = 0;
  }
  const cerrarDlg = () => { if (dlg.open) dlg.close(); };
  dlg.addEventListener("click", (e) => { if (e.target === dlg) cerrarDlg(); });
  const pie = (ok, extra = "") => `<div class="dlg-pie">${extra}<button type="button" class="btn-sec" data-a="cerrar">Cancelar</button>`
    + `<button type="submit" class="btn">${esc(ok)}</button></div>`;
  const errorForm = '<p class="form-error" role="alert"></p>';

  function enviarForm(form, tarea) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = $("button[type=submit]", form);
      const err = $(".form-error", form);
      if (err) err.textContent = "";
      btn.disabled = true;
      try { await tarea(Object.fromEntries(new FormData(form))); }
      catch (ex) { if (err && !(ex instanceof ErrorSesion)) err.textContent = ex.message; }
      finally { btn.disabled = false; }
    });
  }

  // ------------------------------------------------------ piezas de vista
  const cabecera = (titulo, lead, acciones = "") => `<div class="cabecera"><div><h1 tabindex="-1">${esc(titulo)}</h1>`
    + (lead ? `<p>${esc(lead)}</p>` : "") + `</div><div class="acciones">${acciones}</div></div>`;
  const vacio = (titulo, texto, accion = "") => `<div class="vacio"><strong>${esc(titulo)}</strong>${esc(texto)}<br>${accion}</div>`;
  const tabla = (cab, filas, opc = {}) => `<div class="tabla-wrap"><table aria-label="${esc(opc.nombre || "Datos")}"><thead><tr>`
    + cab.map((c) => `<th${c.n ? ' class="n"' : ""}>${esc(c.t ?? c)}</th>`).join("")
    + "</tr></thead><tbody>" + filas.join("") + "</tbody>" + (opc.pie || "") + "</table></div>";

  function filaStock(x) {
    const escala = Math.max(x.disponible_kg, x.stock_minimo, 1) * 1.2;
    const w = (x.disponible_kg / escala * 100).toFixed(1);
    const m = (x.stock_minimo / escala * 100).toFixed(1);
    const desc = `Disponible ${kgf(x.disponible_kg)}, mínimo ${kgf(x.stock_minimo)}`;
    return `<tr><td><strong>${esc(x.producto)}</strong></td><td class="n">${kgf(x.disponible_kg)}</td>`
      + `<td class="n muted">${kgf(x.stock_minimo)}</td>`
      + `<td><div class="nivel ${x.bajo ? "bajo" : ""}" role="img" aria-label="${esc(desc)}" style="--w:${w}%;--m:${m}%"><i></i><b></b></div></td>`
      + `<td>${x.bajo ? etq("bajo", "Stock bajo") : etq("ok", "Normal")}</td></tr>`;
  }
  const tablaStock = (stock) => tabla(["Producto", {t: "Disponible", n: 1}, {t: "Mínimo", n: 1}, "Nivel", "Estado"],
    stock.map(filaStock), {nombre: "Inventario por producto"});

  // ------------------------------------------------------------ pantallas
  async function vInicio() {
    const [stock, alertas, pedidos] = await Promise.all([api("/stock"), api("/alertas"), api("/pedidos")]);
    const total = stock.reduce((a, x) => a + x.disponible_kg, 0);
    const bajos = stock.filter((x) => x.bajo).length;
    const activos = pedidos.filter((p) => ["pendiente", "confirmado"].includes(p.estado)).length;
    let acc = "";
    if (puede("admin", "acopiador")) acc += `<a class="btn" href="#/lotes">${ic("plus")}Registrar lote</a>`;
    if (puede("admin", "vendedor")) acc += `<button type="button" class="btn" data-a="pedido-nuevo">${ic("plus")}Nuevo pedido</button>`;
    const recientes = alertas.slice().reverse().slice(0, 5);
    const html = cabecera("Inventario", "Lo que hay disponible hoy en el centro de acopio.", acc)
      + `<div class="resumen"><div><span class="r-num">${kgf(total)}</span><span class="r-eti">en inventario</span></div>`
      + `<div class="${bajos ? "alerta" : ""}"><span class="r-num">${bajos}</span><span class="r-eti">${bajos === 1 ? "producto bajo su mínimo" : "productos bajo su mínimo"}</span></div>`
      + `<div><span class="r-num">${activos}</span><span class="r-eti">${activos === 1 ? "pedido por atender" : "pedidos por atender"}</span></div></div>`
      + `<section class="panel"><div class="panel-cab"><h2>Stock por producto</h2><span class="muted">La marca vertical señala el mínimo.</span></div>`
      + (stock.length ? tablaStock(stock) : vacio("Aún no hay productos", "Un administrador debe crearlos en la sección Productos.")) + "</section>"
      + `<section class="panel"><div class="panel-cab"><h2>Alertas recientes</h2></div>`
      + (recientes.length ? '<ul class="lista">' + recientes.map((a) => `<li>${ic("warn")}<span>${esc(a.mensaje)}</span>`
        + `<time>${fecha(a.fecha)} ${hora(a.fecha)}</time></li>`).join("") + "</ul>"
        : vacio("Sin alertas por ahora", "Aparecerán aquí cuando un producto baje de su mínimo.")) + "</section>";
    return {html};
  }

  async function vProductores() {
    const lista = await api("/productores");
    const det = await Promise.all(lista.map((p) => api("/productores/" + p.id)));
    const edita = puede("admin", "acopiador");
    const filas = det.map((p) => {
      const ha = p.parcelas.reduce((a, q) => a + q.area_ha, 0);
      return `<tr><td><strong>${esc(p.codigo)}</strong></td><td>${esc(p.nombre)}</td><td>${esc(p.comunidad)}</td>`
        + `<td>${esc(p.telefono || "—")}</td><td class="n">${p.parcelas.length} · ${nf.format(ha)} ha</td>`
        + `<td>${p.activo ? etq("ok", "Activo") : etq("inactivo", "Inactivo")}</td>`
        + `<td class="acc"><button type="button" class="btn-sec btn-sm" data-a="productor-ver" data-id="${p.id}">${edita ? "Ver y editar" : "Ver"}</button></td></tr>`;
    });
    const html = cabecera("Productores", "Quiénes entregan cosecha y en qué parcelas.",
      edita ? `<button type="button" class="btn" data-a="productor-nuevo">${ic("plus")}Nuevo productor</button>` : "")
      + `<section class="panel">` + (lista.length
        ? tabla(["Código", "Nombre", "Comunidad", "Teléfono", {t: "Parcelas", n: 1}, "Estado", ""], filas, {nombre: "Productores"})
        : vacio("Aún no hay productores", "Registra al primero para poder asociarle parcelas y lotes.",
          edita ? `<button type="button" class="btn" data-a="productor-nuevo">Nuevo productor</button>` : "")) + "</section>";
    return {html, datos: det};
  }

  async function dlgProductorNuevo() {
    const lista = await api("/productores");
    const maximo = lista.reduce((m, p) => Math.max(m, parseInt(p.codigo.slice(2), 10) || 0), 0);
    const sugerido = "P-" + String(maximo + 1).padStart(4, "0");
    abrir("Nuevo productor", `<form class="dlg-form" id="f-prod"><div class="dlg-cuerpo"><div class="campos">`
      + `<label>Código<input name="codigo" required pattern="P-\\d{4}" value="${sugerido}"><span class="ayuda">Formato P-0000. Cada productor tiene un código único.</span></label>`
      + `<label>Nombre completo<input name="nombre" required autocomplete="off"></label>`
      + `<label>Comunidad<input name="comunidad" required autocomplete="off"></label>`
      + `<label>Teléfono<input name="telefono" inputmode="numeric" pattern="\\d{9}" maxlength="9"><span class="ayuda">Opcional. 9 dígitos.</span></label>`
      + `</div>${errorForm}</div>${pie("Guardar productor")}</form>`);
    enviarForm($("#f-prod"), async (d) => {
      const p = await api("/productores", "POST", d);
      cerrarDlg(); toast("Productor guardado"); mostrar();
      dlgProductor(p.id).catch(fallo);
    });
  }

  async function dlgProductor(id) {
    const p = await api("/productores/" + id);
    const edita = puede("admin", "acopiador");
    const parcelas = p.parcelas.length ? tabla(["Parcela", {t: "Área", n: 1}, {t: "Altitud", n: 1}],
      p.parcelas.map((q) => `<tr><td>${esc(q.nombre)}</td><td class="n">${nf.format(q.area_ha)} ha</td><td class="n">${nf.format(q.altitud_msnm)} msnm</td></tr>`),
      {nombre: "Parcelas"}) : `<p class="muted">Este productor aún no tiene parcelas.${edita ? " Agrega la primera abajo." : ""}</p>`;
    const forms = edita ? `<hr><h3>Agregar parcela</h3><form id="f-parcela"><div class="campos">`
      + `<label>Nombre<input name="nombre" required autocomplete="off"></label>`
      + `<label>Área (ha)<input name="area_ha" type="number" min="0.01" step="0.01" required></label>`
      + `<label>Altitud (msnm)<input name="altitud_msnm" type="number" min="1" max="6500" step="1" required></label>`
      + `</div>${errorForm}<button type="submit" class="btn btn-sm">Agregar parcela</button></form>`
      + `<hr><h3>Datos del productor</h3><form id="f-edit"><div class="campos">`
      + `<label>Nombre completo<input name="nombre" required value="${esc(p.nombre)}"></label>`
      + `<label>Comunidad<input name="comunidad" required value="${esc(p.comunidad)}"></label>`
      + `<label>Teléfono<input name="telefono" inputmode="numeric" pattern="\\d{9}" maxlength="9" value="${esc(p.telefono || "")}"></label>`
      + `<label class="check ancho"><input type="checkbox" name="activo" ${p.activo ? "checked" : ""}>Productor activo</label>`
      + `</div>${errorForm}<button type="submit" class="btn btn-sm">Guardar cambios</button></form>` : "";
    abrir(`${p.codigo} · ${p.nombre}`, `<div class="dlg-cuerpo"><p class="meta">${esc(p.comunidad)}${p.telefono ? " · Tel. " + esc(p.telefono) : ""}</p>`
      + `<h3>Parcelas</h3>${parcelas}${forms}</div>`, true);
    if (!edita) return;
    enviarForm($("#f-parcela"), async (d) => {
      await api(`/productores/${id}/parcelas`, "POST", {nombre: d.nombre, area_ha: +d.area_ha, altitud_msnm: +d.altitud_msnm});
      toast("Parcela agregada"); mostrar(); await dlgProductor(id);
    });
    enviarForm($("#f-edit"), async (d) => {
      await api("/productores/" + id, "PUT", {nombre: d.nombre, comunidad: d.comunidad, telefono: d.telefono, activo: d.activo ? 1 : 0});
      toast("Cambios guardados"); mostrar(); await dlgProductor(id);
    });
  }

  async function vLotes() {
    const [prods, pr, stock] = await Promise.all([api("/productos"), api("/productores"), api("/stock")]);
    const det = await Promise.all(pr.map((p) => api("/productores/" + p.id)));
    const conParcelas = det.filter((p) => p.parcelas.length);
    let cuerpo;
    if (!prods.length || !conParcelas.length) {
      cuerpo = vacio("Falta información para registrar un lote",
        !prods.length ? "Un administrador debe crear los productos primero."
          : "Cada lote sale de una parcela. Agrega una parcela a un productor.",
        !prods.length ? "" : '<a class="btn" href="#/productores">Ir a Productores</a>');
    } else {
      const sel = (v, a) => (String(v) === String(a) ? " selected" : "");
      const optProd = prods.map((p) => `<option value="${p.id}"${sel(p.id, ultimoLote.producto_id)}>${esc(p.nombre)}</option>`).join("");
      const optParc = conParcelas.map((p) => `<optgroup label="${esc(p.codigo + " · " + p.nombre + (p.activo ? "" : " (inactivo)"))}">`
        + p.parcelas.map((q) => `<option value="${q.id}"${sel(q.id, ultimoLote.parcela_id)}>${esc(q.nombre)} · ${nf.format(q.area_ha)} ha</option>`).join("")
        + "</optgroup>").join("");
      const cal = ultimoLote.calidad || "A";
      cuerpo = `<form id="f-lote" class="panel-cuerpo"><div class="campos">`
        + `<label>Producto<select name="producto_id" required>${optProd}</select></label>`
        + `<label>Parcela de origen<select name="parcela_id" required>${optParc}</select></label>`
        + `<label>Fecha de cosecha<input name="fecha_cosecha" type="date" required max="${hoy()}" value="${hoy()}"></label>`
        + `<label>Cantidad (kg)<input name="cantidad_kg" type="number" min="0.1" step="0.1" inputmode="decimal" required></label>`
        + `<div class="ancho"><label id="l-cal">Calidad</label><div class="seg" role="radiogroup" aria-labelledby="l-cal">`
        + ["A", "B", "C"].map((c) => `<label><input type="radio" name="calidad" value="${c}"${c === cal ? " checked" : ""}><span>Calidad ${c}</span></label>`).join("")
        + `</div></div></div>${errorForm}<button type="submit" class="btn">${ic("plus")}Registrar lote</button></form>`;
    }
    const html = cabecera("Registrar lote", "Anota cada cosecha que llega. El inventario se actualiza al instante.")
      + `<section class="panel"><div class="panel-cab"><h2>Datos del lote</h2></div>${cuerpo}</section>`
      + `<section class="panel"><div class="panel-cab"><h2>Inventario actual</h2></div>`
      + (stock.length ? tablaStock(stock) : vacio("Aún no hay productos", "")) + "</section>";
    return {html, enlazar: () => {
      const f = $("#f-lote");
      if (!f) return;
      enviarForm(f, async (d) => {
        const r = await api("/lotes", "POST", {producto_id: +d.producto_id, parcela_id: +d.parcela_id,
          fecha_cosecha: d.fecha_cosecha, cantidad_kg: +d.cantidad_kg, calidad: d.calidad});
        ultimoLote = {producto_id: d.producto_id, parcela_id: d.parcela_id, calidad: d.calidad};
        const nombre = (prods.find((p) => p.id === r.producto_id) || {}).nombre || "producto";
        toast(`Lote registrado: ${kgf(r.cantidad_kg)} de ${nombre}`);
        mostrar();
      });
    }};
  }

  // ------------------------------------------------------------- pedidos
  const filaPedido = (p, cli) => {
    const c = cli[p.cliente_id];
    const maneja = puede("admin", "vendedor");
    let acc = `<button type="button" class="btn-sec btn-sm" data-a="pedido-ver" data-id="${p.id}">Ver</button>`;
    if (maneja && p.estado === "pendiente") acc += `<button type="button" class="btn btn-sm" data-a="confirmar" data-id="${p.id}">Confirmar</button>`;
    if (maneja && p.estado === "confirmado") acc += `<button type="button" class="btn btn-sm" data-a="despachar" data-id="${p.id}">Despachar</button>`;
    if (maneja && ["pendiente", "confirmado"].includes(p.estado)) acc += `<button type="button" class="btn-peligro btn-sm" data-a="cancelar" data-id="${p.id}">Cancelar</button>`;
    return `<tr><td><button type="button" class="enlace" data-a="pedido-ver" data-id="${p.id}">N.º ${p.id}</button></td>`
      + `<td>${fecha(p.fecha)}</td><td>${esc(c ? c.razon_social : "Cliente " + p.cliente_id)}</td>`
      + `<td>${etq(p.estado, ESTADOS[p.estado])}</td><td class="n">${sol(p.total)}</td><td class="acc">${acc}</td></tr>`;
  };

  async function vPedidos() {
    const [ped, clis] = await Promise.all([api("/pedidos"), api("/clientes")]);
    const cli = Object.fromEntries(clis.map((c) => [c.id, c]));
    const orden = ped.slice().sort((a, b) => b.id - a.id);
    const cuenta = (e) => (e === "todos" ? orden.length : orden.filter((p) => p.estado === e).length);
    const visibles = filtroPedidos === "todos" ? orden : orden.filter((p) => p.estado === filtroPedidos);
    const chips = ["todos", "pendiente", "confirmado", "despachado", "cancelado"].map((e) =>
      `<button type="button" data-a="filtro" data-id="${e}" aria-pressed="${filtroPedidos === e}">${e === "todos" ? "Todos" : ESTADOS[e]} (${cuenta(e)})</button>`).join("");
    const html = cabecera("Pedidos", "Crea, confirma y despacha. Al confirmar, el stock se descuenta del lote más antiguo.",
      puede("admin", "vendedor") ? `<button type="button" class="btn" data-a="pedido-nuevo">${ic("plus")}Nuevo pedido</button>` : "")
      + (orden.length ? `<div class="filtros" role="group" aria-label="Filtrar por estado">${chips}</div>` : "")
      + `<section class="panel">` + (visibles.length
        ? tabla(["Pedido", "Fecha", "Cliente", "Estado", {t: "Total", n: 1}, ""], visibles.map((p) => filaPedido(p, cli)), {nombre: "Pedidos"})
        : vacio(orden.length ? "No hay pedidos en este estado" : "Aún no hay pedidos",
          orden.length ? "Prueba con otro filtro." : "Crea el primero cuando un cliente lo solicite.",
          !orden.length && puede("admin", "vendedor") ? `<button type="button" class="btn" data-a="pedido-nuevo">Nuevo pedido</button>` : "")) + "</section>";
    return {html};
  }

  async function accionPedido(id, accion) {
    const hecho = {confirmar: "confirmado", despachar: "despachado", cancelar: "cancelado"};
    try {
      await api(`/pedidos/${id}/${accion}`, "POST", {});
      cerrarDlg(); toast(`Pedido N.º ${id} ${hecho[accion]}`); mostrar();
    } catch (ex) { fallo(ex); }
  }

  function dlgCancelar(id) {
    abrir(`Cancelar el pedido N.º ${id}`, `<div class="dlg-cuerpo"><p>Si el pedido ya estaba confirmado, el stock vuelve al inventario. Esta acción no se puede deshacer.</p></div>`
      + `<div class="dlg-pie"><button type="button" class="btn-sec" data-a="cerrar">Mantener pedido</button>`
      + `<button type="button" class="btn" data-a="cancelar-ok" data-id="${id}">Cancelar pedido</button></div>`);
  }

  const htmlTraza = (lotes, nombres) => (lotes.length ? tabla(["Lote", "Producto", "Productor", "Parcela", "Cosecha", "Calidad", {t: "Kg", n: 1}],
    lotes.map((l) => `<tr><td>N.º ${l.lote_id}</td><td>${esc(nombres[l.producto_id] || "")}</td><td>${esc(l.productor)}</td><td>${esc(l.parcela)}</td>`
      + `<td>${fecha(l.fecha_cosecha)}</td><td>${esc(l.calidad)}</td><td class="n">${nf.format(l.kg)}</td></tr>`), {nombre: "Lotes asignados"})
    : '<p class="muted">Este pedido aún no tiene lotes asignados. Se asignan al confirmarlo.</p>');

  async function dlgPedido(id) {
    const [p, clis, prods] = await Promise.all([api("/pedidos/" + id), api("/clientes"), api("/productos")]);
    const c = clis.find((x) => x.id === p.cliente_id);
    const nombres = Object.fromEntries(prods.map((x) => [x.id, x.nombre]));
    const maneja = puede("admin", "vendedor");
    let traza = "";
    if (maneja && ["confirmado", "despachado"].includes(p.estado)) {
      const t = await api("/reportes/trazabilidad/" + id);
      traza = `<h3>De qué lotes salió</h3>${htmlTraza(t.lotes, nombres)}`;
    }
    const items = tabla(["Producto", {t: "Cantidad", n: 1}, {t: "Precio por kg", n: 1}, {t: "Subtotal", n: 1}],
      p.items.map((i) => `<tr><td>${esc(nombres[i.producto_id] || "Producto " + i.producto_id)}</td><td class="n">${kgf(i.cantidad_kg)}</td>`
        + `<td class="n">${sol(i.precio_unit)}</td><td class="n">${sol(i.cantidad_kg * i.precio_unit)}</td></tr>`),
      {nombre: "Productos del pedido", pie: `<tfoot><tr><td colspan="3">Total</td><td class="n">${sol(p.total)}</td></tr></tfoot>`});
    let botones = "";
    if (maneja && p.estado === "pendiente") botones += `<button type="button" class="btn" data-a="confirmar" data-id="${id}">Confirmar pedido</button>`;
    if (maneja && p.estado === "confirmado") botones += `<button type="button" class="btn" data-a="despachar" data-id="${id}">Despachar pedido</button>`;
    if (maneja && ["pendiente", "confirmado"].includes(p.estado)) botones = `<button type="button" class="btn-peligro" data-a="cancelar" data-id="${id}">Cancelar pedido</button>` + botones;
    abrir(`Pedido N.º ${id}`, `<div class="dlg-cuerpo"><p>${etq(p.estado, ESTADOS[p.estado])} <span class="meta">&nbsp;${fecha(p.fecha)} · ${esc(c ? c.razon_social + " (" + c.tipo + ")" : "Cliente " + p.cliente_id)}</span></p>`
      + `<h3>Productos</h3>${items}${traza}</div>`
      + `<div class="dlg-pie"><button type="button" class="btn-sec" data-a="cerrar">Cerrar</button>${botones}</div>`, true);
  }

  async function dlgNuevoPedido() {
    const [cli, prod, stock] = await Promise.all([api("/clientes"), api("/productos"), api("/stock")]);
    if (!cli.length) { toast("Primero registra un cliente en la sección Clientes.", "error"); return; }
    if (!prod.length) { toast("No hay productos en el catálogo.", "error"); return; }
    const disp = Object.fromEntries(stock.map((s) => [s.producto_id, s.disponible_kg]));
    const optCli = cli.map((c) => `<option value="${c.id}" data-tipo="${c.tipo}">${esc(c.razon_social)} (${c.tipo})</option>`).join("");
    const optProd = prod.map((p) => `<option value="${p.id}" data-precio="${p.precio_base}">${esc(p.nombre)} · ${sol(p.precio_base)} por kg</option>`).join("");
    const fila = () => `<div class="item"><label>Producto<select class="i-prod">${optProd}</select></label>`
      + `<label>Cantidad (kg)<input class="i-kg" type="number" min="0.1" step="0.1" inputmode="decimal" required></label>`
      + `<button type="button" class="icono" data-a="item-quitar" aria-label="Quitar producto">${ic("x")}</button><div class="i-prev" aria-live="polite"></div></div>`;
    abrir("Nuevo pedido", `<form class="dlg-form" id="f-ped"><div class="dlg-cuerpo">`
      + `<label>Cliente<select id="p-cli" required>${optCli}</select></label>`
      + `<h3>Productos</h3><div id="items">${fila()}</div>`
      + `<button type="button" class="btn-sec btn-sm" data-a="item-agregar">${ic("plus")}Agregar otro producto</button>`
      + `<div class="total-est"><span>Total estimado</span><span id="total-est">${sol(0)}</span></div>`
      + `<span class="ayuda">Los mayoristas reciben 5 % desde 100 kg y 10 % desde 500 kg. El total final lo calcula el sistema al crear el pedido.</span>`
      + `${errorForm}</div>${pie("Crear pedido")}</form>`, true);
    const form = $("#f-ped");
    const calcular = () => {
      const tipo = $("#p-cli").selectedOptions[0].dataset.tipo;
      let total = 0;
      $$(".item", form).forEach((it) => {
        const o = $(".i-prod", it).selectedOptions[0];
        const kg = parseFloat($(".i-kg", it).value) || 0;
        const pct = tipo === "mayorista" ? (kg >= 500 ? 10 : kg >= 100 ? 5 : 0) : 0;
        const unit = Math.round(parseFloat(o.dataset.precio) * (1 - pct / 100) * 100) / 100;
        const sub = unit * kg;
        total += sub;
        const hay = disp[o.value] ?? 0;
        $(".i-prev", it).innerHTML = (kg > 0 ? `${sol(unit)} por kg${pct ? ` (descuento de ${pct} %)` : ""} · ${sol(sub)} · ` : "")
          + `Disponible: ${kgf(hay)}` + (kg > hay ? ` <span class="alerta">Supera el stock actual: podrás crear el pedido, pero no confirmarlo hasta tener stock.</span>` : "");
      });
      $("#total-est").textContent = sol(total);
    };
    form.addEventListener("input", calcular);
    form.addEventListener("change", calcular);
    form.addEventListener("click", (e) => {
      const b = e.target.closest("[data-a]");
      if (!b) return;
      if (b.dataset.a === "item-agregar") { $("#items").insertAdjacentHTML("beforeend", fila()); calcular(); }
      if (b.dataset.a === "item-quitar") {
        if ($$(".item", form).length > 1) { b.closest(".item").remove(); calcular(); }
        else toast("El pedido necesita al menos un producto.", "error");
      }
    });
    calcular();
    enviarForm(form, async () => {
      const items = $$(".item", form).map((it) => ({producto_id: +$(".i-prod", it).value, cantidad_kg: +$(".i-kg", it).value}));
      const r = await api("/pedidos", "POST", {cliente_id: +$("#p-cli").value, items});
      cerrarDlg(); toast(`Pedido N.º ${r.id} creado`);
      if (ruta() !== "pedidos") location.hash = "#/pedidos"; else mostrar();
    });
  }

  // ------------------------------------------------------------- clientes
  async function vClientes() {
    const lista = await api("/clientes");
    const filas = lista.map((c) => `<tr><td><strong>${esc(c.razon_social)}</strong></td><td>${etq(c.tipo, cap(c.tipo))}</td>`
      + `<td class="muted">${c.tipo === "mayorista" ? "5 % desde 100 kg · 10 % desde 500 kg" : "Sin descuento por volumen"}</td></tr>`);
    const html = cabecera("Clientes", "A quién le vendes. El tipo de cliente define el descuento por volumen.",
      `<button type="button" class="btn" data-a="cliente-nuevo">${ic("plus")}Nuevo cliente</button>`)
      + `<section class="panel">` + (lista.length ? tabla(["Cliente", "Tipo", "Descuento"], filas, {nombre: "Clientes"})
        : vacio("Aún no hay clientes", "Registra el primero para poder crearle pedidos.",
          `<button type="button" class="btn" data-a="cliente-nuevo">Nuevo cliente</button>`)) + "</section>";
    return {html};
  }

  function dlgCliente() {
    abrir("Nuevo cliente", `<form class="dlg-form" id="f-cli"><div class="dlg-cuerpo"><div class="campos">`
      + `<label class="ancho">Razón social o nombre<input name="razon_social" required autocomplete="off"></label>`
      + `<div class="ancho"><label id="l-tipo">Tipo de cliente</label><div class="seg" role="radiogroup" aria-labelledby="l-tipo">`
      + `<label><input type="radio" name="tipo" value="mayorista" checked><span>Mayorista</span></label>`
      + `<label><input type="radio" name="tipo" value="minorista"><span>Minorista</span></label></div>`
      + `<span class="ayuda">Los mayoristas reciben descuento por volumen.</span></div></div>${errorForm}</div>${pie("Guardar cliente")}</form>`);
    enviarForm($("#f-cli"), async (d) => { await api("/clientes", "POST", d); cerrarDlg(); toast("Cliente guardado"); mostrar(); });
  }

  // ------------------------------------------------------------- reportes
  async function vReportes() {
    const v = await api("/reportes/ventas");
    const mayor = Math.max(...v.map((x) => x.monto), 1);
    const kgTot = v.reduce((a, x) => a + x.kg, 0), montoTot = v.reduce((a, x) => a + x.monto, 0);
    const filas = v.map((x) => `<tr><td><strong>${esc(x.producto)}</strong></td><td class="n">${kgf(x.kg)}</td><td class="n">${sol(x.monto)}</td>`
      + `<td style="min-width:160px"><div class="barra" style="--w:${(x.monto / mayor * 100).toFixed(1)}%"></div></td></tr>`);
    const html = cabecera("Reportes", "Qué se vendió y de dónde salió cada kilo.")
      + `<section class="panel"><div class="panel-cab"><h2>Ventas por producto</h2><span class="muted">Incluye pedidos confirmados y despachados.</span></div>`
      + (v.length ? tabla(["Producto", {t: "Kilos vendidos", n: 1}, {t: "Monto", n: 1}, ""], filas, {nombre: "Ventas por producto",
        pie: `<tfoot><tr><td>Total</td><td class="n">${kgf(kgTot)}</td><td class="n">${sol(montoTot)}</td><td></td></tr></tfoot>`})
        : vacio("Aún no hay ventas", "Aparecerán cuando confirmes tu primer pedido.")) + "</section>"
      + `<section class="panel"><div class="panel-cab"><h2>Trazabilidad de un pedido</h2></div><form id="f-traz" class="panel-cuerpo">`
      + `<div class="campos"><label>Número de pedido<input name="id" type="number" min="1" step="1" required></label></div>`
      + `${errorForm}<button type="submit" class="btn btn-sm">Consultar lotes</button></form><div id="traz" class="tabla-wrap"></div></section>`;
    return {html, enlazar: () => {
      enviarForm($("#f-traz"), async (d) => {
        const [t, prods] = await Promise.all([api("/reportes/trazabilidad/" + d.id), api("/productos")]);
        const nombres = Object.fromEntries(prods.map((x) => [x.id, x.nombre]));
        $("#traz").innerHTML = `<div class="panel-cuerpo"><p>Pedido N.º ${t.pedido_id} · ${etq(t.estado, ESTADOS[t.estado])}</p></div>` + htmlTraza(t.lotes, nombres);
      });
    }};
  }

  // ------------------------------------------------------------- productos
  async function vProductos() {
    const [prods, stock] = await Promise.all([api("/productos"), api("/stock")]);
    const disp = Object.fromEntries(stock.map((s) => [s.producto_id, s.disponible_kg]));
    const filas = prods.map((p) => `<tr><td><strong>${esc(p.nombre)}</strong></td><td class="n">${sol(p.precio_base)}</td>`
      + `<td class="n">${kgf(p.stock_minimo)}</td><td class="n">${kgf(disp[p.id] ?? 0)}</td></tr>`);
    const html = cabecera("Productos", "El catálogo de lo que acopia la asociación.",
      `<button type="button" class="btn" data-a="producto-nuevo">${ic("plus")}Nuevo producto</button>`)
      + `<section class="panel">` + (prods.length ? tabla(["Producto", {t: "Precio por kg", n: 1}, {t: "Stock mínimo", n: 1}, {t: "Disponible", n: 1}], filas, {nombre: "Productos"})
        : vacio("Aún no hay productos", "Crea el primero para poder registrar lotes.", `<button type="button" class="btn" data-a="producto-nuevo">Nuevo producto</button>`)) + "</section>";
    return {html};
  }

  function dlgProducto() {
    abrir("Nuevo producto", `<form class="dlg-form" id="f-producto"><div class="dlg-cuerpo"><div class="campos">`
      + `<label class="ancho">Nombre<input name="nombre" required autocomplete="off"></label>`
      + `<label>Precio por kg (S/)<input name="precio_base" type="number" min="0.01" step="0.01" required></label>`
      + `<label>Stock mínimo (kg)<input name="stock_minimo" type="number" min="0" step="1" value="0"><span class="ayuda">Debajo de esta cantidad se genera una alerta.</span></label>`
      + `</div>${errorForm}</div>${pie("Guardar producto")}</form>`);
    enviarForm($("#f-producto"), async (d) => {
      await api("/productos", "POST", {nombre: d.nombre, precio_base: +d.precio_base, stock_minimo: +(d.stock_minimo || 0)});
      cerrarDlg(); toast("Producto guardado"); mostrar();
    });
  }

  // -------------------------------------------------------------- usuarios
  async function vUsuarios() {
    const html = cabecera("Usuarios", "Crea cuentas para el equipo y asigna su rol.")
      + `<section class="panel"><div class="panel-cab"><h2>Nuevo usuario</h2></div><form id="f-user" class="panel-cuerpo"><div class="campos">`
      + `<label>Usuario<input name="username" required autocomplete="off" autocapitalize="none"></label>`
      + `<label>Contraseña<input name="password" type="password" minlength="8" required autocomplete="new-password"><span class="ayuda">Mínimo 8 caracteres.</span></label>`
      + `<label>Rol<select name="rol"><option value="acopiador">Acopiador: registra productores y lotes</option>`
      + `<option value="vendedor">Vendedor: gestiona clientes, pedidos y reportes</option>`
      + `<option value="admin">Administrador: acceso completo</option></select></label>`
      + `</div>${errorForm}<button type="submit" class="btn">Crear usuario</button></form></section>`;
    return {html, enlazar: () => {
      const f = $("#f-user");
      enviarForm(f, async (d) => {
        await api("/usuarios", "POST", d);
        toast(`Usuario ${d.username} creado`); f.reset();
      });
    }};
  }

  // ----------------------------------------------------- navegación y sesión
  const VISTAS = {inicio: vInicio, productores: vProductores, lotes: vLotes, pedidos: vPedidos,
    clientes: vClientes, reportes: vReportes, productos: vProductos, usuarios: vUsuarios};
  const ruta = () => (location.hash.replace(/^#\/?/, "") || "inicio").split("?")[0];

  async function mostrar(enfocar = false) {
    if (!sesion) return;
    const id = ruta();
    const item = NAV.find((n) => n.id === id);
    if (!item || (item.roles && !item.roles.includes(sesion.rol))) { location.replace("#/inicio"); return; }
    $$("#menu a").forEach((a) => (a.getAttribute("href") === "#/" + id ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
    document.title = item.t + " · SIGAP";
    const mio = ++token;
    const v = $("#vista");
    if (!v.innerHTML || enfocar) v.innerHTML = '<p class="cargando">Cargando…</p>';
    try {
      const r = await VISTAS[id]();
      if (mio !== token) return;
      v.innerHTML = r.html;
      if (r.enlazar) r.enlazar();
      if (enfocar) { const h = $("h1", v); if (h) h.focus({preventScroll: true}); }
    } catch (ex) {
      if (ex instanceof ErrorSesion || mio !== token) return;
      v.innerHTML = vacio("No se pudo cargar esta sección", ex.message, '<button type="button" class="btn" data-a="reintentar">Reintentar</button>');
    }
  }

  function iniciar(s) {
    sesion = s;
    try { sessionStorage.setItem("sigap.sesion", JSON.stringify(s)); } catch { /* sin almacenamiento */ }
    $("#login").hidden = true;
    $("#app").hidden = false;
    $("#quien").textContent = s.username;
    $("#rol").textContent = ROLES[s.rol] || s.rol;
    $("#avatar").textContent = s.username.slice(0, 1).toUpperCase();
    $("#menu").innerHTML = NAV.filter((n) => !n.roles || n.roles.includes(s.rol))
      .map((n) => `<a href="#/${n.id}">${ic(n.i)}${esc(n.t)}</a>`).join("");
    if (!location.hash) { location.replace("#/inicio"); return; }
    mostrar(true);
  }

  function cerrarSesion(mensaje = "") {
    sesion = null; token++;
    try { sessionStorage.removeItem("sigap.sesion"); } catch { /* sin almacenamiento */ }
    cerrarDlg();
    $("#app").hidden = true;
    $("#login").hidden = false;
    $("#vista").innerHTML = "";
    $("#msg-login").textContent = mensaje;
    $("#f-login").reset();
    $("#l-user").focus();
    document.title = "SIGAP · Acopio y pedidos";
    history.replaceState(null, "", location.pathname);
  }

  // ------------------------------------------------------------- eventos
  const ACCIONES = {
    "cerrar": cerrarDlg,
    "reintentar": () => mostrar(),
    "filtro": (id) => { filtroPedidos = id; mostrar(); },
    "pedido-ver": (id) => dlgPedido(+id),
    "pedido-nuevo": () => dlgNuevoPedido(),
    "confirmar": (id) => accionPedido(+id, "confirmar"),
    "despachar": (id) => accionPedido(+id, "despachar"),
    "cancelar": (id) => dlgCancelar(+id),
    "cancelar-ok": (id) => accionPedido(+id, "cancelar"),
    "productor-ver": (id) => dlgProductor(+id),
    "productor-nuevo": () => dlgProductorNuevo(),
    "cliente-nuevo": () => dlgCliente(),
    "producto-nuevo": () => dlgProducto(),
  };
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-a]");
    const fn = b && ACCIONES[b.dataset.a];
    if (!fn) return;
    Promise.resolve().then(() => fn(b.dataset.id)).catch(fallo);
  });
  window.addEventListener("hashchange", () => mostrar(true));

  $("#salir").innerHTML = ic("out");
  $("#salir").addEventListener("click", async () => {
    try { await fetch("/api/auth/logout", {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"}); } catch { /* sin conexión */ }
    cerrarSesion();
  });
  $("#ver-clave").addEventListener("click", (e) => {
    const c = $("#l-pass"), ver = c.type === "password";
    c.type = ver ? "text" : "password";
    e.target.textContent = ver ? "Ocultar" : "Mostrar";
  });
  $("#f-login").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("button[type=submit]", e.target), msg = $("#msg-login");
    const d = Object.fromEntries(new FormData(e.target));
    if (!d.username || !d.password) { msg.textContent = "Escribe tu usuario y tu contraseña."; return; }
    msg.textContent = ""; btn.disabled = true;
    try {
      const u = await api("/auth/login", "POST", d);
      iniciar({username: u.username, rol: u.rol});
    } catch (ex) {
      msg.textContent = ex.message === "Credenciales inválidas" ? "Usuario o contraseña incorrectos." : ex.message;
    } finally { btn.disabled = false; }
  });

  // Recupera la sesión si la cookie sigue vigente al recargar la página.
  (async () => {
    let guardada = null;
    try { guardada = JSON.parse(sessionStorage.getItem("sigap.sesion")); } catch { guardada = null; }
    if (!guardada) { $("#l-user").focus(); return; }
    try { await api("/stock"); iniciar(guardada); }
    catch { cerrarSesion(); }
  })();
})();
