(function () {
    "use strict";

    function getEl(id) {
        return document.getElementById(id);
    }

    function getValue(id) {
        const el = getEl(id);
        return el ? el.value : "";
    }

    function showError(message) {
        const text = message || "No se pudo conectar con el servidor.";
        if (window.Swal) {
            Swal.fire({
                title: "Error",
                text,
                icon: "error",
                confirmButtonColor: "#2d6cdf",
            });
        } else {
            alert(text);
        }
    }

    function showSuccess() {
        if (window.Swal) {
            Swal.fire({
                title: "¡Acuerdo enviado!",
                text: "El prestador revisará tu solicitud.",
                icon: "success",
                confirmButtonColor: "#2d6cdf",
            });
        } else {
            alert("El prestador revisará tu solicitud.");
        }
    }

    function closeModal() {
        if (typeof window.cerrarModal === "function") {
            window.cerrarModal();
            return;
        }
        const modal = getEl("modalAcuerdo");
        const form = getEl("formAcuerdo");
        if (modal) {
            modal.style.display = "none";
        }
        if (form) {
            form.reset();
        }
    }

    function bindServerSubmit() {
        const form = getEl("formAcuerdo");
        if (!form || form.dataset.serverSubmitBound === "1") {
            return;
        }

        form.addEventListener(
            "submit",
            async function (event) {
                event.preventDefault();
                event.stopImmediatePropagation();

                const prestadorId = window.prestadorSeleccionadoId;
                if (!prestadorId) {
                    showError("No se seleccionó un prestador válido.");
                    return;
                }

                const config = window.JobxpressRequestConfig || {};
                try {
                    const response = await fetch("/cliente/solicitud", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            prestador_id: prestadorId,
                            servicio_id: config.serviceId ?? null,
                            servicio: config.serviceName || "",
                            fecha: getValue("fecha"),
                            hora: getValue("hora"),
                            monto: getValue("monto"),
                            direccion: getValue("direccion"),
                            descripcion: getValue("descripcion"),
                        }),
                    });

                    const data = await response.json().catch(function () {
                        return {};
                    });

                    if (!response.ok) {
                        showError(data.error || "No se pudo enviar la solicitud.");
                        return;
                    }

                    showSuccess();
                    closeModal();
                } catch (_error) {
                    showError();
                }
            },
            true
        );

        form.dataset.serverSubmitBound = "1";
    }

    document.addEventListener("DOMContentLoaded", bindServerSubmit);
})();
