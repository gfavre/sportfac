// Copy the pinned npm distribution; no CDN or runtime download is needed.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const source = path.join(root, 'node_modules/jodit');
const target = path.join(root, 'sportfac/backend/static/backend/vendor/jodit');
fs.mkdirSync(target, {recursive: true});
for (const [from, to] of [
    ['es2021/jodit.min.js', 'jodit.min.js'],
    ['es2021/jodit.min.css', 'jodit.min.css'],
    ['LICENSE.txt', 'LICENSE.txt'],
]) fs.copyFileSync(path.join(source, from), path.join(target, to));
