// Execute the actual appointment script with a small DOM and deferred fetches.
// No browser, WhatsApp session, or network connection is used.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync(path.join(__dirname, 'templates/patient_info.html'), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];

function setup() {
    const handlers = {}, pending = [], opened = [];
    const date = {
        value: '', min: '2026-11-12', validity: '',
        setCustomValidity(value) { this.validity = value; }, reportValidity() {},
        addEventListener(event, fn) { handlers[event] = fn; },
    };
    const options = ['', '8:00 AM - 8:30 AM', '8:30 AM - 9:00 AM']
        .map(value => ({ value, textContent: value, dataset: {}, disabled: false }));
    const time = {
        value: options[1].value, options,
        get selectedOptions() { return options.filter(o => o.value === this.value); },
        setCustomValidity() {}, reportValidity() {}, addEventListener() {},
    };
    const status = { textContent: '', classList: { remove() {}, add() {} } };
    const values = { full_name: 'Audit & Test', age: '28', gender: 'Male', phone: '9000000000',
        referred_doctor: 'Audit Doctor', hospital_name: 'Test Clinic' };
    const form = {
        querySelector(selector) {
            const name = selector.match(/name="([^"]+)"/)[1];
            if (name === 'gender') assert.ok(selector.includes(':checked'));
            return { value: values[name], checked: true };
        },
        querySelectorAll() { return [{ value: 'NT Scan' }, { value: 'Whole Abdomen' }]; },
        addEventListener(event, fn) { handlers.submit = fn; },
    };
    vm.runInNewContext(script, {
        console, Intl, Date, Set, Array, Boolean, parseInt, encodeURIComponent,
        document: {
            addEventListener(event, fn) { fn(); },
            querySelector(selector) { return selector.includes('preferred_date') ? date : time; },
            getElementById(id) { return id === 'patientForm' ? form : status; },
        },
        fetch(url) { return new Promise(resolve => pending.push({ url, resolve })); },
        window: { open(...args) { opened.push(args); } },
    });
    return { date, time, status, handlers, pending, opened };
}

async function resolveRequest(request, booked = []) {
    request.resolve({ ok: true, json: () => Promise.resolve({
        booked_slots: booked, past_slots: [], clinic_today: '2026-11-12',
        is_closed: false, is_past_date: false,
    }) });
    await new Promise(resolve => setImmediate(resolve));
}

(async () => {
    // Each early-return path must invalidate any request for the previous date.
    for (const nextDate of ['', '2026-11-11', '2026-11-15']) {
        const s = setup();
        s.date.value = '2026-11-16'; s.handlers.change();
        s.date.value = nextDate; s.handlers.input();
        const before = JSON.stringify([s.status.textContent, s.date.validity, s.time.options]);
        await resolveRequest(s.pending[0], ['8:00 AM - 8:30 AM']);
        assert.equal(JSON.stringify([s.status.textContent, s.date.validity, s.time.options]), before);
    }
    // Responses arriving out of order must not replace the current date's state.
    const s = setup();
    s.date.value = '2026-11-16'; s.handlers.change();
    s.date.value = '2026-11-17'; s.handlers.change();
    await resolveRequest(s.pending[1], ['8:30 AM - 9:00 AM']);
    await resolveRequest(s.pending[0], ['8:00 AM - 8:30 AM']);
    assert.equal(s.time.options[1].disabled, false);
    assert.equal(s.time.options[2].disabled, true);

    s.time.value = '8:00 AM - 8:30 AM';
    s.handlers.submit({ preventDefault() { assert.fail('Valid booking unexpectedly blocked'); } });
    assert.equal(s.opened.length, 1);
    const [url, target, features] = s.opened[0];
    const parsed = new URL(url);
    assert.equal(parsed.origin, 'https://wa.me');
    assert.equal(parsed.pathname, '/919848204278');
    assert.equal(target, '_blank');
    assert.equal(features, 'noopener,noreferrer');
    for (const value of ['Audit & Test', '28', 'Male', '9000000000', 'Audit Doctor',
        'Test Clinic', '2026-11-17', '8:00 AM - 8:30 AM', 'NT Scan', 'Whole Abdomen', 'IST']) {
        assert.ok(parsed.searchParams.get('text').includes(value), value);
    }
    s.date.value = '2026-11-15'; s.handlers.change();
    let blocked = false;
    s.handlers.submit({ preventDefault() { blocked = true; } });
    assert.equal(blocked, true);
    assert.equal(s.opened.length, 1);
    console.log('PASS: stale responses, reversed responses, manual message and invalid submission checks');
})().catch(error => { console.error(error); process.exitCode = 1; });
