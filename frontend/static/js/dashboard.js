const API_URL = window.location.origin + "/api";
let seccionActual = 'dashboard';
let chartInstance = null;

async function apiFetch(url, options = {}) {
    const token = sessionStorage.getItem('access_token');
    if (!token) {
        cerrarSesion();
        throw new Error("Sesión no autenticada");
    }

    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
        cerrarSesion();
        throw new Error("Sesión expirada");
    }
    return response;
}

async function leerRespuestaApi(response) {
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
        throw new Error("El servidor devolvió una respuesta no válida.");
    }

    const result = await response.json();
    if (!response.ok || result?.status === "error") {
        throw new Error(
            result?.message || result?.detail || "La operación no se pudo completar."
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
});

async function mostrarSeccion(seccion) {
    seccionActual = seccion;
    const user = JSON.parse(sessionStorage.getItem('user'));
    const btn = document.getElementById('btn-accion-principal');
    const tit = document.getElementById('titulo-seccion');

    document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('sidebar-active'));
    
    // Asignar sidebar active según corresponda
    let sideId = 'nav-' + seccion.split('_')[0];
    document.getElementById(sideId)?.classList.add('sidebar-active');

    btn.style.display = 'flex';
    
    if (seccion === 'dashboard') {
        tit.innerText = user.id_rol == 3 ? "Mis Reservas" : "Dashboard General";
        btn.innerHTML = '<i class="fas fa-plus"></i> NUEVA RESERVA';
        btn.onclick = () => prepararModal('reserva');
        await cargarTabla('reservas');
        initChart();
    } else if (seccion === 'salones') {
        tit.innerText = "Gestión de Salones";
        btn.innerHTML = '<i class="fas fa-plus"></i> REGISTRAR SALÓN';
        btn.onclick = () => prepararModal('salon');
        if (user.id_rol != 1) btn.style.display = 'none'; // US-05: Solo admin puede registrar
        await cargarTabla('salones');
    } else if (seccion === 'reservas_globales') {
        tit.innerText = "Reservas Globales";
        btn.style.display = 'none'; // No se crean desde este panel global
        await cargarTabla('reservas_globales');
    } else if (seccion === 'docentes') {
        tit.innerText = "Listado de Docentes";
        btn.innerHTML = '<i class="fas fa-plus"></i> REGISTRAR DOCENTE';
        btn.onclick = () => prepararModal('docente');
        if (user.id_rol != 1) btn.style.display = 'none'; // US-13: Solo admin
        await cargarTabla('docentes');
    } else if (seccion === 'roles') {
        tit.innerText = "Control de Roles";
        if (esSuperadminAncla(user)) {
            btn.style.display = 'flex';
            btn.innerHTML = '<i class="fas fa-plus"></i> NUEVO SUPERADMINISTRADOR';
            btn.onclick = () => prepararModal('superadmin');
        } else {
            btn.style.display = 'none';
        }
        await cargarTabla('roles');
    }
}

async function cargarTabla(tipo) {
    const user = JSON.parse(sessionStorage.getItem('user'));
    const head = document.getElementById('tabla-head');
    const body = document.getElementById('tabla-body');
    mostrarTablaVacia(body, 5, "Sincronizando con Supabase...");

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
        body.replaceChildren();

        if (tipo === 'reservas' || tipo === 'reservas_globales') {
            head.innerHTML = '<tr><th class="px-6 py-4">Docente</th><th class="px-6 py-4">Salón</th><th class="px-6 py-4">Fecha</th><th class="px-6 py-4">Horario</th><th class="px-6 py-4">Acción</th></tr>';
            const data = result.data || [];

            if (data.length === 0) {
                mostrarTablaVacia(body, 5, "No hay reservas registradas");
            } else {
                data.forEach(r => {
                    const h_ini = r.hora_inicio ? r.hora_inicio.substring(0,5) : '--:--';
                    const h_fin = r.hora_fin ? r.hora_fin.substring(0,5) : '--:--';
                    const row = document.createElement('tr');
                    row.className = "border-b hover:bg-slate-50/50 transition";
                    agregarCelda(row, r.docente, "px-6 py-4 font-bold text-slate-700");
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
                            () => editarReserva(r.id_reserva, r.fecha, h_ini, h_fin, r.id_salon, r.id_docente)
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
                <label class="text-xs font-bold text-slate-400 uppercase">ID del Docente</label>
                <input type="number" id="m-docente" placeholder="ID del Docente" class="w-full p-3 border border-slate-200 rounded-2xl outline-none focus:ring-2 focus:ring-ucc-dorado transition" required>
            </div>
            ` : ''}
        `;
        if (editData) {
            document.getElementById('m-reserva-id').value = String(editData.id_reserva);
            document.getElementById('m-fecha').value = editData.fecha;
            document.getElementById('m-inicio').value = editData.hora_inicio;
            document.getElementById('m-fin').value = editData.hora_fin;
            if (user.id_rol != 3) {
                document.getElementById('m-docente').value = String(editData.id_docente);
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

function editarReserva(id_reserva, fecha, hora_inicio, hora_fin, id_salon, id_docente) {
    prepararModal('reserva', { id_reserva, fecha, hora_inicio, hora_fin, id_salon, id_docente });
}

async function enviarFormulario(e, tipo) {
    e.preventDefault();
    const user = JSON.parse(sessionStorage.getItem('user'));
    let data = {};
    let endpoint = `${API_URL}/${tipo}s`;
    let method = 'POST';
    
    if (tipo === 'reserva') {
        const id_docente_val = user.id_rol == 3 ? user.id_usuario : document.getElementById('m-docente').value;
        data = { 
            fecha: document.getElementById('m-fecha').value, 
            hora_inicio: document.getElementById('m-inicio').value, 
            hora_fin: document.getElementById('m-fin').value,
            id_salon: parseInt(document.getElementById('m-salon').value), 
            id_docente: parseInt(id_docente_val)
        };
    } else if (tipo === 'editar_reserva') {
        const id_reserva = document.getElementById('m-reserva-id').value;
        const id_docente_val = user.id_rol == 3 ? user.id_usuario : document.getElementById('m-docente').value;
        data = { 
            fecha: document.getElementById('m-fecha').value, 
            hora_inicio: document.getElementById('m-inicio').value, 
            hora_fin: document.getElementById('m-fin').value,
            id_salon: parseInt(document.getElementById('m-salon').value), 
            id_docente: parseInt(id_docente_val)
        };
        endpoint = `${API_URL}/reservas/${id_reserva}`;
        method = 'PUT';
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
        alert(result.message || "Operación realizada con éxito");
        cerrarModal();
        mostrarSeccion(seccionActual);
    } catch (err) {
        alert(err.message || "Error al enviar el formulario.");
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