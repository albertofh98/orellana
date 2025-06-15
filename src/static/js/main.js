document.addEventListener('DOMContentLoaded', function () {
    // Elementos del DOM para búsqueda avanzada y modales
    const searchForm = document.getElementById('searchForm');
    const resultadosContainer = document.getElementById('resultadosContainer');
    const resultadosList = document.getElementById('resultadosList');
    const resultadosInfo = document.getElementById('resultadosInfo');
    const paginacionUl = document.getElementById('paginacion');
    const ultimasConvocatoriasList = document.getElementById('ultimasConvocatoriasList');
    
    let convocatoriaModalInstance = null;
    if (document.getElementById('convocatoriaModal')) {
        convocatoriaModalInstance = new bootstrap.Modal(document.getElementById('convocatoriaModal'));
    }
    const convocatoriaModalTitle = document.getElementById('convocatoriaModalTitle');
    const convocatoriaModalBody = document.getElementById('convocatoriaModalBody');

    // Elementos del DOM para el chat
    const chatInput = document.getElementById('chatInput');
    const sendChatButton = document.getElementById('sendChat');
    const chatMessagesContainer = document.getElementById('chatMessages');

    // --- Identificador único para la sesión de chat del cliente (Thread ID) ---
    let chatThreadId = localStorage.getItem('chatThreadId');
    if (!chatThreadId) {
        if (window.crypto && window.crypto.randomUUID) {
            chatThreadId = crypto.randomUUID(); // Genera un UUID v4
            localStorage.setItem('chatThreadId', chatThreadId);
        } else {
            // Fallback simple si crypto.randomUUID no está disponible (navegadores muy antiguos o contexto no seguro)
            chatThreadId = 'fallback-thread-id-' + Date.now() + Math.random().toString(36).substring(2, 15);
            localStorage.setItem('chatThreadId', chatThreadId);
            console.warn("crypto.randomUUID no disponible, usando fallback para chatThreadId.");
        }
    }
    console.log("Chat Thread ID:", chatThreadId);


    // --- Funciones de Chat ---
    function addMessageToChat(content, type, isLoading = false) {
        const messageWrapperDiv = document.createElement('div');
        messageWrapperDiv.classList.add('message', type);

        const contentWrapperDiv = document.createElement('div');
        contentWrapperDiv.classList.add('message-content');

        if (isLoading) {
            contentWrapperDiv.innerHTML = '<div class="spinner-border spinner-border-sm text-light" role="status"><span class="visually-hidden">Pensando...</span></div>';
            messageWrapperDiv.id = 'loading-message'; // Para poder quitarlo luego
        } else {
            // Usar marked.js para renderizar Markdown si es una respuesta del sistema.
            // Asegurarse de que marked está cargado (lo está, según el HTML).
            try {
                contentWrapperDiv.innerHTML = type === 'system' ? marked.parse(content || "") : (content || "");
            } catch (e) {
                console.error("Error al parsear Markdown con marked.js:", e);
                contentWrapperDiv.textContent = content || ""; // Fallback a texto plano
            }
        }
        
        messageWrapperDiv.appendChild(contentWrapperDiv);
        if (chatMessagesContainer) {
            chatMessagesContainer.appendChild(messageWrapperDiv);
            chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
        }
        return contentWrapperDiv; // Devolver el div de contenido para el streaming
    }

    async function handleChatSubmit() {
        if (!chatInput || !sendChatButton || !chatMessagesContainer) {
            console.error("Elementos del chat no encontrados en el DOM.");
            return;
        }
        const query = chatInput.value.trim();
        if (!query) return;

        addMessageToChat(query, 'user');
        chatInput.value = '';
        chatInput.disabled = true;
        sendChatButton.disabled = true;
        addMessageToChat('', 'system', true); // Indicador de carga "Pensando..."

        let systemMessageContentDiv = null; // Para actualizar el mensaje del sistema en streaming

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ consulta: query, thread_id: chatThreadId }),
            });

            const loadingMessage = document.getElementById('loading-message');
            if (loadingMessage) {
                loadingMessage.remove();
            }

            if (!response.ok) {
                const errorText = await response.text();
                addMessageToChat(`Error: ${errorText || response.statusText}`, 'system error');
                return;
            }
            
            // Crear el div del mensaje del sistema una vez, antes de empezar a recibir chunks
            systemMessageContentDiv = addMessageToChat("", 'system'); // Crea el contenedor y devuelve el div de contenido

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let accumulatedResponse = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                accumulatedResponse += chunk;

                if (systemMessageContentDiv) {
                    try {
                        systemMessageContentDiv.innerHTML = marked.parse(accumulatedResponse || "");
                    } catch (e) {
                        console.error("Error al parsear Markdown en stream:", e);
                        systemMessageContentDiv.textContent = accumulatedResponse || ""; // Fallback
                    }
                    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
                }
            }
        } catch (error) {
            console.error('Error en la petición de chat:', error);
            const loadingMessage = document.getElementById('loading-message');
            if (loadingMessage) loadingMessage.remove();
            if (systemMessageContentDiv) { // Si ya se creó el div del sistema, mostrar error ahí
                systemMessageContentDiv.innerHTML = marked.parse("Error de conexión al intentar procesar tu consulta.");
            } else { // Si no, crear uno nuevo para el error
                addMessageToChat('Error de conexión al intentar procesar tu consulta.', 'system error');
            }
        } finally {
            if (chatInput) chatInput.disabled = false;
            if (sendChatButton) sendChatButton.disabled = false;
            if (chatInput) chatInput.focus();
        }
    }

    if (sendChatButton && chatInput) {
        sendChatButton.addEventListener('click', handleChatSubmit);
        chatInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                handleChatSubmit();
            }
        });
    }

    // --- Funciones de Búsqueda Avanzada y Detalles ---
    function formatFecha(fechaStr) {
        if (!fechaStr) return 'No especificada';
        try {
            const parts = fechaStr.split(' '); // API puede devolver "DD/MM/YYYY HH:mm:ss"
            if (parts.length > 0 && parts[0].match(/^\d{2}\/\d{2}\/\d{4}$/)) {
                return parts[0];
            }
            // Input date es YYYY-MM-DD
            if (fechaStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
                const [year, month, day] = fechaStr.split('-');
                return `${day}/${month}/${year}`;
            }
            return fechaStr; // Fallback
        } catch (e) {
            console.warn("Error formateando fecha:", fechaStr, e);
            return fechaStr;
        }
    }

    function crearItemConvocatoria(item, esUltimaConvocatoria = false) {
        const div = document.createElement('div');
        div.className = `list-group-item list-group-item-action convocatoria-item ${esUltimaConvocatoria ? 'p-3' : 'p-2'}`;
        // Usar BDNS como ID principal si está, si no, el ID que venga (ej. idConvocatoria)
        div.dataset.id = item.BDNS || item.idConvocatoria || item.id; 

        const title = item.tituloConvocatoria || item.titulo || "Título no disponible";
        const organismo = item.organsimo || item.organo || "Organismo no disponible";
        const fecha = formatFecha(item.fechaRegistroDesdeSolicitingToolDate || item.fechaPublicacion || item.fecha);

        let tipoAdminBadge = '';
        if (item.tipoAdministracion) {
            let badgeClass = 'bg-secondary';
            let adminText = item.tipoAdministracion;
            switch (String(item.tipoAdministracion).toUpperCase()) {
                case 'C': adminText = 'Estado'; badgeClass = 'bg-danger'; break;
                case 'A': adminText = 'Autonómica'; badgeClass = 'bg-warning text-dark'; break;
                case 'L': adminText = 'Local'; badgeClass = 'bg-info text-dark'; break;
                case 'O': adminText = 'Otros'; badgeClass = 'bg-success'; break;
            }
            tipoAdminBadge = `<span class="badge ${badgeClass} badge-administracion ms-2">${adminText}</span>`;
        }
        
        div.innerHTML = `
            <div class="d-flex w-100 justify-content-between">
                <h5 class="mb-1 convocatoria-title">${title}</h5>
                <small class="text-muted">${fecha}</small>
            </div>
            <p class="mb-1 convocatoria-meta">
                <i class="bi bi-building me-1"></i> ${organismo} ${tipoAdminBadge}
            </p>
            ${item.BDNS ? `<small class="text-muted">BDNS: ${item.BDNS}</small>` : ''}
        `;

        div.addEventListener('click', () => {
            if (div.dataset.id) {
                mostrarDetallesConvocatoria(div.dataset.id);
            } else {
                console.warn("No hay ID para mostrar detalles de convocatoria", item);
            }
        });
        return div;
    }

    function generarPaginacion(totalPages, currentPage) {
        if (!paginacionUl) return;
        paginacionUl.innerHTML = '';
        const maxPagesToShow = 5;
        let startPage, endPage;

        if (totalPages <= maxPagesToShow) {
            startPage = 0;
            endPage = totalPages -1;
        } else {
            if (currentPage <= Math.floor(maxPagesToShow / 2)) {
                startPage = 0;
                endPage = maxPagesToShow - 1;
            } else if (currentPage + Math.floor(maxPagesToShow / 2) >= totalPages) {
                startPage = totalPages - maxPagesToShow;
                endPage = totalPages - 1;
            } else {
                startPage = currentPage - Math.floor(maxPagesToShow / 2);
                endPage = currentPage + Math.floor(maxPagesToShow / 2);
            }
        }
        if (startPage < 0) startPage = 0;

        if (currentPage > 0) {
            const prevLi = document.createElement('li');
            prevLi.className = 'page-item';
            prevLi.innerHTML = `<a class="page-link" href="#" data-page="${currentPage - 1}"><i class="bi bi-chevron-left"></i></a>`;
            paginacionUl.appendChild(prevLi);
        }

        for (let i = startPage; i <= endPage; i++) {
            if (i < totalPages) { //Asegurar que i no excede totalPages
                const pageLi = document.createElement('li');
                pageLi.className = `page-item ${i === currentPage ? 'active' : ''}`;
                pageLi.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i + 1}</a>`;
                paginacionUl.appendChild(pageLi);
            }
        }

        if (currentPage < totalPages - 1) {
            const nextLi = document.createElement('li');
            nextLi.className = 'page-item';
            nextLi.innerHTML = `<a class="page-link" href="#" data-page="${currentPage + 1}"><i class="bi bi-chevron-right"></i></a>`;
            paginacionUl.appendChild(nextLi);
        }

        paginacionUl.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const pageTarget = e.target.closest('a');
                if (pageTarget && pageTarget.dataset.page) {
                   const page = parseInt(pageTarget.dataset.page);
                   realizarBusqueda(page);
                }
            });
        });
    }
    
    let currentSearchParamsForPagination = {}; // Usar esto para la paginación

    function mostrarResultados(data, pageRequest) {
        if (!resultadosList || !resultadosContainer || !resultadosInfo) return;

        resultadosList.innerHTML = '';
        resultadosContainer.style.display = 'block';

        if (!data || !data.content || data.content.length === 0) {
            resultadosInfo.textContent = 'No se encontraron convocatorias con los criterios seleccionados.';
            if (paginacionUl) paginacionUl.innerHTML = '';
            return;
        }

        const items = data.content;
        const totalItems = data.totalElements; 
        const pageSizeApi = data.size; // El tamaño de página que la API usó
        const totalPages = data.totalPages;
        const currentPageApi = data.number; // 0-indexed

        resultadosInfo.textContent = `Mostrando ${items.length} de ${totalItems} resultados. Página ${currentPageApi + 1} de ${totalPages}.`;

        items.forEach(item => {
            resultadosList.appendChild(crearItemConvocatoria(item));
        });
        
        if (totalPages > 1) {
            generarPaginacion(totalPages, currentPageApi);
        } else {
            if(paginacionUl) paginacionUl.innerHTML = '';
        }
    }
    
    async function realizarBusqueda(page = 0) {
        if (!searchForm || !resultadosInfo || !resultadosList) return;
        
        const formData = new FormData(searchForm);
        const params = new URLSearchParams();
        
        // Si page es 0 (nueva búsqueda), actualizamos los parámetros guardados
        // Si no, usamos los parámetros de la búsqueda anterior para la paginación
        if (page === 0) {
            currentSearchParamsForPagination = {};
            for (const [key, value] of formData.entries()) {
                if (value) {
                    params.append(key, value);
                    currentSearchParamsForPagination[key] = value;
                }
            }
        } else { // Usar parámetros guardados para paginar
            for (const key in currentSearchParamsForPagination) {
                if (currentSearchParamsForPagination[key] && key !== 'page' && key !== 'pageSize') {
                    params.append(key, currentSearchParamsForPagination[key]);
                }
            }
        }

        params.append('page', page);
        params.append('pageSize', '50'); 

        resultadosInfo.textContent = 'Buscando...';
        resultadosList.innerHTML = '<div class="text-center mt-3"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div></div>';
        if (paginacionUl) paginacionUl.innerHTML = '';
        
        try {
            const response = await fetch(`/api/buscar?${params.toString()}`);
            if (!response.ok) {
                throw new Error(`Error HTTP: ${response.status} ${response.statusText}`);
            }
            const data = await response.json();
            mostrarResultados(data, page);
        } catch (error) {
            console.error('Error en la búsqueda:', error);
            if(resultadosInfo) resultadosInfo.textContent = 'Error al realizar la búsqueda.';
            if(resultadosList) resultadosList.innerHTML = `<div class="alert alert-danger">No se pudieron cargar los resultados: ${error.message}</div>`;
        }
    }

    if (searchForm) {
        searchForm.addEventListener('submit', function (e) {
            e.preventDefault();
            realizarBusqueda(0);
        });
        searchForm.addEventListener('reset', function() {
            if (resultadosContainer) resultadosContainer.style.display = 'none';
            if (resultadosList) resultadosList.innerHTML = '';
            if (paginacionUl) paginacionUl.innerHTML = '';
            currentSearchParamsForPagination = {};
        });
    }

    async function mostrarDetallesConvocatoria(id) {
        if (!convocatoriaModalInstance || !convocatoriaModalTitle || !convocatoriaModalBody) return;

        convocatoriaModalTitle.textContent = 'Cargando detalles...';
        convocatoriaModalBody.innerHTML = '<div class="text-center mt-3"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div></div>';
        convocatoriaModalInstance.show();

        try {
            const response = await fetch(`/api/convocatoria/${id}`);
            if (!response.ok) throw new Error(`Error HTTP: ${response.status} ${response.statusText}`);
            
            const data = await response.json();
            // La API para un ID específico devuelve un array con un objeto (o a veces un objeto paginado con 'content')
            const convocatoria = (Array.isArray(data) && data.length > 0) ? data[0] : 
                                 (data && data.content && Array.isArray(data.content) && data.content.length > 0) ? data.content[0] :
                                 (data && Object.keys(data).length > 0 && !Array.isArray(data)) ? data : // Si es un solo objeto no en array
                                 null;


            if (!convocatoria || Object.keys(convocatoria).length === 0) {
                convocatoriaModalTitle.textContent = 'Detalles de la Convocatoria';
                convocatoriaModalBody.innerHTML = '<p>No se encontraron detalles para esta convocatoria o el formato es inesperado.</p>';
                return;
            }

            convocatoriaModalTitle.textContent = convocatoria.tituloConvocatoria || convocatoria.titulo || 'Detalle de Convocatoria';
            
            let htmlDetalles = `<div class="convocatoria-detail-header mb-3">
                                    <h4>${convocatoria.tituloConvocatoria || convocatoria.titulo || 'N/A'}</h4>
                                    <p class="text-muted mb-0">BDNS: ${convocatoria.BDNS || 'No disponible'}</p>
                                </div>`;

            htmlDetalles += '<div class="convocatoria-detail-section">';
            htmlDetalles += `<h5><i class="bi bi-building me-2"></i>Organismo</h5><p>${convocatoria.organsimo || convocatoria.organo || 'No especificado'}</p>`;
            
            htmlDetalles += `<h5><i class="bi bi-calendar-event me-2"></i>Fechas Clave</h5>`;
            htmlDetalles += `<p class="mb-1"><strong>Publicación:</strong> ${formatFecha(convocatoria.fechaPublicacion || convocatoria.fechaRegistroDesdeSolicitingToolDate || convocatoria.fechaCreacionBDNS) || 'No especificada'}</p>`;
            if (convocatoria.fechaFinPlazoSolicitud) {
                htmlDetalles += `<p class="mb-1"><strong>Fin Plazo Solicitud:</strong> ${formatFecha(convocatoria.fechaFinPlazoSolicitud)}</p>`;
            }
             if (convocatoria.fechaInicioPlazoSolicitud) {
                htmlDetalles += `<p class="mb-1"><strong>Inicio Plazo Solicitud:</strong> ${formatFecha(convocatoria.fechaInicioPlazoSolicitud)}</p>`;
            }
            htmlDetalles += '</div>';

            if(convocatoria.objetivo || convocatoria.descripcion){
                htmlDetalles += '<div class="convocatoria-detail-section">';
                htmlDetalles += `<h5><i class="bi bi-text-paragraph me-2"></i>Objeto / Descripción</h5><p>${convocatoria.objetivo || convocatoria.descripcion || 'No disponible'}</p>`;
                htmlDetalles += '</div>';
            }
            
            if (convocatoria.beneficiarios) {
                 htmlDetalles += `<div class="convocatoria-detail-section"><h5><i class="bi bi-people me-2"></i>Beneficiarios</h5><p>${convocatoria.beneficiarios}</p></div>`;
            }
            if (convocatoria.cuantia) { // Ojo: `cuantia` puede ser un string con HTML o texto.
                 htmlDetalles += `<div class="convocatoria-detail-section"><h5><i class="bi bi-cash-coin me-2"></i>Cuantía</h5><div>${convocatoria.cuantia}</div></div>`;
            }
            // El nombre del campo para URL puede variar, ej: urlDetalleConvocatoria, urlSedeElectronica, etc.
            const urlInfo = convocatoria.urlMasInformacion || convocatoria.urlDetalle || convocatoria.urlSedeElectronicaConvocatoria;
            if (urlInfo) { 
                htmlDetalles += `<div class="convocatoria-detail-section">
                                    <h5><i class="bi bi-link-45deg me-2"></i>Más Información</h5>
                                    <p><a href="${urlInfo}" target="_blank" rel="noopener noreferrer">Enlace a la convocatoria oficial</a></p>
                                 </div>`;
            }
            
            convocatoriaModalBody.innerHTML = htmlDetalles;

        } catch (error) {
            console.error('Error al obtener detalles de la convocatoria:', error);
            if (convocatoriaModalTitle) convocatoriaModalTitle.textContent = 'Error';
            if (convocatoriaModalBody) convocatoriaModalBody.innerHTML = `<p class="text-danger">Error al cargar los detalles: ${error.message}</p>`;
        }
    }
});