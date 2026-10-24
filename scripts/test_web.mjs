// Bundle test-only TypeScript with the already locked Vite esbuild dependency.
import {build} from '../frontend/node_modules/esbuild/lib/main.js';
import {mkdir} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
await mkdir('runtime/web-tests',{recursive:true});
// Keep hooks and the server renderer on the same installed React instance.
const reactExternal={name:'react-external',setup(builder){
  builder.onResolve({filter:/^react(?:\/jsx(?:-dev)?-runtime)?$/},({path})=>({
    path:new URL(`../frontend/node_modules/${path==='react'?'react/index.js':`${path}.js`}`,import.meta.url).pathname,
    external:true,
  }));
}};
await build({entryPoints:['tests/web/controller.test.ts'],bundle:true,loader:{'.s':'text'},plugins:[reactExternal],platform:'node',format:'esm',external:['../../frontend/node_modules/react/index.js','../../frontend/node_modules/react-dom/server.node.js'],outfile:'runtime/web-tests/controller.test.mjs'});
const run=spawnSync(process.execPath,['--test','runtime/web-tests/controller.test.mjs'],{stdio:'inherit'});
process.exitCode=run.status??1;
