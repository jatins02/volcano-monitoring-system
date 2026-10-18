"""Actual CLI checks of both submitted core and GUI using independent fixtures."""
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
try:
    from .common import ROOT,read_json,run
    from .logisim import command
    from .bridge_proof import validate_exit
    from .circuit_dsl import Circuit
except ImportError:
    from common import ROOT,read_json,run
    from logisim import command
    from bridge_proof import validate_exit
    from circuit_dsl import Circuit


def status_word(expected: dict, mask: int) -> int:
    return (mask | int(expected['valid'])<<4 | expected['effective_mask']<<5 |
            expected['k']<<9 | expected['warning_code']<<12 | int(expected['emergency'])<<14 |
            int(expected['fault'])<<15 | expected['raw_mask']<<16 | expected['range_mask']<<20)


def check(root: Path=ROOT) -> int:
    cases=[]
    for name in ['truth_table.json','sensor_cases.json']:
        cases+=read_json(root/'tests/fixtures'/name)['cases']
    project=ET.parse(root/'circuit/volcano.circ').getroot()
    results={};expected=[]
    test=Circuit(project,'CombinationalCheck',[])
    for i,case in enumerate(cases):
        for kind in ['MonitorCore','MonitorGUI']:
            child=Circuit.__new__(Circuit);child.name=kind
            child.inputs=[(s,8) for s in 'VTGA']+[('mask',4)]
            node=project.find(f"circuit[@name='{kind}']")
            pins=[p for p in node.findall("comp[@name='Pin']") if p.find("a[@name='output']").get('val')=='true']
            child.outputs=[(p.find("a[@name='label']").get('val'),int(p.find("a[@name='width']").get('val'))) for p in pins]
            inputs={s:test.constant(8,case['input']['values'][j]) for j,s in enumerate('VTGA')}
            inputs['mask']=test.constant(4,case['input']['connectivity_mask'])
            outputs=test.instance(child,inputs,f'CASE_{i}_{kind}')
            results[f'case_{i}_{kind}']=outputs['status']
            expected.append(status_word(case['expected'],case['input']['connectivity_mask']))
    results['halt']=test.constant(1,1);test.finish(results)
    out=root/'runtime/stage3';out.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(project).write(out/'check.circ',encoding='utf-8',xml_declaration=True)
    result=run(command(root,['--clear-prefs',str(out/'check.circ'),'--tty','table,halt',
                             '--toplevel-circuit','CombinationalCheck']),cwd=root,timeout=30)
    (out/'stdout.txt').write_text(result.stdout);(out/'stderr.txt').write_text(result.stderr)
    validate_exit(result.returncode,result.stderr)
    lines=result.stdout.splitlines()
    if len(lines)!=1:raise ValueError('expected one settled combinational observation')
    cells=lines[0].split('\t')
    actual=[int(cell.replace(' ',''),2) for cell in cells]
    if actual!=expected:
        differences=[(i,a,e) for i,(a,e) in enumerate(zip(actual,expected)) if a!=e]
        raise ValueError(f'combinational mismatch: {differences[:5]} (actual={len(actual)},expected={len(expected)})')
    (out/'results.json').write_text(json.dumps({'case_count':len(cases),'core_and_gui_observations':len(expected),'expected':expected,'actual':actual},indent=2)+'\n')
    print(f'Combinational hardware: {len(cases)} independent fixture cases passed for core and GUI')
    return len(cases)


if __name__=='__main__':check()
