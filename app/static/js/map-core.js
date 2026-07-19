import { getThemeColor, findMainTheme } from './utils.js';

let map;
let clinicMarkers = [];
let nearbyMarkers = [];
let infoWindow;

function escapeHtml(text) {
    return String(text ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

async function waitForGoogleMaps() {
    if (window.google && window.google.maps) return;
    return new Promise(resolve => {
        const t = setInterval(() => {
            if (window.google && window.google.maps) {
                clearInterval(t);
                resolve();
            }
        }, 100);
    });
}

export async function initGoogleMap(mapId, center = { lat: 37.4979, lng: 127.0286 }, zoom = 14) {
    await waitForGoogleMaps();
    const { Map, RenderingType } = await google.maps.importLibrary("maps");

    // Hide Google's default business/attraction pins so only KR Care Clinic/Stay/Food markers compete for attention.
    // JSON styles require raster rendering (vector + mapId ignores `styles`).
    const hideGooglePois = [
        { featureType: 'poi', stylers: [{ visibility: 'off' }] },
        { featureType: 'poi.business', stylers: [{ visibility: 'off' }] },
    ];

    const options = {
        zoom,
        center,
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
        gestureHandling: 'greedy',
        clickableIcons: false,
        renderingType: RenderingType?.RASTER || 'RASTER',
        styles: hideGooglePois,
    };
    // Advanced Markers still need a map ID
    if (mapId) options.mapId = mapId;

    map = new Map(document.getElementById("map"), options);
    infoWindow = new google.maps.InfoWindow();
    _addLocationButton();
    return map;
}

function _clearMarkers(list) {
    list.forEach(m => { m.map = null; });
    list.length = 0;
}

export async function renderClinicMarkers(items) {
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");
    _clearMarkers(clinicMarkers);

    items.forEach(item => {
        if (!item.lat || !item.lng) return;

        const el = document.createElement('div');
        el.className = 'item-marker item-marker--clinic';
        el.innerHTML = `
            <span class="item-marker-pulse" aria-hidden="true"></span>
            <span class="item-marker-ring" aria-hidden="true"></span>
            <img src="${escapeHtml(item.thumbnail)}" alt="${escapeHtml(item.title)}" loading="lazy">
            <span class="item-marker-badge"><i class="fa-solid fa-heart-pulse" aria-hidden="true"></i></span>
        `;

        const marker = new AdvancedMarkerElement({
            map,
            position: { lat: parseFloat(item.lat), lng: parseFloat(item.lng) },
            title: item.title,
            content: el,
            zIndex: 100,
        });
        marker.itemData = { ...item, is_nearby: false };
        marker.addListener('click', () => focusClinicMarker(marker));
        clinicMarkers.push(marker);
    });
}

export async function renderNearbyMarkers(pois) {
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");
    _clearMarkers(nearbyMarkers);

    pois.forEach(item => {
        if (!item.lat || !item.lng) return;
        const theme = findMainTheme(item.categories || [item.kind]);
        const color = getThemeColor(theme);
        const iconClass = theme === 'food' ? 'fa-utensils' : 'fa-bed';

        const el = document.createElement('div');
        el.className = `marker-dot marker-dot--nearby marker-dot--${theme}`;
        el.style.backgroundColor = color;
        el.innerHTML = `<i class="fa-solid ${iconClass}" aria-hidden="true"></i>`;
        el.setAttribute('role', 'img');
        el.setAttribute('aria-label', item.kind || theme);

        const marker = new AdvancedMarkerElement({
            map,
            position: { lat: parseFloat(item.lat), lng: parseFloat(item.lng) },
            title: item.title,
            content: el,
            zIndex: 10,
        });
        marker.itemData = { ...item, is_nearby: true };
        marker.addListener('click', () => _showInfoWindow(marker, marker.itemData));
        nearbyMarkers.push(marker);
    });
}

/**
 * Show/hide markers by category theme (legacy). Prefer filterMapByClinicIds for region filters.
 */
export function filterMapMarkers(theme) {
    const showClinic = theme === 'all' || theme === 'clinic' || theme === 'region';
    const showStay = theme === 'all' || theme === 'stay';
    const showFood = theme === 'all' || theme === 'food';

    clinicMarkers.forEach(m => {
        m.map = showClinic ? map : null;
    });
    nearbyMarkers.forEach(m => {
        const kind = (m.itemData?.kind || '').toLowerCase();
        const visible =
            (kind === 'stay' && showStay) ||
            (kind === 'food' && showFood);
        m.map = visible ? map : null;
    });
    _fitVisible();
}

/**
 * Region filter: clinic markers are already rendered for the filtered set.
 * Keep nearby pins that relate to any visible clinic id.
 */
export function filterMapByClinicIds(clinicIds) {
    const ids = new Set(
        (clinicIds || []).map(id => String(id || '').replace(/_(en|ja|zh_tw|zh|ko)$/i, ''))
    );

    clinicMarkers.forEach(m => {
        m.map = map;
    });
    nearbyMarkers.forEach(m => {
        const near = m.itemData?.near_clinics || [];
        const visible = near.some(id =>
            ids.has(String(id || '').replace(/_(en|ja|zh_tw|zh|ko)$/i, ''))
        );
        m.map = visible ? map : null;
    });
    _fitVisible();
}

export function closeInfoWindow() {
    if (infoWindow) infoWindow.close();
}

function _clinicBaseId(item) {
    const raw = String(item?.id || item?.base_id || '').trim();
    return raw.replace(/_(en|ja|zh_tw|zh|ko)$/i, '');
}

/** Zoom/pan to a clinic marker and open its info window. */
export function focusClinicMarker(marker) {
    if (!map || !marker) return;
    const item = marker.itemData || {};
    const baseId = _clinicBaseId(item);
    const related = nearbyMarkers.filter(m => {
        const near = m.itemData?.near_clinics || [];
        return baseId && near.includes(baseId) && m.map;
    });

    if (related.length) {
        const bounds = new google.maps.LatLngBounds();
        bounds.extend(marker.position);
        related.forEach(m => bounds.extend(m.position));
        map.fitBounds(bounds, { top: 72, right: 48, bottom: 48, left: 48 });
        google.maps.event.addListenerOnce(map, 'idle', () => {
            if (map.getZoom() > 16) map.setZoom(16);
            if (map.getZoom() < 14) map.setZoom(14);
        });
    } else {
        map.panTo(marker.position);
        map.setZoom(16);
    }
    _showInfoWindow(marker, item);
}

/** Focus map on a clinic by item id (with or without lang suffix). */
export function focusClinicById(id) {
    const baseId = _clinicBaseId({ id });
    const marker = clinicMarkers.find(m => _clinicBaseId(m.itemData) === baseId);
    if (!marker) return false;
    focusClinicMarker(marker);
    return true;
}

function _showInfoWindow(marker, item) {
    if (item.is_nearby) {
        infoWindow.setContent(_nearbyInfoHtml(item));
    } else {
        infoWindow.setContent(_clinicInfoHtml(item));
    }
    infoWindow.open({ anchor: marker, map });
    google.maps.event.addListenerOnce(infoWindow, 'domready', () => {
        document.getElementById('krcare-info-close')?.addEventListener('click', (e) => {
            e.preventDefault();
            closeInfoWindow();
        });
    });
}

function _clinicInfoHtml(item) {
    return `
        <div class="info-box-content">
            <div class="info-box-badge">Clinic</div>
            <div class="info-box-title">${escapeHtml(item.title)}</div>
            <div class="info-box-address">📍 ${escapeHtml(item.address || '')}</div>
            <a href="${escapeHtml(item.link || '#')}" class="info-box-link">View Details →</a>
        </div>`;
}

function _nearbyInfoHtml(item) {
    const kind = escapeHtml(item.kind || '');
    const tel = (item.tel || '').trim();
    const website = (item.website || '').trim();
    const telHref = tel.replace(/[\s-]/g, '');
    const thumb = escapeHtml(item.thumbnail || '/static/images/default.jpg');

    const rows = [];
    if (item.subtype) rows.push(['Type', item.subtype]);
    if (item.hours) rows.push(['Hours', item.hours]);
    if (item.parking) rows.push(['Parking', item.parking]);
    if (item.transit) rows.push(['Access', item.transit]);
    if (tel) rows.push(['Phone', tel]);

    const details = rows.map(([label, value]) => `
        <div class="info-box-row">
            <dt>${escapeHtml(label)}</dt>
            <dd>${escapeHtml(value)}</dd>
        </div>`).join('');

    const actions = [];
    if (tel) {
        actions.push(`<a class="info-box-action" href="tel:${escapeHtml(telHref)}"><i class="fa-solid fa-phone"></i> Call</a>`);
    }
    if (website) {
        actions.push(`<a class="info-box-action info-box-action--primary" href="${escapeHtml(website)}" target="_blank" rel="noopener noreferrer"><i class="fa-solid fa-globe"></i> Website</a>`);
    }
    actions.push(`<button type="button" class="info-box-action info-box-action--close" id="krcare-info-close"><i class="fa-solid fa-xmark"></i> Close</button>`);

    return `
        <div class="info-box-content info-box-content--nearby">
            <div class="info-box-media">
                <img src="${thumb}" alt="" loading="lazy">
            </div>
            <div class="info-box-badge info-box-badge--${kind.toLowerCase()}">${kind}</div>
            <div class="info-box-title">${escapeHtml(item.title)}</div>
            <div class="info-box-address"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(item.address || '')}</div>
            ${item.overview ? `<p class="info-box-overview">${escapeHtml(item.overview)}</p>` : ''}
            ${details ? `<dl class="info-box-dl">${details}</dl>` : ''}
            ${item.tips ? `<p class="info-box-tips"><i class="fa-solid fa-circle-info"></i> ${escapeHtml(item.tips)}</p>` : ''}
            <div class="info-box-actions">${actions.join('')}</div>
        </div>`;
}

function _fitVisible() {
    if (!map) return;
    const bounds = new google.maps.LatLngBounds();
    let n = 0;
    [...clinicMarkers, ...nearbyMarkers].forEach(m => {
        if (m.map) {
            bounds.extend(m.position);
            n += 1;
        }
    });
    if (n === 0) return;
    if (n === 1) {
        map.setCenter([...clinicMarkers, ...nearbyMarkers].find(m => m.map).position);
        map.setZoom(14);
    } else {
        map.fitBounds(bounds, { padding: 80 });
    }
}

function _addLocationButton() {
    const btn = document.createElement('button');
    btn.textContent = '🎯 My Location';
    btn.className = 'location-button';
    btn.style.cssText = 'margin:10px; padding:8px 14px; background:#fff; border:1px solid #ccc; border-radius:20px; cursor:pointer; font-size:13px; box-shadow:0 2px 6px rgba(0,0,0,.2);';
    map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(btn);
    btn.onclick = () => {
        if (!navigator.geolocation) return;
        navigator.geolocation.getCurrentPosition(pos => {
            map.setCenter({ lat: pos.coords.latitude, lng: pos.coords.longitude });
            map.setZoom(14);
        });
    };
}

// Back-compat aliases used by older callers
export async function renderPhotoMarkers(items) {
    await renderClinicMarkers(items);
    filterMapMarkers('all');
}

export function filterMarkers(theme) {
    filterMapMarkers(theme);
}
