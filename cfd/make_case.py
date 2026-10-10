"""Build a conforming 3-D shell/fluid mesh and a reproducible OpenFOAM case.
Run inside the CFD image with /usr/bin/python3 (Debian's gmsh bindings).
"""
import argparse,json,math
from pathlib import Path
import gmsh

p=argparse.ArgumentParser();p.add_argument('--case',default='/case/coarse');p.add_argument('--surface-size',type=float,default=.004);p.add_argument('--speed',type=float,default=1.6);p.add_argument('--iterations',type=int,default=600);args=p.parse_args()
case=Path(args.case)
if case.exists() and any(child.is_dir() and child.name.replace('.', '',1).isdigit() and float(child.name)>0 for child in case.iterdir()):
 raise RuntimeError('Case contains solution fields. Choose a new case directory to preserve results.')
case.mkdir(parents=True,exist_ok=True)
for d in ['0','constant','system']:(case/d).mkdir(exist_ok=True)
# Existing outer dome: R=.12 m, rise=.04 m, sphere R=.20 m, centre z=-.16 m.
# Assumed 1 mm shell thickness, explicitly recorded for this first CFD experiment.
gmsh.initialize();gmsh.option.setNumber('General.NumThreads',1);gmsh.model.add('shallow_dome')
occ=gmsh.model.occ
outer=occ.addSphere(0,0,-.16,.2);inner=occ.addSphere(0,0,-.16,.199)
shell,_=occ.cut([(3,outer)],[(3,inner)])
slab=occ.addBox(-.25,-.25,0,.5,.5,.06)
shell,_=occ.intersect(shell,[(3,slab)])
box=occ.addBox(-.96,-.96,-.96,1.92,1.92,2.88)
fluid,_=occ.cut([(3,box)],shell);occ.synchronize()
surfaces=gmsh.model.getBoundary(fluid,oriented=False)
patches={'inlet':[],'outlet':[],'sides':[],'dome':[]}
for dim,tag in surfaces:
 x0,y0,z0,x1,y1,z1=gmsh.model.getBoundingBox(dim,tag)
 if abs(z0+.96)<1e-5 and abs(z1+.96)<1e-5:name='inlet'
 elif abs(z0-1.92)<1e-5 and abs(z1-1.92)<1e-5:name='outlet'
 elif any(abs(a-b)<1e-5 and abs(abs(a)-.96)<1e-5 for a,b in [(x0,x1),(y0,y1)]):name='sides'
 else:name='dome'
 patches[name].append(tag)
for i,(name,tags) in enumerate(patches.items(),1):
 if not tags:raise RuntimeError(f'Missing boundary {name}')
 gmsh.model.addPhysicalGroup(2,tags,i);gmsh.model.setPhysicalName(2,i,name)
gmsh.model.addPhysicalGroup(3,[tag for dim,tag in fluid],10);gmsh.model.setPhysicalName(3,10,'fluid')
d=gmsh.model.mesh.field.add('Distance');gmsh.model.mesh.field.setNumbers(d,'FacesList',patches['dome'])
t=gmsh.model.mesh.field.add('Threshold')
for key,value in [('InField',d),('SizeMin',args.surface_size),('SizeMax',.14),('DistMin',.004),('DistMax',.30)]:gmsh.model.mesh.field.setNumber(t,key,value)
w=gmsh.model.mesh.field.add('Box')
for key,value in [('VIn',.035),('VOut',.14),('XMin',-.20),('XMax',.20),('YMin',-.20),('YMax',.20),('ZMin',.02),('ZMax',1.0),('Thickness',.08)]:gmsh.model.mesh.field.setNumber(w,key,value)
rim=[]
for dim,tag in gmsh.model.getEntities(1):
 bb=gmsh.model.getBoundingBox(dim,tag)
 if abs(bb[2])<1e-5 and abs(bb[5])<1e-5:rim.append(tag)
e=gmsh.model.mesh.field.add('Distance');gmsh.model.mesh.field.setNumbers(e,'EdgesList',rim);gmsh.model.mesh.field.setNumber(e,'NNodesByEdge',400)
et=gmsh.model.mesh.field.add('Threshold')
for key,value in [('InField',e),('SizeMin',.0015),('SizeMax',.14),('DistMin',.001),('DistMax',.08)]:gmsh.model.mesh.field.setNumber(et,key,value)
m=gmsh.model.mesh.field.add('Min');gmsh.model.mesh.field.setNumbers(m,'FieldsList',[t,w,et]);gmsh.model.mesh.field.setAsBackgroundMesh(m)
for key,value in [('Mesh.MeshSizeFromPoints',0),('Mesh.MeshSizeFromCurvature',0),('Mesh.MeshSizeExtendFromBoundary',0),('Mesh.Algorithm3D',1),('Mesh.OptimizeThreshold',0.7),('Mesh.MshFileVersion',2.2),('Mesh.Binary',0)]:gmsh.option.setNumber(key,value)
gmsh.model.mesh.generate(3);gmsh.model.mesh.optimize('')
gmsh.write(str(case/'mesh.msh'));nodes=len(gmsh.model.mesh.getNodes()[0]);gmsh.finalize()

def write(path,body,cls='dictionary',name=None):
 target=case/path
 target.write_text('FoamFile\n{\n version 2.0;\n format ascii;\n class '+cls+';\n object '+(name or target.name)+';\n}\n'+body+'\n')
write('constant/transportProperties','transportModel Newtonian;\nnu [0 2 -1 0 0 0 0] 1.5e-5;')
write('constant/turbulenceProperties','simulationType RAS;\nRAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }')
U=args.speed;k=1.5*(.01*U)**2;omega=math.sqrt(k)/(.09**.25*.024)
def field(name,dim,value,bcs,vector=False):
 write('0/'+name,f'dimensions {dim};\ninternalField uniform {value};\nboundaryField\n{{\n'+bcs+'\n}', 'volVectorField' if vector else 'volScalarField')
field('U','[0 1 -1 0 0 0 0]',f'(0 0 {U})',f'inlet {{type fixedValue; value uniform (0 0 {U});}}\noutlet {{type inletOutlet; inletValue uniform (0 0 {U}); value uniform (0 0 {U});}}\nsides {{type slip;}}\ndome {{type noSlip;}}',True)
field('p','[0 2 -2 0 0 0 0]','0','inlet {type zeroGradient;}\noutlet {type fixedValue; value uniform 0;}\nsides {type zeroGradient;}\ndome {type zeroGradient;}')
for name,value,dim,wall in [('k',k,'[0 2 -2 0 0 0 0]','kqRWallFunction'),('omega',omega,'[0 0 -1 0 0 0 0]','omegaWallFunction'),('nut',0,'[0 2 -1 0 0 0 0]','nutkWallFunction')]:
 bc=f'inlet {{type fixedValue; value uniform {value};}}\noutlet {{type inletOutlet; inletValue uniform {value}; value uniform {value};}}\nsides {{type zeroGradient;}}\ndome {{type {wall}; value uniform {value};}}'
 if name=='nut':bc='inlet {type calculated; value uniform 0;}\noutlet {type calculated; value uniform 0;}\nsides {type calculated; value uniform 0;}\ndome {type nutkWallFunction; value uniform 0;}'
 field(name,dim,str(value),bc)
write('system/fvSchemes','''ddtSchemes { default steadyState; }
gradSchemes { default cellLimited Gauss linear 1; }
divSchemes { default none; div(phi,U) bounded Gauss linearUpwind grad(U); div(phi,k) bounded Gauss upwind; div(phi,omega) bounded Gauss upwind; div((nuEff*dev2(T(grad(U))))) Gauss linear; }
laplacianSchemes { default Gauss linear limited 0.5; }
interpolationSchemes { default linear; }
snGradSchemes { default limited 0.5; }
wallDist { method meshWave; }''')
write('system/fvSolution','''solvers {
 p { solver GAMG; tolerance 1e-7; relTol 0.05; smoother GaussSeidel; }
 "(U|k|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0.05; }
}
SIMPLE { nNonOrthogonalCorrectors 2; consistent yes; }
relaxationFactors { fields {p 0.25;} equations {U 0.5; k 0.5; omega 0.5;} }''')
write('system/controlDict',f'''application simpleFoam;
startFrom latestTime; startTime 0; stopAt endTime; endTime {args.iterations}; deltaT 1;
writeControl timeStep; writeInterval 100; purgeWrite 2;
writeFormat ascii; writePrecision 8; writeCompression off; timeFormat general; timePrecision 6; runTimeModifiable true;
functions {{
 drag {{ type forceCoeffs; libs ("libforces.so"); patches (dome); rho rhoInf; rhoInf 1.225; CofR (0 0 0); liftDir (1 0 0); dragDir (0 0 1); pitchAxis (0 1 0); magUInf {U}; lRef .24; Aref {math.pi*.12**2}; writeControl timeStep; writeInterval 1; }}
 yPlus {{type yPlus; libs ("libfieldFunctionObjects.so"); writeControl writeTime;}}
 planes {{type surfaces; libs ("libsampling.so"); writeControl writeTime; surfaceFormat raw; fields (p U); interpolationScheme cellPoint; surfaces ( midplane {{type cuttingPlane; planeType pointAndNormal; pointAndNormalDict {{point (0 0 0); normal (0 1 0);}} interpolate true;}} );}}
}}''')
(case/'metadata.json').write_text(json.dumps(dict(speed_m_s=U,diameter_m=.24,rise_m=.04,shell_thickness_m=.001,air_density=1.225,nu=1.5e-5,reynolds=U*.24/1.5e-5,surface_size_m=args.surface_size,rim_size_m=.0015,mesh_method='Gmsh Delaunay with rim refinement, barycentric tetrahedron-to-hexahedron subdivision',nodes_before_hex_subdivision=nodes,solver='simpleFoam / steady incompressible RANS kOmegaSST',inlet_turbulence_intensity=.01,inlet_length_scale_m=.024,domain=[[-.96,-.96,-.96],[.96,.96,1.92]],limitations=['Fixed dome only; no payload or cables','Assumed 1 mm shell thickness','Steady RANS cannot resolve unsteady wake','No boundary-layer prism inflation in initial mesh; yPlus and mesh sensitivity must be evaluated','Do not calibrate MuJoCo until force and grid convergence are assessed']),indent=2)+'\n')
print('CASE READY',str(case),nodes,flush=True)
