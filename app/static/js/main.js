/**
 * KR Care map + list engine
 * - Clinics: content items with detail pages
 * - Stay/Food: nearby map pins (shown for clinics matching the region filter)
 * - Filters: two-level region (sido → district)
 */

import {
    SIDO_FILTERS,
    districtFiltersFor,
    matchesRegionFilter,
    withRegion,
} from './regions.js';
import {
    initGoogleMap,
    renderClinicMarkers,
    renderNearbyMarkers,
    filterMapByClinicIds,
    closeInfoWindow,
    focusClinicById,
} from './map-core.js';

const params = new URLSearchParams(window.location.search);
let currentLang = params.get('lang') || document.documentElement.lang || 'en';
if (!['en', 'ja', 'zh', 'zh_tw', 'ko'].includes(currentLang)) {
    currentLang = 'en';
}

let clinicItems = [];
let nearbyPois = [];
let currentSido = 'all';
let currentDistrict = null; // null | 'all' | featured key | 'other'

function clinicBaseId(item) {
    return String(item?.id || item?.base_id || '').replace(/_(en|ja|zh_tw|zh|ko)$/i, '');
}

async function loadClinics(lang) {
    const res = await fetch(`/api/items?lang=${encodeURIComponent(lang)}`);
    const data = await res.json();
    const key = Object.keys(data).find(k => Array.isArray(data[k]));
    const items = data[key] || [];
    clinicItems = items
        .filter(i => (i.categories || []).some(c => String(c).toLowerCase() === 'clinic'))
        .map(withRegion);
    if (!clinicItems.length) clinicItems = items.map(withRegion);

    const el = document.getElementById('last-updated-date');
    if (el) el.textContent = data.last_updated || '';
}

async function loadNearby(lang) {
    const res = await fetch(`/api/nearby?lang=${encodeURIComponent(lang)}`);
    const data = await res.json();
    nearbyPois = data.pois || [];
}

function filteredClinics() {
    return clinicItems.filter(item =>
        matchesRegionFilter(item.region, currentSido, currentDistrict)
    );
}

function filteredNearby(clinics) {
    const ids = new Set(clinics.map(clinicBaseId));
    return nearbyPois.filter(poi => {
        const near = poi.near_clinics || [];
        return near.some(id => ids.has(String(id).replace(/_(en|ja|zh_tw|zh|ko)$/i, '')));
    });
}

async function initApp() {
    try {
        await Promise.all([loadClinics(currentLang), loadNearby(currentLang)]);
        const mapEl = document.getElementById('map');
        const mapId = mapEl?.dataset.mapId || '';
        await initGoogleMap(mapId);
        bindFilterButtons();
        await updateUI();
    } catch (err) {
        console.error('KR Care: initial load failed', err);
    }
}

async function updateUI() {
    const clinics = filteredClinics();
    // Sido / "All Seoul" views: clinics only. Nearby Stay/Food pins sprawl
    // outside the city and keep the map from framing Seoul correctly.
    const showNearby = Boolean(currentDistrict && currentDistrict !== 'all');
    const nearby = showNearby ? filteredNearby(clinics) : [];
    const scope =
        currentSido === 'all' ? 'all' :
        (currentDistrict && currentDistrict !== 'all') ? 'district' :
        'sido';
    renderList(clinics);
    await renderClinicMarkers(clinics);
    await renderNearbyMarkers(nearby);
    filterMapByClinicIds(clinics.map(clinicBaseId), { scope });
    updateCounts();
    renderDistrictRow();
}

function renderList(data) {
    const container = document.getElementById('item-list');
    if (!container) return;

    if (data.length === 0) {
        container.innerHTML = `
            <div style="grid-column:1/-1; text-align:center; padding:100px 0; color:#999;">
                <p style="font-size:1.2rem;">No clinics found in this region.</p>
            </div>`;
        return;
    }

    container.innerHTML = data.map(item => `
        <div class="onsen-card" data-clinic-id="${item.id || ''}">
            <a href="${item.link}">
                <img src="${item.thumbnail}" class="card-thumb" alt="${item.title}" loading="lazy">
            </a>
            <div class="card-content">
                <h3 class="card-title"><a href="${item.link}">${item.title}</a></h3>
                <p class="card-summary">${item.summary || ''}</p>
                <div class="card-meta">
                    <span>📍 ${item.address || ''}</span>
                    <span>📅 ${item.published || item.date || ''}</span>
                </div>
                <button type="button" class="card-map-focus" data-clinic-id="${item.id || ''}">Show on map</button>
            </div>
        </div>
    `).join('');

    container.querySelectorAll('.card-map-focus').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.clinicId;
            if (!id || !focusClinicById(id)) return;
            document.getElementById('map')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    });
}

function updateCounts() {
    const totalEl = document.getElementById('total-items');
    if (totalEl) totalEl.textContent = String(filteredClinics().length);

    for (const btn of SIDO_FILTERS) {
        const el = document.getElementById(btn.countId);
        if (!el) continue;
        if (btn.key === 'all') {
            el.textContent = String(clinicItems.length);
            continue;
        }
        el.textContent = String(
            clinicItems.filter(i => matchesRegionFilter(i.region, btn.key, null)).length
        );
    }

    const districts = districtFiltersFor(currentSido);
    for (const btn of districts) {
        const el = document.getElementById(btn.countId);
        if (!el) continue;
        const districtKey = btn.key === 'all' ? 'all' : btn.key;
        el.textContent = String(
            clinicItems.filter(i =>
                matchesRegionFilter(i.region, currentSido, districtKey)
            ).length
        );
    }
}

function renderDistrictRow() {
    const row = document.querySelector('.theme-filter-buttons[data-level="district"]');
    if (!row) return;

    const filters = districtFiltersFor(currentSido);
    if (!filters.length) {
        row.classList.add('is-hidden');
        row.hidden = true;
        row.innerHTML = '';
        return;
    }

    row.hidden = false;
    row.classList.remove('is-hidden');
    const active = currentDistrict || 'all';
    row.innerHTML = filters.map(btn => `
        <button type="button"
                class="theme-button theme-button--district ${btn.key === active ? 'active' : ''}"
                data-district="${btn.key}">
            ${btn.label}
            <span class="count-badge" id="${btn.countId}">0</span>
        </button>
    `).join('');

    row.querySelectorAll('.theme-button').forEach(btn => {
        btn.addEventListener('click', async () => {
            currentDistrict = btn.dataset.district;
            closeInfoWindow();
            await updateUI();
            if (window.innerWidth < 768) {
                document.getElementById('list-section')?.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // refresh district counts after buttons exist
    updateCounts();
}

function bindFilterButtons() {
    document.querySelectorAll('.theme-filter-buttons[data-level="sido"] .theme-button').forEach(btn => {
        btn.addEventListener('click', async () => {
            document
                .querySelectorAll('.theme-filter-buttons[data-level="sido"] .theme-button')
                .forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSido = btn.dataset.sido || 'all';
            currentDistrict = currentSido === 'seoul' || currentSido === 'busan' ? 'all' : null;
            closeInfoWindow();
            await updateUI();
            if (window.innerWidth < 768) {
                document.getElementById('list-section')?.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
}

document.querySelectorAll('.lang-btn[data-lang]').forEach(btn => {
    btn.addEventListener('click', async () => {
        document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentLang = btn.dataset.lang;
        await Promise.all([loadClinics(currentLang), loadNearby(currentLang)]);
        closeInfoWindow();
        await updateUI();
    });
});

initApp();
