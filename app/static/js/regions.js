/**
 * Region parsing for KR Care clinic filters (address-based, no paid APIs).
 * Returns { sido, district } keys used by the two-level filter UI.
 */

const SIDO_RULES = [
    ['seoul', /Seoul|서울|ソウル|首尔|首爾/i],
    ['busan', /Busan|부산|釜山|プサン|プサン/i],
    ['incheon', /Incheon|인천|仁川/i],
    ['gyeonggi', /Gyeonggi|경기|京畿/i],
    ['daegu', /Daegu|대구|大邱/i],
    ['daejeon', /Daejeon|대전|大田/i],
    ['gwangju', /Gwangju|광주|光州/i],
    ['ulsan', /Ulsan|울산|蔚山/i],
    ['gangwon', /Gangwon|강원|江原/i],
    ['jeju', /Jeju|제주|济州|濟州/i],
    ['jeonbuk', /Jeonbuk|Jeollabuk|전북|전라북|全北/i],
    ['jeonnam', /Jeonnam|전남|전라남|全南/i],
    ['gyeongbuk', /Gyeongbuk|경북|경상북|庆北|慶北/i],
    ['gyeongnam', /Gyeongnam|경남|경상남|庆南|慶南/i],
    ['chungbuk', /Chungbuk|충북|충청북|忠北|Cheongju/i],
    ['chungnam', /Chungnam|충남|충청남|忠南/i],
];

/** Top-level filter keys shown in the first row */
export const SIDO_FILTERS = [
    { key: 'all', label: 'All', countId: 'count-sido-all' },
    { key: 'seoul', label: 'Seoul', countId: 'count-sido-seoul' },
    { key: 'busan', label: 'Busan', countId: 'count-sido-busan' },
    { key: 'incheon', label: 'Incheon', countId: 'count-sido-incheon' },
    { key: 'gyeonggi', label: 'Gyeonggi', countId: 'count-sido-gyeonggi' },
    { key: 'daegu', label: 'Daegu', countId: 'count-sido-daegu' },
    { key: 'other', label: 'Other', countId: 'count-sido-other' },
];

const TOP_SIDO = new Set(['seoul', 'busan', 'incheon', 'gyeonggi', 'daegu']);

/** Seoul sub-filters (featured districts + Other Seoul) */
export const SEOUL_DISTRICT_FILTERS = [
    { key: 'all', label: 'All Seoul', countId: 'count-gu-seoul-all' },
    { key: 'gangnam', label: 'Gangnam', countId: 'count-gu-gangnam' },
    { key: 'seocho', label: 'Seocho', countId: 'count-gu-seocho' },
    { key: 'jung', label: 'Jung', countId: 'count-gu-jung' },
    { key: 'jongno', label: 'Jongno', countId: 'count-gu-jongno' },
    { key: 'mapo', label: 'Mapo', countId: 'count-gu-mapo' },
    { key: 'other', label: 'Other Seoul', countId: 'count-gu-seoul-other' },
];

/** Busan sub-filters */
export const BUSAN_DISTRICT_FILTERS = [
    { key: 'all', label: 'All Busan', countId: 'count-gu-busan-all' },
    { key: 'busanjin', label: 'Busanjin', countId: 'count-gu-busanjin' },
    { key: 'haeundae', label: 'Haeundae', countId: 'count-gu-haeundae' },
    { key: 'nam', label: 'Nam', countId: 'count-gu-nam' },
    { key: 'other', label: 'Other Busan', countId: 'count-gu-busan-other' },
];

const SEOUL_FEATURED = new Set(['gangnam', 'seocho', 'jung', 'jongno', 'mapo']);
const BUSAN_FEATURED = new Set(['busanjin', 'haeundae', 'nam']);

const GU_EN_ALIASES = {
    gangnam: 'gangnam',
    seocho: 'seocho',
    jung: 'jung',
    jongno: 'jongno',
    mapo: 'mapo',
    busanjin: 'busanjin',
    haeundae: 'haeundae',
    nam: 'nam',
    yeongdeungpo: 'yeongdeungpo',
    songpa: 'songpa',
    yongsan: 'yongsan',
    dong: 'dong',
    seo: 'seo',
    buk: 'buk',
    saha: 'saha',
    yeonje: 'yeonje',
    dongnae: 'dongnae',
    gijang: 'gijang',
};

const GU_KO = [
    ['gangnam', /강남구/],
    ['seocho', /서초구/],
    ['jung', /중구/],
    ['jongno', /종로구/],
    ['mapo', /마포구/],
    ['busanjin', /부산진구/],
    ['haeundae', /해운대구/],
    ['nam', /남구/],
];

export function parseSido(address) {
    const text = String(address || '');
    for (const [key, re] of SIDO_RULES) {
        if (re.test(text)) return TOP_SIDO.has(key) ? key : 'other';
    }
    return 'other';
}

export function parseDistrict(address, sido) {
    const text = String(address || '');
    const m = text.match(/\b([A-Za-z]+(?:jin)?)-gu\b/i);
    if (m) {
        const raw = m[1].toLowerCase();
        if (raw === 'busanjin') return 'busanjin';
        return GU_EN_ALIASES[raw] || raw;
    }
    if (/\bGijang\b/i.test(text)) return 'gijang';
    for (const [key, re] of GU_KO) {
        if (re.test(text)) return key;
    }
    // Japanese / Chinese district fragments seen in multilingual addresses
    if (sido === 'seoul') {
        if (/瑞草|ソチョ|서초/.test(text)) return 'seocho';
        if (/江南|カンナム|강남/.test(text)) return 'gangnam';
        if (/鍾路|钟路|종로|ジョンロ/.test(text)) return 'jongno';
        if (/麻浦|마포|マポ/.test(text)) return 'mapo';
        if (/中区|중구|チュンク/.test(text)) return 'jung';
    }
    if (sido === 'busan') {
        if (/釜山鎮|부산진|ソミョン|西面/.test(text)) return 'busanjin';
        if (/海云台|海雲台|해운대|ヘウンデ/.test(text)) return 'haeundae';
        if (/南区|남구|ナム区/.test(text)) return 'nam';
    }
    return null;
}

export function parseRegion(address) {
    const sido = parseSido(address);
    const district = parseDistrict(address, sido);
    return { sido, district };
}

/** Enrich item with region keys (mutates for convenience, also returns). */
export function withRegion(item) {
    const region = parseRegion(item?.address);
    item.region = region;
    return item;
}

/**
 * Does a clinic match the current two-level filter?
 * @param {{sido:string, district:?string}} region
 * @param {string} sidoFilter  'all' | sido key
 * @param {string|null} districtFilter  null | 'all' | featured key | 'other'
 */
export function matchesRegionFilter(region, sidoFilter, districtFilter) {
    if (!region) return sidoFilter === 'all';
    if (sidoFilter === 'all') return true;
    if (region.sido !== sidoFilter) return false;
    if (!districtFilter || districtFilter === 'all') return true;

    const featured =
        sidoFilter === 'seoul' ? SEOUL_FEATURED :
        sidoFilter === 'busan' ? BUSAN_FEATURED : null;

    if (!featured) return true;

    if (districtFilter === 'other') {
        return !region.district || !featured.has(region.district);
    }
    return region.district === districtFilter;
}

export function districtFiltersFor(sido) {
    if (sido === 'seoul') return SEOUL_DISTRICT_FILTERS;
    if (sido === 'busan') return BUSAN_DISTRICT_FILTERS;
    return [];
}
