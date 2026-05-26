import http from 'k6/http';
import { sleep, check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000/';
const TARGET_PATH = __ENV.TARGET_PATH || 'contrataciones';

export const options = {
    vus: 10,
    duration: '60s',
    
};


export default function () {
    const url = `${BASE_URL}${TARGET_PATH}`;
    const res = http.get(url);

    check(res, {
        'status 200': (r) => r.status === 200,
    });

    sleep(1);
}
