// Bundle test-only TypeScript with the already locked Vite esbuild dependency.
import {build} from '../frontend/node_modules/esbuild/lib/main.js';
import {mkdir} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
await mkdir('runtime/web-tests',{recursive:true});
await build({entryPoints:['tests/web/controller.test.ts'],bundle:true,platform:'node',format:'esm',outfile:'runtime/web-tests/controller.test.mjs'});
const run=spawnSync(process.execPath,['--test','runtime/web-tests/controller.test.mjs'],{stdio:'inherit'});
process.exitCode=run.status??1;
