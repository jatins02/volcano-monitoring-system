import {test} from 'node:test';
import assert from 'node:assert/strict';
import {LabController,matches} from '../../frontend/src/controller';
import {ApiError,session} from '../../frontend/src/api';
import {RULES_SHA256} from '../../frontend/src/generated-rules';
const sid='00000000-0000-0000-0000-000000000001',jid='00000000-0000-0000-0000-000000000002';
const empty=()=>({id:sid,generation:0,revision:0,rule_hash:RULES_SHA256,samples:[],latest_job:null,last_successful_result:null});
function fixture(){let s:any=empty(),calls=0,release:()=>void=()=>{};let hold=false;const storage={getItem:()=>null,setItem:()=>{}};const api:any={health:async()=>({available:true,rule_hash:RULES_SHA256}),create:async()=>structuredClone(s),session:async()=>structuredClone(s),submit:async(_:any,action:string,rows:any[])=>{calls++;if(action!=='retry'){s.revision+=rows.length;s.samples.push(...rows);}const j={id:jid,session:sid,generation:s.generation,revision:s.revision,rule_hash:RULES_SHA256,input_hash:'hash',status:'queued'};s.latest_job=j;return j;},reset:async()=>{s={...empty(),generation:s.generation+1};return s;},job:async()=>{if(hold)await new Promise<void>(r=>{release=r;});return {...s.latest_job,status:'failed',error_message:'intentional failure'};}};return{controller:new LabController(api,storage,1),api,get session(){return s;},get calls(){return calls;},hold:()=>{hold=true;},release:()=>{hold=false;release();}};}
const input={values:[20,20,20,20],connectivity_mask:15,fault_injection:false};
test('double Apply is locked synchronously and failed accepted history is retained',async()=>{const f=fixture();await f.controller.initialize();const first=f.controller.commit([input]);assert.equal(await f.controller.commit([input]),false);await first;assert.equal(f.calls,1);assert.equal(f.controller.state.session?.revision,1);assert.match(f.controller.state.error??'',/intentional/);});
test('Retry re-evaluates without another reading',async()=>{const f=fixture();await f.controller.initialize();await f.controller.commit([input]);await f.controller.commit([],'retry');assert.equal(f.calls,2);assert.equal(f.session.revision,1);});
test('reset invalidates an in-flight result even when transport ignores abort',async()=>{const f=fixture();await f.controller.initialize();f.hold();const first=f.controller.commit([input]);await new Promise(r=>setTimeout(r,5));await f.controller.reset();f.release();await first;assert.equal(f.controller.state.session?.generation,1);assert.equal(f.controller.state.session?.revision,0);assert.equal(f.controller.state.displayed,null);assert.equal(f.controller.state.error,null);});
test('historical view cannot submit and Pause prevents following commits',async()=>{const f=fixture();await f.controller.initialize();f.controller.history(0);await f.controller.commit([input]);assert.equal(f.calls,0);f.controller.history(null);f.hold();const p=f.controller.play([input,input]);await new Promise(r=>setTimeout(r,5));f.controller.pause();f.release();await p;assert.equal(f.calls,1);});
test('409 refreshes shared session without silently applying stale draft',async()=>{const f=fixture();await f.controller.initialize();f.api.submit=async()=>{throw new ApiError(409,'STALE');};await f.controller.commit([input]);assert.match(f.controller.state.message,/Shared session changed/);assert.equal(f.session.revision,0);});
test('result guards reject wrong session, generation, revision, input hash and rule hash',()=>{const s:any={...empty(),revision:1};const p:any={id:jid,session:sid,generation:0,revision:1,input_hash:'a',rule_hash:RULES_SHA256};assert.equal(matches({provenance:p} as any,s,p),true);for(const [key,value] of Object.entries({session:jid,generation:1,revision:2,input_hash:'b',rule_hash:'wrong'})){assert.equal(matches({provenance:{...p,[key]:value}} as any,s,p),false,key);}});
test('malformed accepted history is rejected at network boundary',()=>{assert.throws(()=>session({...empty(),revision:1}),/Incomplete/);});
import recorded from './result-fixture.json';
import {result as decodeResult} from '../../frontend/src/api';
import {escapeHtml,reportHtml} from '../../frontend/src/exports';
import {SCENARIOS} from '../../frontend/src/scenarios';
import {validDraft} from '../../frontend/src/controls';
test('actual saved result is accepted; missing native rows and unknown bits fail closed',()=>{assert.equal(decodeResult(recorded).hardware.length,11);let bad=structuredClone(recorded);bad.assembly.records.pop();assert.throws(()=>decodeResult(bad),/Incomplete native/);bad=structuredClone(recorded);bad.hardware[0]!.buses[1]=-1;assert.throws(()=>decodeResult(bad),/Malformed buses/);});
test('HTML exports escape raw output and keep full revision provenance',()=>{assert.equal(escapeHtml('<script>"&'), '&lt;script&gt;&quot;&amp;');const r=structuredClone(recorded);r.tool_outputs.assembly.stdout='<script>alert(1)</script>';const html=reportHtml({...empty(),revision:11} as any,r as any);assert(!html.includes('<script>'));assert(html.includes('&lt;script&gt;'));assert(html.includes('confirmed revision 11'));});
test('all deterministic scenarios stay within explicit input contracts',()=>{assert.equal(SCENARIOS.length,6);for(const scenario of SCENARIOS)for(const row of scenario.samples)assert(validDraft({values:row.values.map(String),mask:row.connectivity_mask,fault:row.fault_injection}));assert.equal(validDraft({values:['','20','20','20'],mask:15,fault:false}),false);assert.equal(validDraft({values:['101','20','20','20'],mask:15,fault:false}),false);});

import {createElement} from '../../frontend/node_modules/react/index.js';
import {renderToStaticMarkup} from '../../frontend/node_modules/react-dom/server.node.js';
import {LogicDiagram,logicSignals} from '../../frontend/src/logic-diagram';
import type {Snapshot} from '../../frontend/src/types';
import truthTable from '../fixtures/truth_table.json';
import sensorCases from '../fixtures/sensor_cases.json';
test('digital schematic covers all 16 combinations and all threshold/fault fixtures independently of assembly',()=>{
  for(const fixture of [...truthTable.cases,...sensorCases.cases]){
    const sample={...fixture.input,...fixture.expected} as Snapshot;
    const signals=logicSignals(sample);
    assert.equal(signals.sums[0]!+signals.sums[1]!,fixture.expected.k,fixture.id);
    const html=renderToStaticMarkup(createElement(LogicDiagram,{sample}));
    for(const [i,name] of ['V','T','G','A'].entries()){
      assert(html.includes(`data-input="${name}" data-level="${(fixture.expected.raw_mask>>i)&1}"`),fixture.id);
    }
    for(const warning of ['NORMAL','WATCH','DANGER']){
      assert(html.includes(`data-output="${warning}" data-level="${+(fixture.expected.warning===warning)}"`),fixture.id);
    }
    if(!sample.valid)assert.deepEqual(signals.effective,[0,0,0,0]);
  }
});
test('empty schematic keeps all digital inputs and outputs unknown',()=>{
  assert.deepEqual(logicSignals().raw,[undefined,undefined,undefined,undefined]);
  const html=renderToStaticMarkup(createElement(LogicDiagram,{}));
  assert.equal((html.match(/data-level="\?"/g)??[]).length,8);
  assert(html.includes('NO DATA'));
});

import {AssemblyOutput,AssemblyStatistics,AssemblyComparison,AssemblyView} from '../../frontend/src/assembly-view';
import {presentationStatus} from '../../frontend/src/presentation';
import type {Result} from '../../frontend/src/types';
test('Code defaults to a labelled teaching example without runtime metadata',()=>{
  const html=renderToStaticMarkup(createElement(AssemblyView,{result:recorded as Result,diagnostic:null,sample:recorded.hardware[0] as Snapshot,historical:false}));
  assert(html.includes('Teaching example'));
  assert(html.includes('classify_reading:'));
  assert(html.includes('Results use the full assembly program.'));
  for(const value of [recorded.provenance.id,recorded.provenance.source_sha256,'stdout','B0–B5','Source SHA256'])assert(!html.includes(value));
});
test('Output selects the actual assembly record, including historical readings',()=>{
  const result=structuredClone(recorded) as Result;
  result.assembly.records[0]!.warning='FAULT';
  result.assembly.records[0]!.fault=true;
  const html=renderToStaticMarkup(createElement(AssemblyOutput,{result,sample:result.hardware[0]}));
  assert(html.includes('Reading 1'));
  assert(html.includes('FAULT'));
  assert(html.includes('excluded from statistics'));
  assert(!html.includes('NORMAL'));
});
test('statistics retain assembly averages and full-session scope, including all-fault sessions',()=>{
  const result=structuredClone(recorded) as Result;
  result.assembly.summary.statistics.V!.average_x100=1234;
  let html=renderToStaticMarkup(createElement(AssemblyStatistics,{result}));
  assert(html.includes('All 11 readings'));
  assert(html.includes('12.34'));
  result.assembly.summary.valid_samples=0;
  for(const stats of Object.values(result.assembly.summary.statistics))Object.assign(stats,{count:0,minimum:null,maximum:null,sum:0,average_x100:null});
  html=renderToStaticMarkup(createElement(AssemblyStatistics,{result}));
  assert(html.includes('NO VALID DATA'));
  assert(!html.includes('12.34'));
});
test('new mismatch remains visible alongside an older successful result',()=>{
  const html=renderToStaticMarkup(createElement(AssemblyComparison,{result:recorded as Result,diagnostic:recorded as Result}));
  assert(html.includes('results differ'));
  assert(html.includes('Previous confirmed results'));
  assert(!html.includes('agree on every reading'));
  const firstMismatch=renderToStaticMarkup(createElement(AssemblyComparison,{result:null,diagnostic:recorded as Result}));
  assert(firstMismatch.includes('No confirmed result is available.'));
  assert(!firstMismatch.includes('Previous confirmed results'));
});
test('short status distinguishes pending, history, stale output and missing tools',()=>{
  const state=fixture().controller.state;
  assert.match(presentationStatus(state),/tools unavailable/);
  state.health={available:true,issues:[],rule_hash:RULES_SHA256,versions:{}};
  assert.equal(presentationStatus(state),'No readings yet');
  state.session={...empty(),revision:12};
  state.displayed=recorded as Result;
  assert.match(presentationStatus(state),/Retry/);
  state.pending={revision:12} as any;
  assert.match(presentationStatus(state),/Evaluating reading 12/);
  state.pending=null;state.historical=0;
  assert.match(presentationStatus(state),/Viewing saved reading 1/);
  state.error='failed';
  assert.match(presentationStatus(state),/previous confirmed/);
});
