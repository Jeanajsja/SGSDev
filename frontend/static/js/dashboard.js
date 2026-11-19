const API_URL = window.location.origin + "/api";
const API_CACHE_TTL_MS = 45000;
let seccionActual = 'dashboard';
let chartInstance = null;
let agendaFecha = null;
let agendaVista = 'semana';
let agendaCache = { salones: [], reservas: [] };
let navegacionId = 0;
const apiGetCache = new Map();

function invalidarCacheApi(prefijo = null) {
    if (!prefijo) {
        apiGetCache.clear();
        return;
    }
    for (const key of [...apiGetCache.keys()]) {
        if (key.includes(prefijo)) apiGetCache.delete(key);
    }
}

const AGENDA_INICIO = 7;
const AGENDA_FIN = 22;
const AGENDA_TRACK_H = 600;
const AGENDA_HEAD_H = 56;
const AGENDA_COLORES = [
    "#0e4a8a",
    "#1a66b8",
    "#7c3aed",
    "#be123c",
    "#0f766e",
    "#c2410c",
    "#0369a1",
    "#4f46e5",
];

async function apiFetch(url, options = {}) {
    const token = sessionStorage.getItem('access_token');
    if (!token) {
        cerrarSesion();
        throw new Error("Sesión no autenticada");
    }

    const method = String(options.method || 'GET').toUpperCase();
    const cacheable = method === 'GET' && !options.bypassCache;
    if (cacheable) {
        const hit = apiGetCache.get(url);
        if (hit && (Date.now() - hit.at) < API_CACHE_TTL_MS) {
            return hit.response.clone();
        }
    }

    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
        cerrarSesion();
        throw new Error("Sesión expirada");
    }
    if (cacheable && response.ok) {
        apiGetCache.set(url, { at: Date.now(), response: response.clone() });
    }
    if (method !== 'GET' && response.ok) {
        invalidarCacheApi('/api/');
    }
    return response;
}

function mensajeSeguroParaUsuario(raw) {
    let texto = raw;
    if (Array.isArray(raw)) {
        texto = raw
            .map((item) => (typeof item === "object" ? item?.msg || "" : String(item || "")))
            .filter(Boolean)
            .join(". ");
    } else if (raw && typeof raw === "object") {
        texto = raw.message || raw.msg || "";
    }
    texto = String(texto || "").trim();
    if (!texto) {
        return "No se pudo completar la operación. Intenta de nuevo.";
    }
    const interno =
        /supabase|postgres|psycopg|sqlalchemy|traceback|db_host|db_port|db_user|sslmode|pooler|hostaddr|connection refused|operationalerror|database|base de datos|relation |column |syntax error|duplicate key|smtp|uvicorn|fastapi|werkzeug|jinja/i;
    if (interno.test(texto)) {
        return "No se pudo completar la operación. Intenta de nuevo.";
    }
    return texto;
}

async function leerRespuestaApi(response) {
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
        throw new Error("El servidor devolvió una respuesta no válida.");
    }

    const result = await response.json();
    if (!response.ok || result?.status === "error") {
        throw new Error(
            mensajeSeguroParaUsuario(
                result?.message || result?.detail || "No se pudo completar la operación. Intenta de nuevo."
            )
        );
    }
    return result;
}

function agregarCelda(fila, texto, clase = "") {
    const celda = document.createElement('td');
    celda.className = clase;
    celda.textContent = texto == null ? "" : String(texto);
    fila.appendChild(celda);
    return celda;
}

function agregarBoton(contenedor, texto, icono, clase, accion) {
    const boton = document.createElement('button');
    boton.type = "button";
    boton.className = clase;
    boton.setAttribute("aria-label", texto);
    if (icono) {
        const icon = document.createElement('i');
        icon.className = icono;
        boton.append(icon);
    }
    boton.append(document.createTextNode(`${icono ? " " : ""}${texto}`));
    boton.addEventListener("click", accion);
    contenedor.appendChild(boton);
    return boton;
}

function mostrarTablaVacia(body, columnas, mensaje, clase = "p-10 text-center text-slate-400 italic") {
    const fila = document.createElement('tr');
    const celda = document.createElement('td');
    celda.colSpan = columnas;
    celda.className = clase;
    celda.textContent = mensaje;
    fila.appendChild(celda);
    body.replaceChildren(fila);
}

document.addEventListener('DOMContentLoaded', () => {
    let user;
    try {
        user = JSON.parse(sessionStorage.getItem('user'));
    } catch {
        user = null;
    }
    if (!user || !sessionStorage.getItem('access_token')) {
        cerrarSesion();
        return;
    }

    document.getElementById('user-display-name').innerText = user.nombre;
    const rolesMap = { 1: 'SUPERADMINISTRADOR', 2: 'ADMINISTRADOR', 3: 'DOCENTE' };
    document.getElementById('user-display-role').innerText = rolesMap[user.id_rol];

    // --- TRANSFORMACIÓN DE INTERFAZ (RBAC) ---
    const rol = parseInt(user.id_rol);
    if (rol === 3) { // DOCENTE: No ve Docentes, Reservas Globales ni Roles
        ['nav-docentes', 'nav-reservas', 'nav-roles'].forEach(id => {
            const el = document.getElementById(id); if(el) el.style.display = 'none';
        });
        document.getElementById('seccion-grafico').style.display = 'none';
    } else if (rol === 2) { // OPERATIVO: No ve Control de Roles
        const el = document.getElementById('nav-roles'); if(el) el.style.display = 'none';
    }

    mostrarSeccion('dashboard');
    precargarCatalogos();
});

function precargarCatalogos() {
    // Calienta cache GET en segundo plano (salones/docentes/reservas) para pestañas siguientes
    Promise.allSettled([
        apiFetch(`${API_URL}/salones`),
        apiFetch(`${API_URL}/docentes`),
        apiFetch(`${API_URL}/reservas`),
    ]).catch(() => {});
}

async function mostrarSeccion(seccion) {
    const requestId = ++navegacionId;
    seccionActual = seccion;
    const user = JSON.parse(sessionStorage.getItem('user'));
    const btn = document.getElementById('btn-accion-principal');
    const tit = document.getElementById('titulo-seccion');
    const esAgenda = seccion === 'reservas_globales';

    document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('sidebar-active'));
    
    // Asignar sidebar active según corresponda
    let sideId = 'nav-' + seccion.split('_')[0];
    document.getElementById(sideId)?.classList.add('sidebar-active');

    // Cambiar layout YA (antes del await) para no mostrar datos de la pestaña anterior
    mostrarVistaAgenda(esAgenda);
    prepararCargaSeccion(esAgenda);

    btn.style.display = 'flex';
    
    if (seccion === 'dashboard') {
        tit.innerText = user.id_rol == 3 ? "Mis Reservas" : "Dashboard General";
        btn.innerHTML = '<i class="fas fa-plus"></i> NUEVA RESERVA';
        btn.onclick = () => prepararModal('reserva');
        await cargarTabla('reservas', requestId);
        if (requestId !== navegacionId) return;
        // Reutiliza /api/reservas ya cacheado por cargarTabla (evita 2da espera)
        initChart();
    } else if (seccion === 'salones') {
        tit.innerText = "Gestión de Salones";
        btn.innerHTML = '<i class="fas fa-plus"></i> REGISTRAR SALÓN';
        btn.onclick = () => prepararModal('salon');
        if (user.id_rol != 1) btn.style.display = 'none'; // US-05: Solo admin puede registrar
        await cargarTabla('salones', requestId);
    } else if (seccion === 'reservas_globales') {
        tit.innerText = "Agenda de Salones";
        btn.innerHTML = '<i class="fas fa-plus"></i> NUEVA RESERVA';
        btn.onclick = () => prepararModal('reserva');
        btn.style.display = 'flex';
        await cargarAgendaSalones(requestId);
    } else if (seccion === 'docentes') {
        tit.innerText = "Listado de Docentes";
        btn.innerHTML = '<i class="fas fa-plus"></i> REGISTRAR DOCENTE';
        btn.onclick = () => prepararModal('docente');
        if (user.id_rol != 1) btn.style.display = 'none'; // US-13: Solo admin
        await cargarTabla('docentes', requestId);
    } else if (seccion === 'roles') {
        tit.innerText = "Control de Roles";
        if (esSuperadminAncla(user)) {
            btn.style.display = 'flex';
            btn.innerHTML = '<i class="fas fa-plus"></i> NUEVO SUPERADMINISTRADOR';
            btn.onclick = () => prepararModal('superadmin');
        } else {
            btn.style.display = 'none';
        }
        await cargarTabla('roles', requestId);
    }
}

function prepararCargaSeccion(esAgenda) {
    const head = document.getElementById('tabla-head');
    const body = document.getElementById('tabla-body');
    const board = document.getElementById('agenda-board');
    const stat = document.getElementById('stat-reservas');
    if (head) head.innerHTML = '';
    if (body) mostrarTablaVacia(body, 5, "Cargando...");
    if (board) board.innerHTML = '<div class="p-16 text-center text-slate-400 font-bold">Cargando agenda...</div>';
    if (stat) stat.innerText = '--';
    if (!esAgenda && board) board.replaceChildren();
}

function mostrarVistaAgenda(activa) {
    const agenda = document.getElementById('seccion-agenda');
    const tabla = document.getElementById('seccion-tabla');
    const stats = document.getElementById('seccion-stats');
    const grafico = document.getElementById('seccion-grafico');
    const user = JSON.parse(sessionStorage.getItem('user') || '{}');
    const setHidden = (el, hide) => {
        if (!el) return;
        el.classList.toggle('hidden', hide);
        if (hide) el.style.display = 'none';
        else el.style.removeProperty('display');
    };
    setHidden(agenda, !activa);
    setHidden(tabla, activa);
    setHidden(stats, activa);
    // Docente nunca ve el gráfico; no reactivar su display al salir de agenda
    setHidden(grafico, activa || parseInt(user.id_rol) === 3);
}

function fechaLocalISO(date = new Date()) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

function parseFechaISO(iso) {
    const [y, m, d] = String(iso || '').split('-').map(Number);
    return new Date(y, (m || 1) - 1, d || 1);
}

function inicioSemana(fecha) {
    const d = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
    const day = d.getDay();
    const diff = day === 0 ? -6 : 1 - day; // lunes como inicio
    d.setDate(d.getDate() + diff);
    return d;
}

function formatearRangoAgenda(iso, vista) {
    const fecha = parseFechaISO(iso);
    if (vista === 'mes') {
        return fecha.toLocaleDateString('es-CO', { month: 'long', year: 'numeric' });
    }
    if (vista === 'semana') {
        const ini = inicioSemana(fecha);
        const fin = new Date(ini);
        fin.setDate(ini.getDate() + 6);
        const mismoMes = ini.getMonth() === fin.getMonth();
        const a = ini.toLocaleDateString('es-CO', { day: 'numeric', month: mismoMes ? undefined : 'short' });
        const b = fin.toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' });
        return `${a} – ${b}`;
    }
    return fecha.toLocaleDateString('es-CO', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
    });
}

function minutosDesdeInicio(hora) {
    const [h, m] = String(hora || '00:00').substring(0, 5).split(':').map(Number);
    return (h * 60 + m) - (AGENDA_INICIO * 60);
}

function intervaloReserva(r) {
    const totalMin = (AGENDA_FIN - AGENDA_INICIO) * 60;
    const ini = String(r.hora_inicio || '00:00').substring(0, 5);
    const fin = String(r.hora_fin || '00:00').substring(0, 5);
    let start = Math.max(0, minutosDesdeInicio(ini));
    let end = minutosDesdeInicio(fin);
    if (end <= start) end = start + 60;
    end = Math.min(totalMin, end);
    return { start, end, totalMin };
}

/** Asigna columnas solo a reservas que se solapan de verdad (evita el efecto “hora montada”). */
function asignarColumnasSolapes(reservas) {
    const items = reservas.map((r, order) => {
        const { start, end } = intervaloReserva(r);
        return { r, order, start, end, col: 0, cols: 1 };
    }).sort((a, b) => a.start - b.start || a.end - b.end || a.order - b.order);

    const active = [];
    items.forEach((item) => {
        for (let i = active.length - 1; i >= 0; i -= 1) {
            if (active[i].end <= item.start) active.splice(i, 1);
        }
        const used = new Set(active.map((a) => a.col));
        let col = 0;
        while (used.has(col)) col += 1;
        item.col = col;
        active.push(item);
        const groupCols = Math.max(1, ...active.map((a) => a.col + 1));
        active.forEach((a) => {
            a.cols = Math.max(a.cols, groupCols);
        });
        item.cols = Math.max(item.cols, groupCols);
    });

    // Propaga el ancho del grupo a todos los miembros solapados
    items.forEach((item) => {
        const peers = items.filter(
            (o) => o !== item && o.start < item.end && o.end > item.start
        );
        const maxCols = Math.max(item.cols, ...peers.map((p) => p.cols), item.col + 1);
        item.cols = maxCols;
        peers.forEach((p) => {
            p.cols = Math.max(p.cols, maxCols);
        });
    });

    return items.sort((a, b) => a.order - b.order);
}

function etiquetaReservaAgenda(r) {
    const idClase = r.id_clase != null ? r.id_clase : r.id_docente;
    const docente = (r.docente || '').trim() || 'Docente';
    const clase = idClase != null ? `Clase #${idClase}` : 'Clase';
    return { idClase, docente, clase, texto: `${docente} · ${clase}` };
}

function colorAgenda(clave) {
    const texto = String(clave || '');
    let hash = 0;
    for (let i = 0; i < texto.length; i += 1) {
        hash = (hash + texto.charCodeAt(i) * (i + 1)) % AGENDA_COLORES.length;
    }
    return AGENDA_COLORES[hash];
}

function nombreSalonAgenda(idSalon) {
    const salon = (agendaCache.salones || []).find((s) => Number(s.id_salon) === Number(idSalon));
    return salon?.nombre || `Salón ${idSalon}`;
}

function reservasActivas() {
    return (agendaCache.reservas || []).filter((r) => String(r.estado || '').toLowerCase() !== 'cancelada');
}

function reservasEnRango(desdeISO, hastaISO) {
    return reservasActivas().filter((r) => {
        const fecha = String(r.fecha || '').substring(0, 10);
        return fecha >= desdeISO && fecha <= hastaISO;
    });
}

function sincronizarBotonesVistaAgenda() {
    ['dia', 'semana', 'mes'].forEach((vista) => {
        const btn = document.getElementById(`agenda-vista-${vista}`);
        if (!btn) return;
        btn.classList.toggle('agenda-view-btn-active', agendaVista === vista);
    });
}

function cambiarVistaAgenda(vista) {
    if (!['dia', 'semana', 'mes'].includes(vista)) return;
    agendaVista = vista;
    sincronizarBotonesVistaAgenda();
    actualizarEtiquetaAgenda();
    renderCalendarioAgenda();
}

function actualizarEtiquetaAgenda() {
    const label = document.getElementById('agenda-fecha-label');
    if (label && agendaFecha) {
        label.textContent = formatearRangoAgenda(agendaFecha, agendaVista);
    }
}

function irAgendaHoy() {
    agendaFecha = fechaLocalISO(new Date());
    const input = document.getElementById('agenda-fecha');
    if (input) input.value = agendaFecha;
    actualizarEtiquetaAgenda();
    renderCalendarioAgenda();
}

function cambiarPeriodoAgenda(delta) {
    const base = agendaFecha || fechaLocalISO(new Date());
    const fecha = parseFechaISO(base);
    if (agendaVista === 'mes') fecha.setMonth(fecha.getMonth() + delta);
    else if (agendaVista === 'semana') fecha.setDate(fecha.getDate() + (delta * 7));
    else fecha.setDate(fecha.getDate() + delta);
    agendaFecha = fechaLocalISO(fecha);
    const input = document.getElementById('agenda-fecha');
    if (input) input.value = agendaFecha;
    actualizarEtiquetaAgenda();
    renderCalendarioAgenda();
}

function abrirReservaDesdeAgenda(r) {
    const user = JSON.parse(sessionStorage.getItem('user') || '{}');
    if (user.id_rol != 1 && user.id_rol != 2) return;
    const ini = String(r.hora_inicio || '00:00').substring(0, 5);
    const fin = String(r.hora_fin || '00:00').substring(0, 5);
    editarReserva(r.id_reserva, r.fecha, ini, fin, r.id_salon, r.id_docente);
}

function irAgendaDia(iso) {
    agendaFecha = iso;
    agendaVista = 'dia';
    const input = document.getElementById('agenda-fecha');
    if (input) input.value = iso;
    sincronizarBotonesVistaAgenda();
    actualizarEtiquetaAgenda();
    renderCalendarioAgenda();
}

async function cargarAgendaSalones(requestId = navegacionId, forzar = false) {
    const board = document.getElementById('agenda-board');
    const input = document.getElementById('agenda-fecha');
    if (!board || !input) return;
    if (requestId !== navegacionId || seccionActual !== 'reservas_globales') return;

    if (!input.value) {
        input.value = agendaFecha || fechaLocalISO(new Date());
    }
    agendaFecha = input.value;
    sincronizarBotonesVistaAgenda();
    actualizarEtiquetaAgenda();

    // Si ya hay datos en memoria, pinta al instante y refresca en segundo plano
    const tieneCacheLocal = (agendaCache.salones || []).length > 0;
    if (!tieneCacheLocal) {
        board.innerHTML = '<div class="p-16 text-center text-slate-400 font-bold">Cargando calendario...</div>';
    } else {
        renderCalendarioAgenda();
    }

    try {
        if (forzar) {
            invalidarCacheApi('/api/salones');
            invalidarCacheApi('/api/reservas');
        }
        const [resSalones, resReservas] = await Promise.all([
            apiFetch(`${API_URL}/salones`),
            apiFetch(`${API_URL}/reservas`),
        ]);
        if (requestId !== navegacionId || seccionActual !== 'reservas_globales') return;

        const salonesData = await leerRespuestaApi(resSalones);
        const reservasData = await leerRespuestaApi(resReservas);
        if (requestId !== navegacionId || seccionActual !== 'reservas_globales') return;

        agendaCache.salones = (salonesData.data || [])
            .slice()
            .sort((a, b) => String(a.nombre).localeCompare(String(b.nombre), 'es', { numeric: true }));
        agendaCache.reservas = reservasData.data || [];

        const activas = reservasActivas();
        const stat = document.getElementById('stat-reservas');
        if (stat) stat.innerText = String(activas.length);
        renderCalendarioAgenda();
    } catch (e) {
        if (requestId !== navegacionId || seccionActual !== 'reservas_globales') return;
        if (!tieneCacheLocal) {
            board.innerHTML = `<div class="p-16 text-center text-red-500 font-bold">${e.message || 'No se pudo cargar la agenda'}</div>`;
        }
    }
}

function renderCalendarioAgenda() {
    const board = document.getElementById('agenda-board');
    if (!board || seccionActual !== 'reservas_globales') return;
    sincronizarBotonesVistaAgenda();
    actualizarEtiquetaAgenda();
    if (agendaVista === 'mes') renderAgendaMes(board);
    else if (agendaVista === 'semana') renderAgendaSemana(board);
    else renderAgendaDia(board);
}

function crearEventoAgenda(r, compacto = false) {
    const ini = String(r.hora_inicio || '00:00').substring(0, 5);
    const fin = String(r.hora_fin || '00:00').substring(0, 5);
    const salon = r.salon || nombreSalonAgenda(r.id_salon);
    const meta = etiquetaReservaAgenda(r);
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = compacto ? 'cal-event cal-event-compact' : 'cal-event';
    btn.style.cssText = `border:0;border-radius:8px;color:#fff;text-align:left;padding:${compacto ? '4px 6px' : '6px 8px'};background:${colorAgenda(meta.texto || salon)};box-shadow:0 6px 14px rgba(7,24,51,.16);cursor:pointer;overflow:hidden;`;
    btn.title = `${ini}-${fin} · ${meta.docente} · ${meta.clase} · ${salon}`;
    if (compacto) {
        btn.style.fontSize = '10px';
        btn.style.fontWeight = '700';
        btn.style.lineHeight = '1.25';
        btn.innerHTML = `<strong style="display:block;font-size:10px;font-weight:800">${ini}-${fin}</strong><span style="display:block;opacity:.95">${meta.docente}</span><span style="display:block;opacity:.9">${meta.clase} · ${salon}</span>`;
    } else {
        btn.innerHTML = `<strong style="display:block;font-size:11px;font-weight:800">${ini} - ${fin}</strong><span style="display:block;font-size:10px;margin-top:2px;opacity:.95">${meta.docente}</span><span style="display:block;font-size:10px;opacity:.92">${meta.clase}</span><span style="display:block;font-size:10px;opacity:.92">${salon}</span>`;
    }
    btn.onclick = (e) => {
        e.stopPropagation();
        abrirReservaDesdeAgenda(r);
    };
    return btn;
}

function crearTrackHoras() {
    const totalMin = (AGENDA_FIN - AGENDA_INICIO) * 60;
    const hours = document.createElement('div');
    hours.className = 'cal-hours';
    // overflow visible: el 07:00 no debe quedar recortado por el encabezado
    hours.style.cssText = `position:relative;height:${AGENDA_TRACK_H}px;background:#f8fafc;border-right:1px solid #e8eef6;overflow:visible;`;
    for (let h = AGENDA_INICIO; h < AGENDA_FIN; h += 1) {
        const mark = document.createElement('div');
        mark.className = 'cal-hour-label';
        // Empuja la etiqueta hacia dentro de la franja (evita que 07:00 quede bajo "Hora")
        const topPx = ((h - AGENDA_INICIO) * 60 / totalMin) * AGENDA_TRACK_H + 6;
        mark.style.cssText = `position:absolute;left:0;right:0;z-index:1;padding:0 8px;font-size:10px;font-weight:800;color:#5c6b80;line-height:1.2;top:${topPx}px;`;
        mark.textContent = `${String(h).padStart(2, '0')}:00`;
        hours.appendChild(mark);
    }
    return hours;
}

function pintarLineasHora(track) {
    const totalMin = (AGENDA_FIN - AGENDA_INICIO) * 60;
    for (let h = AGENDA_INICIO; h < AGENDA_FIN; h += 1) {
        const line = document.createElement('div');
        line.className = 'cal-hour-line';
        line.style.cssText = `position:absolute;left:0;right:0;border-top:1px solid #eef2f7;top:${((h - AGENDA_INICIO) * 60 / totalMin) * AGENDA_TRACK_H}px;`;
        track.appendChild(line);
    }
}

function posicionEventoEnTrack(event, r, layout = { col: 0, cols: 1 }) {
    const { start, end, totalMin } = intervaloReserva(r);
    const gap = 2;
    const top = (start / totalMin) * AGENDA_TRACK_H + gap;
    const height = Math.max(28, ((end - start) / totalMin) * AGENDA_TRACK_H - gap * 2);
    const cols = Math.max(1, layout.cols || 1);
    const col = Math.max(0, layout.col || 0);
    const pad = 4;
    const widthPct = 100 / cols;
    event.classList.add('cal-event-abs');
    event.style.position = 'absolute';
    event.style.zIndex = String(2 + col);
    event.style.top = `${top}px`;
    event.style.height = `${height}px`;
    event.style.left = `calc(${col * widthPct}% + ${pad}px)`;
    event.style.width = `calc(${widthPct}% - ${pad * 2}px)`;
    event.style.right = 'auto';
}

function renderAgendaDia(board) {
    const reservas = reservasEnRango(agendaFecha, agendaFecha)
        .slice()
        .sort((a, b) => String(a.hora_inicio).localeCompare(String(b.hora_inicio)));

    const wrap = document.createElement('div');
    wrap.className = 'cal-time-view';
    wrap.style.cssText = 'display:grid;grid-template-columns:72px 1fr;min-height:656px;background:#fff;';

    const hoursWrap = document.createElement('div');
    hoursWrap.style.cssText = 'display:flex;flex-direction:column;min-width:0;';
    const hoursHead = document.createElement('div');
    hoursHead.className = 'cal-week-corner';
    hoursHead.style.cssText = `height:${AGENDA_HEAD_H}px;display:flex;align-items:center;justify-content:center;background:#071833;color:#fff;font-size:11px;font-weight:800;`;
    hoursHead.textContent = 'Hora';
    hoursWrap.appendChild(hoursHead);
    hoursWrap.appendChild(crearTrackHoras());
    wrap.appendChild(hoursWrap);

    const dayCol = document.createElement('div');
    dayCol.style.cssText = 'display:flex;flex-direction:column;min-width:0;';
    const head = document.createElement('div');
    head.className = 'cal-day-head';
    head.style.cssText = `height:${AGENDA_HEAD_H}px;display:flex;align-items:center;justify-content:center;background:#071833;color:#fff;font-size:12px;font-weight:800;text-transform:capitalize;`;
    head.textContent = formatearRangoAgenda(agendaFecha, 'dia');
    dayCol.appendChild(head);

    const track = document.createElement('div');
    track.className = 'cal-day-track';
    track.style.cssText = `position:relative;height:${AGENDA_TRACK_H}px;border-left:1px solid #e8eef6;`;
    pintarLineasHora(track);

    if (!reservas.length) {
        const empty = document.createElement('div');
        empty.className = 'cal-empty';
        empty.style.cssText = 'position:absolute;inset:24px;display:flex;align-items:center;justify-content:center;border:1px dashed #dbe3ef;border-radius:16px;color:#94a3b8;font-size:12px;font-weight:700;';
        empty.textContent = 'No hay reservas este día';
        track.appendChild(empty);
    } else {
        asignarColumnasSolapes(reservas).forEach(({ r, col, cols }) => {
            const event = crearEventoAgenda(r);
            posicionEventoEnTrack(event, r, { col, cols });
            track.appendChild(event);
        });
    }
    dayCol.appendChild(track);
    wrap.appendChild(dayCol);
    board.replaceChildren(wrap);
}

function renderAgendaSemana(board) {
    const lunes = inicioSemana(parseFechaISO(agendaFecha));
    const dias = Array.from({ length: 7 }, (_, i) => {
        const d = new Date(lunes);
        d.setDate(lunes.getDate() + i);
        return d;
    });
    const desde = fechaLocalISO(dias[0]);
    const hasta = fechaLocalISO(dias[6]);
    const reservas = reservasEnRango(desde, hasta);
    const hoyISO = fechaLocalISO(new Date());

    const wrap = document.createElement('div');
    wrap.className = 'cal-week-view';
    wrap.style.cssText = `display:grid;grid-template-columns:72px repeat(7, minmax(120px, 1fr));grid-template-rows:${AGENDA_HEAD_H}px ${AGENDA_TRACK_H}px;min-width:900px;background:#fff;`;

    // Columna izquierda completa (encabezado + horas) para que 07:00 nunca quede bajo "Hora"
    const hoursCol = document.createElement('div');
    hoursCol.className = 'cal-week-hours-col';
    hoursCol.style.cssText = `grid-column:1;grid-row:1 / span 2;display:flex;flex-direction:column;background:#f8fafc;border-right:1px solid #e8eef6;`;
    const corner = document.createElement('div');
    corner.className = 'cal-week-corner';
    corner.style.cssText = `flex:0 0 ${AGENDA_HEAD_H}px;height:${AGENDA_HEAD_H}px;background:#071833;color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;`;
    corner.textContent = 'Hora';
    hoursCol.appendChild(corner);
    const hours = crearTrackHoras();
    hours.className = 'cal-week-hours';
    hoursCol.appendChild(hours);
    wrap.appendChild(hoursCol);

    dias.forEach((d, idx) => {
        const iso = fechaLocalISO(d);
        const head = document.createElement('button');
        head.type = 'button';
        head.className = `cal-week-head${iso === hoyISO ? ' cal-today' : ''}`;
        head.style.cssText = `grid-column:${idx + 2};grid-row:1;height:${AGENDA_HEAD_H}px;width:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;background:${iso === hoyISO ? '#0e4a8a' : '#071833'};color:${iso === hoyISO ? '#edb309' : '#fff'};border:0;border-left:1px solid #0c274f;cursor:pointer;`;
        head.innerHTML = `<span style="font-size:10px;text-transform:uppercase;opacity:.85">${d.toLocaleDateString('es-CO', { weekday: 'short' })}</span><strong style="font-size:16px">${d.getDate()}</strong>`;
        head.onclick = () => irAgendaDia(iso);
        wrap.appendChild(head);
    });

    dias.forEach((d, idx) => {
        const iso = fechaLocalISO(d);
        const col = document.createElement('div');
        col.className = `cal-week-col${iso === hoyISO ? ' cal-today-col' : ''}`;
        col.style.cssText = `grid-column:${idx + 2};grid-row:2;position:relative;height:${AGENDA_TRACK_H}px;border-left:1px solid #e8eef6;${iso === hoyISO ? 'box-shadow:inset 0 0 0 2px rgba(237,179,9,.45);' : ''}`;
        pintarLineasHora(col);
        const delDia = reservas
            .filter((r) => String(r.fecha || '').substring(0, 10) === iso)
            .sort((a, b) => String(a.hora_inicio).localeCompare(String(b.hora_inicio)));
        asignarColumnasSolapes(delDia).forEach(({ r, col: colIdx, cols }) => {
            const event = crearEventoAgenda(r, true);
            posicionEventoEnTrack(event, r, { col: colIdx, cols });
            col.appendChild(event);
        });
        wrap.appendChild(col);
    });

    board.replaceChildren(wrap);
}

function renderAgendaMes(board) {
    const base = parseFechaISO(agendaFecha);
    const first = new Date(base.getFullYear(), base.getMonth(), 1);
    const start = inicioSemana(first);
    const hoyISO = fechaLocalISO(new Date());
    const mesActual = base.getMonth();
    const celdas = [];
    for (let i = 0; i < 42; i += 1) {
        const d = new Date(start);
        d.setDate(start.getDate() + i);
        celdas.push(d);
    }
    const desde = fechaLocalISO(celdas[0]);
    const hasta = fechaLocalISO(celdas[41]);
    const reservas = reservasEnRango(desde, hasta);

    const wrap = document.createElement('div');
    wrap.className = 'cal-month-view';
    wrap.style.cssText = 'padding:12px;';

    const weekdays = document.createElement('div');
    weekdays.className = 'cal-month-weekdays';
    weekdays.style.cssText = 'display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px;margin-bottom:8px;';
    ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].forEach((n) => {
        const el = document.createElement('div');
        el.style.cssText = 'text-align:center;font-size:11px;font-weight:800;color:#5c6b80;text-transform:uppercase;padding:8px 0;';
        el.textContent = n;
        weekdays.appendChild(el);
    });
    wrap.appendChild(weekdays);

    const grid = document.createElement('div');
    grid.className = 'cal-month-grid';
    grid.style.cssText = 'display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px;';
    celdas.forEach((d) => {
        const iso = fechaLocalISO(d);
        const fuera = d.getMonth() !== mesActual;
        const cell = document.createElement('button');
        cell.type = 'button';
        cell.className = 'cal-month-cell';
        cell.style.cssText = `min-height:110px;border:1px solid #e8eef6;border-radius:14px;background:${fuera ? '#f8fafc' : '#fff'};opacity:${fuera ? '.72' : '1'};padding:8px;text-align:left;cursor:pointer;${iso === hoyISO ? 'box-shadow:inset 0 0 0 2px rgba(237,179,9,.55);' : ''}`;
        cell.onclick = () => irAgendaDia(iso);

        const num = document.createElement('div');
        num.style.cssText = 'font-size:12px;font-weight:800;color:#12213a;margin-bottom:6px;';
        num.textContent = String(d.getDate());
        cell.appendChild(num);

        const list = document.createElement('div');
        list.style.cssText = 'display:flex;flex-direction:column;gap:4px;';
        const delDia = reservas
            .filter((r) => String(r.fecha || '').substring(0, 10) === iso)
            .sort((a, b) => String(a.hora_inicio).localeCompare(String(b.hora_inicio)));
        delDia.slice(0, 3).forEach((r) => list.appendChild(crearEventoAgenda(r, true)));
        if (delDia.length > 3) {
            const more = document.createElement('span');
            more.style.cssText = 'font-size:10px;font-weight:700;color:#0e4a8a;';
            more.textContent = `+${delDia.length - 3} más`;
            list.appendChild(more);
        }
        cell.appendChild(list);
        grid.appendChild(cell);
    });
    wrap.appendChild(grid);
    board.replaceChildren(wrap);
}

async function cargarTabla(tipo, requestId = navegacionId) {
    const user = JSON.parse(sessionStorage.getItem('user'));
    const head = document.getElementById('tabla-head');
    const body = document.getElementById('tabla-body');
    if (requestId !== navegacionId) return;
    head.innerHTML = '';
    mostrarTablaVacia(body, 5, "Cargando...");

    try {
        let fetchUrl = `${API_URL}/${tipo}`;
        if (tipo === 'reservas_globales') {
            fetchUrl = `${API_URL}/reservas`;
        }
        if (tipo === 'roles') {
            fetchUrl = `${API_URL}/usuarios`;
        }
        
        const res = await apiFetch(fetchUrl);
        const result = await leerRespuestaApi(res);
        if (requestId !== navegacionId) return;
        body.replaceChildren();

        if (tipo === 'reservas' || tipo === 'reservas_globales') {
            head.innerHTML = '<tr><th class="px-6 py-4">Docente</th><th class="px-6 py-4">ID clase</th><th class="px-6 py-4">Salón</th><th class="px-6 py-4">Fecha</th><th class="px-6 py-4">Horario</th><th class="px-6 py-4">Acción</th></tr>';
            const data = result.data || [];
            agendaCache.reservas = data;

            if (data.length === 0) {
                mostrarTablaVacia(body, 6, "No hay reservas registradas");
            } else {
                data.forEach(r => {
                    const h_ini = r.hora_inicio ? r.hora_inicio.substring(0,5) : '--:--';
                    const h_fin = r.hora_fin ? r.hora_fin.substring(0,5) : '--:--';
                    const idClase = r.id_clase || r.id_docente;
                    const row = document.createElement('tr');
                    row.className = "border-b hover:bg-slate-50/50 transition";
                    agregarCelda(row, r.docente || '—', "px-6 py-4 font-bold text-slate-700");
                    agregarCelda(row, idClase != null ? `#${idClase}` : '--', "px-6 py-4 text-slate-600 font-mono");
                    agregarCelda(row, r.salon, "px-6 py-4 text-slate-600");
                    agregarCelda(row, r.fecha, "px-6 py-4 text-slate-600");
                    const horario = agregarCelda(row, "", "px-6 py-4 text-slate-600");
                    const horarioBadge = document.createElement('span');
                    horarioBadge.className = "bg-ucc-plata text-ucc-azul px-2.5 py-1 rounded-lg text-xs font-bold";
                    horarioBadge.textContent = `${h_ini} - ${h_fin}`;
                    horario.appendChild(horarioBadge);
                    const acciones = agregarCelda(row, "", "px-6 py-4");
                    const canEdit = user.id_rol == 1 || user.id_rol == 2;
                    if (canEdit) {
                        agregarBoton(
                            acciones,
                            "Editar",
                            "fas fa-edit",
                            "text-ucc-azul font-bold hover:underline mr-4",
                            () => editarReserva(r.id_reserva, r.fecha, h_ini, h_fin, r.id_salon, idClase)
                        );
                    }
                    agregarBoton(
                        acciones,
                        "Cancelar",
                        "fas fa-trash-alt",
                        "text-red-500 font-bold hover:underline",
                        () => cancelarReserva(r.id_reserva)
                    );
                    body.appendChild(row);
                });
            }
            if (tipo === 'reservas') {
                document.getElementById('stat-reservas').innerText = data.length;
            }
        } else if (tipo === 'salones') {
            head.innerHTML = '<tr><th class="px-6 py-4">Nombre</th><th class="px-6 py-4">Capacidad</th><th class="px-6 py-4">Ubicación</th><th class="px-6 py-4">Estado</th><th class="px-6 py-4">Acción</th></tr>';
            
            if (!result.data || result.data.length === 0) {
                mostrarTablaVacia(body, 5, "No hay salones registrados");
            } else {
                result.data.forEach(s => {
                    const row = document.createElement('tr');
                    row.className = "border-b hover:bg-slate-50/50 transition";
                    agregarCelda(row, s.nombre, "px-6 py-4 font-bold text-slate-700");
                    agregarCelda(row, `${s.capacidad} personas`, "px-6 py-4 text-slate-600");
                    agregarCelda(row, s.ubicacion, "px-6 py-4 text-slate-600");
                    const estado = agregarCelda(row, "", "px-6 py-4");
                    const badge = document.createElement('span');
                    badge.className = `${s.estado === 'disponible' ? 'bg-ucc-plata text-ucc-azul' : 'bg-[#fdf6de] text-[#8a6a05]'} px-2.5 py-1 rounded-lg text-xs font-bold uppercase`;
                    badge.textContent = s.estado == null ? "" : String(s.estado);
                    estado.appendChild(badge);
                    const acciones = agregarCelda(row, "", "px-6 py-4");
                    if (user.id_rol == 1) {
                        agregarBoton(
                            acciones,
                            "Editar",
                            "fas fa-edit",
                            "text-ucc-azul font-bold hover:underline",
                            () => editarSalon(s.id_salon, s.nombre, s.capacidad, s.ubicacion)
                        );
                    } else {
                        acciones.textContent = "-";
                    }
                    body.appendChild(row);
                });
            }
        } else if (tipo === 'docentes') {
            head.innerHTML = '<tr><th class="px-6 py-4">ID Docente</th><th class="px-6 py-4">Nombre</th><th class="px-6 py-4">Correo</th><th class="px-6 py-4">Perfil</th></tr>';
            
            const dataList = result.data || [];
            if (dataList.length === 0) {
                mostrarTablaVacia(body, 4, "No hay docentes registrados");
            } else {
                dataList.forEach(d => {
                    const row = document.createElement('tr');
                    row.className = "border-b hover:bg-slate-50/50 transition";
                    agregarCelda(row, `#${d.id_docente}`, "px-6 py-4 text-slate-500 font-mono");
                    agregarCelda(row, d.nombre, "px-6 py-4 font-bold text-slate-700");
                    agregarCelda(row, d.correo, "px-6 py-4 text-slate-600");
                    const perfil = agregarCelda(row, "", "px-6 py-4");
                    const badge = document.createElement('span');
                    badge.className = "bg-ucc-plata text-ucc-azul px-2.5 py-1 rounded-lg text-xs font-bold uppercase";
                    badge.textContent = "Docente";
                    perfil.appendChild(badge);
                    body.appendChild(row);
                });
            }
        } else if (tipo === 'roles') {
            head.innerHTML = '<tr><th class="px-6 py-4">Usuario</th><th class="px-6 py-4">Correo</th><th class="px-6 py-4">Rol</th><th class="px-6 py-4">Acción</th></tr>';
            const dataList = Array.isArray(result) ? result : (result.data || []);
            if (dataList.length === 0) {
                mostrarTablaVacia(body, 4, "No hay cuentas registradas");
            } else {
                dataList.forEach(cuenta => {
                    const esAncla = (cuenta.email || "").toLowerCase() === "lfpaez30@ucatolica.edu.co";
                    const puedeAsignarSuper = esSuperadminAncla(user);
                    const row = document.createElement('tr');
                    row.className = "border-b hover:bg-slate-50/50 transition";
                    agregarCelda(row, cuenta.nombre, "px-6 py-4 font-bold text-slate-700");
                    agregarCelda(row, cuenta.email, "px-6 py-4 text-slate-600");
                    const rol = agregarCelda(row, "", "px-6 py-4");
                    const badge = document.createElement('span');
                    badge.className = "bg-ucc-plata text-ucc-azul px-2.5 py-1 rounded-lg text-xs font-bold uppercase";
                    badge.textContent = nombreRol(cuenta.id_rol);
                    rol.appendChild(badge);
                    const acciones = agregarCelda(row, "", "px-6 py-4");
                    if (esAncla) {
                        const nota = document.createElement('span');
                        nota.className = "text-slate-400 text-xs font-bold uppercase";
                        nota.textContent = "Cuenta ancla";
                        acciones.appendChild(nota);
                    } else {
                        const controles = document.createElement('div');
                        controles.className = "flex items-center gap-3";
                        const selector = document.createElement('select');
                        selector.id = `rol-${cuenta.id_usuario}`;
                        selector.className = "p-2 border border-slate-200 rounded-xl text-xs font-bold outline-none focus:ring-2 focus:ring-ucc-dorado";
                        if (puedeAsignarSuper || cuenta.id_rol == 1) {
                            selector.add(new Option("Superadministrador", "1"));
                        }
                        selector.add(new Option("Administrador", "2"));
                        selector.add(new Option("Docente", "3"));
                        selector.value = String(cuenta.id_rol);
                        controles.appendChild(selector);
                        agregarBoton(
                            controles,
                            "Aplicar",
                            "",
                            "text-ucc-azul font-bold hover:underline text-xs uppercase",
                            () => cambiarRol(cuenta.id_usuario)
                        );
                        agregarBoton(
                            controles,
                            "Eliminar",
                            "fas fa-trash-alt",
                            "text-red-500 font-bold hover:underline text-xs uppercase",
                            () => eliminarCuenta(cuenta.id_usuario)
                        );
                        acciones.appendChild(controles);
                    }
                    body.appendChild(row);
                });
            }
        }
    } catch (e) {
        if (requestId !== navegacionId) return;
        mostrarTablaVacia(
            body,
            5,
            e.message || "No fue posible cargar los datos.",
            "p-10 text-center text-red-500 font-bold"
        );
    }
}

async function llenarSelectSalones(selectId, selectedId = null) {
    const select = document.getElementById(selectId);
    if (!select) return;
    try {
        const res = await apiFetch(`${API_URL}/salones`);
        const result = await leerRespuestaApi(res);
        const salones = (result.data || []).filter(
            (s) => (s.estado || "").toLowerCase() === "disponible"
        );
        salones.sort((a, b) => String(a.nombre).localeCompare(String(b.nombre), "es", { numeric: true }));
        select.innerHTML = '<option value="">Selecciona un salón o laboratorio</option>';
        if (!salones.length) {
            select.innerHTML = '<option value="">No hay salones disponibles</option>';
            return;
        }
        salones.forEach((s) => {
            const option = document.createElement("option");
            option.value = String(s.id_salon);
            option.textContent = `${s.nombre} (cupo ${s.capacidad})`;
            if (selectedId != null && String(selectedId) === String(s.id_salon)) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    } catch (e) {
        select.innerHTML = `<option value="">${e.message || "No se pudieron cargar salones"}</option>`;
    }
}

async function prepararModal(tipo, editData = null) {
    const user = JSON.parse(sessionStorage.getItem('user'));
    const campos = document.getElementById('campos-dinamicos');
    campos.innerHTML = "";

    if (tipo === 'reserva') {
        document.getElementById('modal-titulo').innerText = editData ? "Editar Reserva" : "Nueva Reserva";
        campos.innerHTML = `
            ${editData ? '<input type="hidden" id="m-reserva-id">' : ''}
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">Fecha</label>
                <input type="date" id="m-fecha" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div class="space-y-1">
                    <label class="text-xs font-bold text-slate-400 uppercase">Hora Inicio</label>
                    <input type="time" id="m-inicio" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
                </div>
                <div class="space-y-1">
                    <label class="text-xs font-bold text-slate-400 uppercase">Hora Fin</label>
                    <input type="time" id="m-fin" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
                </div>
            </div>
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">Salón / Laboratorio</label>
                <select id="m-salon" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition bg-white" required>
                    <option value="">Cargando salones...</option>
                </select>
            </div>
            ${user.id_rol != 3 ? `
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">ID clase</label>
                <input type="number" id="m-clase" placeholder="ID clase" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
            ` : ''}
        `;
        if (editData) {
            document.getElementById('m-reserva-id').value = String(editData.id_reserva);
            document.getElementById('m-fecha').value = editData.fecha;
            document.getElementById('m-inicio').value = editData.hora_inicio;
            document.getElementById('m-fin').value = editData.hora_fin;
            if (user.id_rol != 3) {
                document.getElementById('m-clase').value = String(editData.id_clase || editData.id_docente);
            }
        }
        document.getElementById('modalMaestro').classList.remove('hidden');
        document.getElementById('formMaestro').onsubmit = (e) => enviarFormulario(e, editData ? 'editar_reserva' : 'reserva');
        await llenarSelectSalones('m-salon', editData ? editData.id_salon : null);
    } else if (tipo === 'salon') {
        document.getElementById('modal-titulo').innerText = "Registrar Salón";
        campos.innerHTML = `
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">Nombre</label>
                <input type="text" id="m-nom" placeholder="Ej: Laboratorio 402" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">Capacidad</label>
                <input type="number" id="m-cap" placeholder="Ej: 40" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">Ubicación</label>
                <input type="text" id="m-ub" placeholder="Ej: Torre B - Piso 4" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
        `;
        document.getElementById('modalMaestro').classList.remove('hidden');
        document.getElementById('formMaestro').onsubmit = (e) => enviarFormulario(e, 'salon');
    } else if (tipo === 'docente') {
        document.getElementById('modal-titulo').innerText = "Registrar Docente";
        campos.innerHTML = `
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">Nombre Completo</label>
                <input type="text" id="m-nom-doc" placeholder="Ej: Ing. María Pérez" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">Correo Institucional</label>
                <input type="email" id="m-corr-doc" placeholder="maria.perez@ucatolica.edu.co" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">Contraseña inicial</label>
                <input type="password" id="m-pass-doc" minlength="12" maxlength="128" autocomplete="new-password" placeholder="Mínimo 12 caracteres" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
        `;
        document.getElementById('modalMaestro').classList.remove('hidden');
        document.getElementById('formMaestro').onsubmit = (e) => enviarFormulario(e, 'docente');
    } else if (tipo === 'superadmin') {
        if (!esSuperadminAncla(user)) {
            alert("Solo el superadministrador ancla puede crear otro superadministrador");
            return;
        }
        document.getElementById('modal-titulo').innerText = "Nuevo superadministrador";
        campos.innerHTML = `
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">Nombre Completo</label>
                <input type="text" id="m-nom-super" placeholder="Nombre" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">Correo</label>
                <input type="email" id="m-email-super" placeholder="correo@ucatolica.edu.co" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
            <div class="space-y-1">
                <label class="text-xs font-bold text-slate-400 uppercase">Contraseña</label>
                <input type="password" id="m-pass-super" minlength="12" maxlength="128" autocomplete="new-password" placeholder="Mínimo 12 caracteres" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
        `;
        document.getElementById('modalMaestro').classList.remove('hidden');
        document.getElementById('formMaestro').onsubmit = (e) => enviarFormulario(e, 'superadmin');
    }
}

function esSuperadminAncla(user) {
    return (user.email || "").toLowerCase() === "lfpaez30@ucatolica.edu.co";
}

function nombreRol(idRol) {
    const nombres = { 1: "Superadministrador", 2: "Administrador", 3: "Docente" };
    return nombres[idRol] || "Sin rol";
}

async function cambiarRol(idUsuario) {
    const user = JSON.parse(sessionStorage.getItem('user'));
    if (parseInt(user.id_rol) !== 1) {
        alert("Solo un superadministrador puede cambiar el rol");
        return;
    }
    const select = document.getElementById(`rol-${idUsuario}`);
    try {
        const res = await apiFetch(`${API_URL}/usuarios/${idUsuario}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id_rol: parseInt(select.value, 10) })
        });
        const result = await leerRespuestaApi(res);
        alert(result.message || "Rol actualizado");
        mostrarSeccion(seccionActual);
    } catch (e) {
        alert(e.message || "Error al cambiar el rol");
    }
}

async function eliminarCuenta(idUsuario) {
    const user = JSON.parse(sessionStorage.getItem('user'));
    if (parseInt(user.id_rol) !== 1) {
        alert("Solo un superadministrador puede eliminar cuentas");
        return;
    }
    if (!confirm("¿Seguro que quieres eliminar esta cuenta?")) return;
    try {
        const res = await apiFetch(`${API_URL}/usuarios/${idUsuario}`, {
            method: "DELETE"
        });
        const result = await leerRespuestaApi(res);
        alert(result.message || "Cuenta eliminada");
        mostrarSeccion(seccionActual);
    } catch (e) {
        alert(e.message || "Error al eliminar la cuenta");
    }
}

function editarSalon(id, nombre, capacidad, ubicacion) {
    const campos = document.getElementById('campos-dinamicos');
    document.getElementById('modal-titulo').innerText = "Editar Salón";
    campos.innerHTML = `
        <input type="hidden" id="m-id-edit">
        <div class="space-y-1">
            <label class="text-xs font-bold text-slate-400 uppercase">Nombre</label>
            <input type="text" id="m-nom-edit" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
        </div>
        <div class="space-y-1">
            <label class="text-xs font-bold text-slate-400 uppercase">Capacidad</label>
            <input type="number" id="m-cap-edit" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
        </div>
        <div class="space-y-1">
            <label class="text-xs font-bold text-slate-400 uppercase">Ubicación</label>
            <input type="text" id="m-ub-edit" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
        </div>
    `;
    document.getElementById('m-id-edit').value = String(id);
    document.getElementById('m-nom-edit').value = nombre;
    document.getElementById('m-cap-edit').value = String(capacidad);
    document.getElementById('m-ub-edit').value = ubicacion;
    document.getElementById('modalMaestro').classList.remove('hidden');
    document.getElementById('formMaestro').onsubmit = (e) => enviarFormulario(e, 'editar_salon');
}

function editarReserva(id_reserva, fecha, hora_inicio, hora_fin, id_salon, id_clase) {
    prepararModal('reserva', { id_reserva, fecha, hora_inicio, hora_fin, id_salon, id_clase, id_docente: id_clase });
}

function minutosDeHora(hora) {
    const [h, m] = String(hora || '00:00').substring(0, 5).split(':').map(Number);
    return (h * 60) + m;
}

function validarDuracionClase(horaInicio, horaFin) {
    const duracion = minutosDeHora(horaFin) - minutosDeHora(horaInicio);
    if (duracion <= 0) {
        return "No es posible realizar la reserva: la hora de fin debe ser mayor que la de inicio";
    }
    if (duracion > 120) {
        return "No es posible realizar la reserva: una clase no puede durar más de 2 horas";
    }
    return null;
}

function validarTraslapeLocal({ fecha, hora_inicio, hora_fin, id_salon, id_clase, excluirId = null }) {
    const ini = minutosDeHora(hora_inicio);
    const fin = minutosDeHora(hora_fin);
    const fechaISO = String(fecha || '').substring(0, 10);
    const reservas = [...(agendaCache.reservas || [])];
    for (const r of reservas) {
        if (excluirId != null && Number(r.id_reserva) === Number(excluirId)) continue;
        if (String(r.estado || '').toLowerCase() === 'cancelada') continue;
        if (String(r.fecha || '').substring(0, 10) !== fechaISO) continue;
        const rIni = minutosDeHora(r.hora_inicio);
        const rFin = minutosDeHora(r.hora_fin);
        if (!(rIni < fin && rFin > ini)) continue;
        const idDoc = r.id_clase != null ? r.id_clase : r.id_docente;
        if (Number(idDoc) === Number(id_clase)) {
            return "No es posible realizar la reserva: el docente ya tiene una clase en ese horario (las horas no pueden traslaparse)";
        }
        // Cualquier clase en ese horario (aunque sea otra sala) bloquea la reserva.
        return "No es posible realizar la reserva: ya hay una clase en ese horario (las horas no pueden traslaparse)";
    }
    return null;
}

async function enviarFormulario(e, tipo) {
    e.preventDefault();
    const user = JSON.parse(sessionStorage.getItem('user'));
    let data = {};
    let endpoint = `${API_URL}/${tipo}s`;
    let method = 'POST';
    
    if (tipo === 'reserva' || tipo === 'editar_reserva') {
        const id_clase_val = user.id_rol == 3 ? user.id_usuario : document.getElementById('m-clase').value;
        const hora_inicio = document.getElementById('m-inicio').value;
        const hora_fin = document.getElementById('m-fin').value;
        const errorClase = validarDuracionClase(hora_inicio, hora_fin);
        if (errorClase) {
            alert(errorClase);
            return;
        }
        const fecha = document.getElementById('m-fecha').value;
        const id_salon = parseInt(document.getElementById('m-salon').value);
        const id_clase = parseInt(id_clase_val);
        const id_reserva = tipo === 'editar_reserva'
            ? document.getElementById('m-reserva-id').value
            : null;
        const errorTraslape = validarTraslapeLocal({
            fecha,
            hora_inicio,
            hora_fin,
            id_salon,
            id_clase,
            excluirId: id_reserva,
        });
        if (errorTraslape) {
            alert(errorTraslape);
            return;
        }
        data = {
            fecha,
            hora_inicio,
            hora_fin,
            id_salon,
            id_clase,
        };
        if (tipo === 'editar_reserva') {
            endpoint = `${API_URL}/reservas/${id_reserva}`;
            method = 'PUT';
        }
    } else if (tipo === 'salon') {
        data = { 
            nombre: document.getElementById('m-nom').value, 
            capacidad: parseInt(document.getElementById('m-cap').value), 
            ubicacion: document.getElementById('m-ub').value 
        };
        endpoint = `${API_URL}/salones`;
    } else if (tipo === 'editar_salon') {
        const salonId = document.getElementById('m-id-edit').value;
        data = { 
            nombre: document.getElementById('m-nom-edit').value, 
            capacidad: parseInt(document.getElementById('m-cap-edit').value), 
            ubicacion: document.getElementById('m-ub-edit').value 
        };
        endpoint = `${API_URL}/salones/${salonId}`;
        method = 'PUT';
    } else if (tipo === 'docente') {
        data = {
            nombre: document.getElementById('m-nom-doc').value,
            correo: document.getElementById('m-corr-doc').value,
            password: document.getElementById('m-pass-doc').value
        };
    } else if (tipo === 'superadmin') {
        data = {
            nombre: document.getElementById('m-nom-super').value,
            email: document.getElementById('m-email-super').value,
            password: document.getElementById('m-pass-super').value,
            id_rol: 1
        };
        endpoint = `${API_URL}/usuarios`;
    }
    
    try {
        const res = await apiFetch(endpoint, {
            method: method, 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify(data) 
        });
        const result = await leerRespuestaApi(res);
        alert(mensajeSeguroParaUsuario(result.message || "Operación realizada con éxito"));
        cerrarModal();
        mostrarSeccion(seccionActual);
    } catch (err) {
        alert(mensajeSeguroParaUsuario(err.message || "No se pudo completar la operación. Intenta de nuevo."));
    }
}

async function cancelarReserva(id) {
    if (confirm("¿Estás seguro de que deseas cancelar esta reserva? (US-26 / US-29)")) {
        try {
            const res = await apiFetch(`${API_URL}/reservas/${id}`, {
                method: 'DELETE'
            });
            await leerRespuestaApi(res);
            alert("Reserva cancelada correctamente");
            mostrarSeccion(seccionActual);
        } catch (e) {
            alert(e.message || "Error de conexión al intentar cancelar la reserva");
        }
    }
}

function cerrarModal() { document.getElementById('modalMaestro').classList.add('hidden'); }
function cerrarSesion() { sessionStorage.clear(); window.location.href = 'login.html'; }
function recargarSeccionActual() { mostrarSeccion(seccionActual); }

async function initChart() {
    const user = JSON.parse(sessionStorage.getItem('user'));
    if (user.id_rol == 3) return; // Docente no tiene permisos del gráfico

    try {
        const res = await apiFetch(`${API_URL}/reservas`);
        const result = await leerRespuestaApi(res);
        if (!result.data) return;

        // Agrupar reservas por salón
        const salonesMap = {};
        result.data.forEach(r => {
            if (r.estado !== 'cancelada') {
                salonesMap[r.salon] = (salonesMap[r.salon] || 0) + 1;
            }
        });

        const labels = Object.keys(salonesMap);
        const data = Object.values(salonesMap);

        const canvas = document.getElementById('reservasChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (chartInstance) {
            chartInstance.destroy();
        }

        chartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Reservas Activas por Salón',
                    data: data,
                    backgroundColor: 'rgba(14, 74, 138, 0.75)',
                    borderColor: '#edb309',
                    borderWidth: 2,
                    borderRadius: 12,
                    barPercentage: 0.5,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#071833',
                        titleColor: '#edb309',
                        bodyColor: '#fff',
                        padding: 12,
                        cornerRadius: 8,
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#5c6b80', font: { weight: 'bold' } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: '#e8eef6' },
                        ticks: { 
                            color: '#5c6b80', 
                            stepSize: 1,
                            font: { weight: 'bold' }
                        }
                    }
                }
            }
        });
    } catch (e) {
        console.error("Error al graficar reservas:", e);
    }
}