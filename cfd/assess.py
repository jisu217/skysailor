"""Compare fixed-body experiments without authorizing free-flight calibration."""
import argparse
import json
from pathlib import Path


def assess(results):
    base=results.get('layered-v6');fine=results.get('layered-refined')
    negative=results.get('tilt-minus10');positive=results.get('tilt-plus10')
    passed=lambda r:bool(r and r['status']=='single_mesh_converged_not_validated')
    report={'upright_converged':passed(base),'meridian_comparison':None,'tilt_comparison':None,
            'free_flight_calibration_ready':False,
            'remaining_validation':['Wall-normal and azimuthal refinement','Domain-size sensitivity','Speed dependence','Unsteady wake and moving-body coupling']}
    if base and fine:
        difference=abs(base['mean_cd_last_100']-fine['mean_cd_last_100'])/max(abs(fine['mean_cd_last_100']),1e-12)
        report['meridian_comparison']={'relative_cd_difference':difference,'tolerance':.03,'both_converged':passed(base) and passed(fine),'within_tolerance':difference<.03,
                                      'note':'Meridional surface refinement only; same first layer and azimuthal resolution. Not a grid-independence proof.'}
    if negative and positive:
        mn=negative['aero_loads']['pitch_moment_com_Nm'];mp=positive['aero_loads']['pitch_moment_com_Nm']
        cn=negative['mean_cd_last_100'];cp=positive['mean_cd_last_100']
        report['tilt_comparison']={'both_converged':passed(negative) and passed(positive),
                                  'mirror_cd_difference':abs(cn-cp)/max(abs(cn),abs(cp),1e-12),
                                  'mirror_moment_error':abs(mn+mp)/max(abs(mn),abs(mp),1e-12),
                                  'both_static_restoring':mn>0 and mp<0,
                                  'negative_my_com_Nm':mn,'positive_my_com_Nm':mp,
                                  'note':'Static tendency at a centred reference COM only; no dynamic stability conclusion.'}
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('cases',nargs='?',default='cfd/cases');a=p.parse_args()
    root=Path(a.cases);results={}
    for name in ['layered-v6','layered-refined','tilt-minus10','tilt-plus10']:
        path=root/name/'result.json'
        if path.exists():results[name]=json.loads(path.read_text())
    report=assess(results)
    (root/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
