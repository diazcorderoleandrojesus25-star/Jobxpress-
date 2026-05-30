import http from 'k6/http';
import { sleep, check } from 'k6';

const BASE_URL = (__ENV.BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const ADDRESS = __ENV.ADDRESS || 'Calle 10 # 20-30, Bogota';
const ENDPOINT = `${BASE_URL}/api/maps/geocode?address=${encodeURIComponent(ADDRESS)}`;

export const options = {
    vus: 80,
    duration: '30s',
};

export default function () {
    const res = http.get(ENDPOINT, {
        headers: {
            Accept: 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        },
    });

    check(res, {
        'status 200': (r) => r.status === 200,
        'has lat': (r) => {
            try {
                return typeof r.json('lat') === 'number';
            } catch (_error) {
                return false;
            }
        },
        'has lng': (r) => {
            try {
                return typeof r.json('lng') === 'number';
            } catch (_error) {
                return false;
            }
        },
    });

    sleep(1);
}
