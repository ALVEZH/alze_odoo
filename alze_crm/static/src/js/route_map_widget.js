/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AlzeRouteMapWidget extends Component {
    static template = "alze_crm.RouteMapWidget";
    static props = { ...standardFieldProps };
    static defaultProps = { height: "400px" };

    setup() {
        this.mapRef = useRef("map");
        this.orm = useService("orm");
        this.map = null;
        this.drawnItems = null;
        this.markersLayer = null;
        this.polygon = null;
        this.state = useState({
            value: this.props.record.data[this.props.name] || "[]",
        });
        onMounted(() => this.initMap());
    }

    // ------------------------------------------------------------
    // Mapeo de índice de color (0-9) a código hexadecimal
    // (Coincide con los colores estándar del widget color_picker de Odoo)
    // ------------------------------------------------------------
    getColorFromIndex(index) {
        const colors = [
            "#FF0000", // 0: Rojo por defecto
            "#FF0000", // 1: Rojo
            "#FFA500", // 2: Naranja
            "#FFFF00", // 3: Amarillo
            "#00FFFF", // 4: Cian
            "#800080", // 5: Púrpura
            "#FFEBCD", // 6: Almendra
            "#40E0D0", // 7: Turquesa
            "#0000FF", // 8: Azul
            "#E30B5C", // 9: Frambuesa
            "#00FF00", // 10: Verde
            "#EE82EE"  // 11: Violeta
        ];
        return colors[index] || "#FF0000";
    }

    getCurrentColor() {
        const colorIndex = this.props.record.data.color;
        return this.getColorFromIndex(colorIndex);
    }

    async initMap() {
        if (typeof L === 'undefined') {
            await this.loadLeaflet();
        }
        this.createMap();
        await this.loadPartnerMarkers();
    }

    loadLeaflet() {
        return new Promise((resolve, reject) => {
            if (typeof L !== 'undefined') return resolve();
            const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = '/alze_crm/static/lib/leaflet/leaflet.css'; document.head.appendChild(link);
            const drawCss = document.createElement('link'); drawCss.rel = 'stylesheet'; drawCss.href = '/alze_crm/static/lib/leaflet/leaflet.draw.css'; document.head.appendChild(drawCss);
            const script = document.createElement('script'); script.src = '/alze_crm/static/lib/leaflet/leaflet.js';
            script.onload = () => {
                const drawScript = document.createElement('script'); drawScript.src = '/alze_crm/static/lib/leaflet/leaflet.draw.js';
                drawScript.onload = () => resolve();
                drawScript.onerror = reject;
                document.head.appendChild(drawScript);
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    createMap() {
        const mapElement = this.mapRef.el;
        this.map = L.map(mapElement, { center: [19.4326, -99.1332], zoom: 10 });
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(this.map);

        this.drawnItems = new L.FeatureGroup();
        this.markersLayer = new L.FeatureGroup();
        this.map.addLayer(this.drawnItems);
        this.map.addLayer(this.markersLayer);

        const currentColor = this.getCurrentColor();

        this.drawControl = new L.Control.Draw({
            draw: {
                polygon: {
                    allowIntersection: false,
                    showArea: true,
                    shapeOptions: {
                        color: currentColor,
                        fillColor: currentColor,
                        fillOpacity: 0.3,
                        weight: 2,
                    },
                },
                polyline: false, rectangle: false, circle: false, circlemarker: false, marker: false,
            },
            edit: { featureGroup: this.drawnItems, remove: true },
        });
        this.map.addControl(this.drawControl);

        this.map.on(L.Draw.Event.CREATED, (e) => {
            this.drawnItems.clearLayers();
            this.drawnItems.addLayer(e.layer);
            this.polygon = e.layer;
            this.savePolygonCoordinates();
            e.layer.on('edit', () => this.savePolygonCoordinates());
            e.layer.on('dragend', () => this.savePolygonCoordinates());
        });
        this.map.on(L.Draw.Event.EDITED, () => this.savePolygonCoordinates());
        this.map.on(L.Draw.Event.DELETED, () => {
            this.polygon = null;
            this.state.value = "[]";
            this.props.record.update({ [this.props.name]: "[]" });
        });

        this.loadExistingPolygon();
    }

    loadExistingPolygon() {
        const coordsStr = this.state.value;
        if (!coordsStr || coordsStr === "[]") return;
        try {
            const coords = JSON.parse(coordsStr);
            if (coords.length < 3) return;
            const latlngs = coords.map(c => [c.lat, c.lng]);
            const currentColor = this.getCurrentColor();
            this.polygon = L.polygon(latlngs, {
                color: currentColor,
                fillColor: currentColor,
                fillOpacity: 0.3,
                weight: 2,
            });
            this.drawnItems.clearLayers();
            this.drawnItems.addLayer(this.polygon);
            this.map.fitBounds(this.polygon.getBounds());
            this.polygon.on('edit', () => this.savePolygonCoordinates());
            this.polygon.on('dragend', () => this.savePolygonCoordinates());
        } catch (e) { console.error(e); }
    }

    async loadPartnerMarkers() {
        const routeId = this.props.record.resId;
        if (!routeId) return;
        try {
            const partners = await this.orm.call('alze.route', 'get_partner_coordinates', [routeId]);
            this.markersLayer.clearLayers();
            partners.forEach(p => {
                if (p.lat && p.lng) {
                    const googleMapsUrl = `https://www.google.com/maps?q=${p.lat},${p.lng}`;
                    const popupContent = `
                        <div style="min-width: 150px;">
                            <b>${p.name}</b><br>
                            <a href="${googleMapsUrl}" target="_blank" rel="noopener noreferrer" 
                               style="display: inline-block; margin-top: 5px; color: #007bff; text-decoration: none;">
                                <i class="fa fa-map-marker"></i> Ver en Google Maps
                            </a>
                        </div>
                    `;
                    const marker = L.marker([p.lat, p.lng]).bindPopup(popupContent);
                    this.markersLayer.addLayer(marker);
                }
            });
            if (partners.length > 0) {
                const group = new L.featureGroup(partners.map(p => L.marker([p.lat, p.lng])));
                if (group.getBounds().isValid()) {
                    this.map.fitBounds(group.getBounds().pad(0.1));
                }
            }
        } catch (e) {
            console.error("Error cargando marcadores de clientes:", e);
        }
    }

    savePolygonCoordinates() {
        if (!this.polygon) return;
        const latlngs = this.polygon.getLatLngs()[0];
        const coords = latlngs.map(ll => ({ lat: ll.lat, lng: ll.lng }));
        const coordsStr = JSON.stringify(coords);
        this.state.value = coordsStr;
        this.props.record.update({ [this.props.name]: coordsStr });
    }

    clearPolygon() {
        if (this.polygon) {
            this.drawnItems.removeLayer(this.polygon);
            this.polygon = null;
        }
        this.state.value = "[]";
        this.props.record.update({ [this.props.name]: "[]" });
    }
}

AlzeRouteMapWidget.template = "alze_crm.RouteMapWidget";
registry.category("fields").add("alze_route_map", { component: AlzeRouteMapWidget });
export default AlzeRouteMapWidget;