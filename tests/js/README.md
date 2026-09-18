# Backend table navigation tests

Run from the repository root (Node.js 18+):

```sh
npm install --prefix tests/js
npm test --prefix tests/js
```

The tests use jsdom and the vendored DataTables, Select and SearchPanes libraries.
They exercise both client-side and simulated server-side Ajax tables; no Django
server or browser is needed. They do not rebuild or change production JS bundles.
