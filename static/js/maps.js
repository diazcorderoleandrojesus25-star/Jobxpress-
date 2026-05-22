(function () {
    "use strict";

    const geocodeEndpoint = "/api/maps/geocode";
    const defaultCenter = { lat: 4.6486259, lng: -74.247896 };
    const defaultZoom = 12;
    const validatedZoom = 15;

    let lastLat = null;
    let lastLng = null;
    let lastValidatedAddress = null;

    function getEl(id) {
        return document.getElementById(id);
    }

    function setStatus(msg) {
        const estado = getEl("estadoDireccion");
        if (estado) {
            estado.textContent = msg;
        }
    }

    function buildEmbedUrl(lat, lng, zoom) {
        return `https://www.google.com/maps?q=${encodeURIComponent(`${lat},${lng}`)}&z=${zoom}&output=embed`;
    }

    function renderMap(lat, lng, zoom) {
        const mapEl = getEl("mapaDireccion");
        if (!mapEl) {
            return;
        }
        mapEl.innerHTML = `
            <iframe
                title="Vista previa del mapa"
                src="${buildEmbedUrl(lat, lng, zoom)}"
                width="100%"
                height="100%"
                style="border:0;"
                loading="lazy"
                referrerpolicy="no-referrer-when-downgrade">
            </iframe>
        `;
    }

    function initMap() {
        renderMap(defaultCenter.lat, defaultCenter.lng, defaultZoom);
    }

    function warnNoAddress() {
        if (window.Swal) {
            Swal.fire({
                title: "Direccion requerida",
                text: "Escribe una direccion para ubicarla en el mapa.",
                icon: "warning",
                confirmButtonColor: "#2d6cdf",
            });
        } else {
            alert("Escribe una direccion para ubicarla en el mapa.");
        }
    }

    function warnInvalidAddress(message) {
        const text = message || "La direccion ingresada no pudo ubicarse en el mapa.";
        if (window.Swal) {
            Swal.fire({
                title: "Direccion invalida",
                text,
                icon: "error",
                confirmButtonColor: "#2d6cdf",
            });
        } else {
            alert(text);
        }
    }

    function clearValidatedLocation() {
        lastLat = null;
        lastLng = null;
        lastValidatedAddress = null;
        initMap();
    }

    async function validateAddress() {
        const direccion = getEl("direccion");
        const addr = (direccion && direccion.value ? direccion.value : "").trim();
        if (!addr) {
            clearValidatedLocation();
            warnNoAddress();
            return;
        }

        setStatus("Buscando...");

        try {
            const response = await fetch(
                `${geocodeEndpoint}?address=${encodeURIComponent(addr)}`,
                {
                    headers: {
                        Accept: "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                }
            );
            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                clearValidatedLocation();
                setStatus("Direccion invalida");
                warnInvalidAddress(data.error);
                return;
            }

            lastLat = data.lat;
            lastLng = data.lng;
            lastValidatedAddress = addr.toLowerCase();
            renderMap(lastLat, lastLng, validatedZoom);
            setStatus("Direccion verificada");
        } catch (_error) {
            clearValidatedLocation();
            setStatus("No se pudo validar");
            warnInvalidAddress("No se pudo conectar con el servidor para validar la direccion.");
        }
    }

    function bindValidateButton() {
        const btn = getEl("btnValidarDireccion");
        if (!btn || btn.dataset.mapsBound === "1") {
            return;
        }
        btn.addEventListener("click", validateAddress);
        btn.dataset.mapsBound = "1";
    }

    function bindAddressInputReset() {
        const direccion = getEl("direccion");
        if (!direccion || direccion.dataset.mapsWatchBound === "1") {
            return;
        }
        direccion.addEventListener("input", () => {
            const current = (direccion.value || "").trim().toLowerCase();
            if (!current || current !== lastValidatedAddress) {
                clearValidatedLocation();
                setStatus("Sin validar");
            }
        });
        direccion.dataset.mapsWatchBound = "1";
    }

    function bindAgreementSubmitValidation() {
        const form = getEl("formAcuerdo");
        if (!form || form.dataset.mapsSubmitBound === "1") {
            return;
        }
        form.addEventListener(
            "submit",
            (event) => {
                const direccion = getEl("direccion");
                const addr = (direccion && direccion.value ? direccion.value : "").trim().toLowerCase();
                const isValidated =
                    !!addr &&
                    !!lastValidatedAddress &&
                    addr === lastValidatedAddress &&
                    lastLat !== null &&
                    lastLng !== null;
                if (isValidated) {
                    return;
                }
                event.preventDefault();
                event.stopImmediatePropagation();
                setStatus("Direccion invalida");
                warnInvalidAddress();
            },
            true
        );
        form.dataset.mapsSubmitBound = "1";
    }

    document.addEventListener("DOMContentLoaded", () => {
        initMap();
        bindValidateButton();
        bindAddressInputReset();
        bindAgreementSubmitValidation();
    });

    window.JobxpressMaps = {
        initMap,
        validateAddress,
        bindValidateButton,
        bindAddressInputReset,
        bindAgreementSubmitValidation,
        getLastLat: () => lastLat,
        getLastLng: () => lastLng,
    };
})();
