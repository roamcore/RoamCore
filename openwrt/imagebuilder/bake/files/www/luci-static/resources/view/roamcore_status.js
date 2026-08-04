'use strict';
'require ui';
'require view';
'require dom';
'require rpc';

var callGetStatus = rpc.declare({
    object: 'luci',
    method: 'getStatus'
});

return view.extend({
    load: function() {
        return Promise.all([
            callGetStatus(),
            this.fetchApi()
        ]);
    },

    fetchApi: function() {
        // Best-effort fetch from the local RoamCore API. The router runs
        // the API on :8080 by default; if it's down (rare) we still
        // render the LuCI status so the user can recover.
        return new Promise(function(resolve) {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', 'http://127.0.0.1:8080/api/v1/status', true);
            xhr.timeout = 2000;
            xhr.onload = function() {
                try { resolve(JSON.parse(xhr.responseText)); }
                catch (e) { resolve(null); }
            };
            xhr.onerror = xhr.ontimeout = function() { resolve(null); };
            xhr.send();
        });
    },

    render: function(data) {
        var api = data && data[1];
        var luciStatus = data && data[0];
        var view = this;

        var root = E('div', { 'class': 'cbi-map' }, [
            E('h2', {}, 'RoamCore status'),
            E('div', { 'class': 'cbi-section' }, [
                E('h3', {}, 'RoamCore networking API'),
                api ? E('p', {}, [
                    E('strong', {}, 'State: '),
                    api.state || 'unknown'
                ]) : E('p', { 'class': 'alert-message warning' },
                    'The RoamCore API is not reachable on this device. ' +
                    'Check that /etc/init.d/roamcore-api is enabled and running.'),
                E('p', {}, [
                    E('strong', {}, 'Home Assistant target: '),
                    api && api.ha_host ? api.ha_host : '(not configured — run the first-boot wizard)'
                ]),
                E('p', {}, [
                    E('strong', {}, 'API endpoint: '),
                    E('code', {}, 'http://' + (window.location.hostname) + ':8080/api/v1/status')
                ])
            ]),
            E('div', { 'class': 'cbi-section' }, [
                E('h3', {}, 'OpenWrt system'),
                E('ul', {}, [
                    E('li', {}, [
                        E('strong', {}, 'Hostname: '),
                        luciStatus && luciStatus.hostname || '—'
                    ]),
                    E('li', {}, [
                        E('strong', {}, 'Model: '),
                        luciStatus && luciStatus.model || '—'
                    ]),
                    E('li', {}, [
                        E('strong', {}, 'Firmware: '),
                        luciStatus && luciStatus.firmware || '—'
                    ]),
                    E('li', {}, [
                        E('strong', {}, 'Uptime: '),
                        luciStatus && luciStatus.uptime || '—'
                    ])
                ])
            ])
        ]);

        return root;
    },

    handleSave: function() { return Promise.resolve(); },
    handleSaveApply: null,
    handleReset: null
});