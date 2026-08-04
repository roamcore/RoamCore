'use strict';
'require ui';
'require view';

return view.extend({
    render: function() {
        return E('div', { 'class': 'cbi-map' }, [
            E('h2', {}, 'RoamCore'),
            E('div', { 'class': 'cbi-section' }, [
                E('p', {}, [
                    'RoamCore is preinstalled on this device. ' +
                    'Open the ',
                    E('a', { href: '/cgi-bin/luci/admin/status/roamcore' }, 'RoamCore status'),
                    ' page to verify the networking API is responding.'
                ])
            ])
        ]);
    },

    load: function() { return Promise.resolve(); },
    handleSave: function() { return Promise.resolve(); },
    handleSaveApply: null,
    handleReset: null
});