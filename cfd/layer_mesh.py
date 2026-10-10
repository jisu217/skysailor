"""Meridional boundary-layer mesh revolved into a conformal full 3-D grid.
The meridian uses (radius,z); full-azimuth cells do not enforce flow symmetry.
Run with the CFD image's /usr/bin/python3.
"""
import argparse,json,math
from pathlib import Path
import gmsh
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--surface-size',type=float,default=.003);p.add_argument('--first-layer',type=float,default=.0005);p.add_argument('--sectors',type=int,default=40);p.add_argument('--rise',type=float,default=.04);p.add_argument('--thickness',type=float,default=.001);a=p.parse_args()
if not 0<a.thickness<a.rise<=.12:raise ValueError('Require 0 < thickness < rise <= radius')
R=(.12**2+a.rise**2)/(2*a.rise);zc=a.rise-R;Ri=R-a.thickness;lip=math.sqrt(Ri**2-zc**2)
case=Path(a.case);case.mkdir(parents=True,exist_ok=True)
if (case/'postProcessing').exists():raise RuntimeError('Use a new case directory')
gmsh.initialize();gmsh.option.setNumber('General.NumThreads',1);gmsh.model.add('layered-meridian');g=gmsh.model.geo
pt=lambda r,z,h:g.addPoint(r,z,0,h)
center=pt(0,zc,.1);bottom=pt(0,-.96,.12);inner=pt(0,a.rise-a.thickness,a.surface_size);innerlip=pt(lip,0,a.surface_size/2);outerlip=pt(.12,0,a.surface_size/2);outer=pt(0,a.rise,a.surface_size);top=pt(0,1.92,.12);rtop=pt(.96,1.92,.12);rbottom=pt(.96,-.96,.12)
axis1=g.addLine(bottom,inner);inside=g.addCircleArc(inner,center,innerlip);rim=g.addLine(innerlip,outerlip);outside=g.addCircleArc(outerlip,center,outer);axis2=g.addLine(outer,top);outlet=g.addLine(top,rtop);side=g.addLine(rtop,rbottom);inlet=g.addLine(rbottom,bottom)
surface=g.addPlaneSurface([g.addCurveLoop([axis1,inside,rim,outside,axis2,outlet,side,inlet])]);g.synchronize()
wall=[inside,rim,outside]
bl=gmsh.model.mesh.field.add('BoundaryLayer')
gmsh.model.mesh.field.setNumbers(bl,'EdgesList',wall)
gmsh.model.mesh.field.setNumbers(bl,'FanNodesList',[innerlip,outerlip])
gmsh.option.setNumber('Mesh.BoundaryLayerFanElements',6)
for name,value in [('hwall_n',a.first_layer),('ratio',1.25),('thickness',.003),('Quads',1)]:gmsh.model.mesh.field.setNumber(bl,name,value)
gmsh.model.mesh.field.setAsBoundaryLayer(bl)
d=gmsh.model.mesh.field.add('Distance');gmsh.model.mesh.field.setNumbers(d,'EdgesList',wall);gmsh.model.mesh.field.setNumber(d,'NNodesByEdge',250)
t=gmsh.model.mesh.field.add('Threshold')
for name,value in [('InField',d),('SizeMin',a.surface_size),('SizeMax',.14),('DistMin',.008),('DistMax',.22)]:gmsh.model.mesh.field.setNumber(t,name,value)
w=gmsh.model.mesh.field.add('Box')
for name,value in [('VIn',.022),('VOut',.14),('XMin',0),('XMax',.23),('YMin',a.rise),('YMax',.85),('Thickness',.1)]:gmsh.model.mesh.field.setNumber(w,name,value)
axisfield=gmsh.model.mesh.field.add('Box')
for name,value in [('VIn',.001),('VOut',.14),('XMin',0),('XMax',.008),('YMin',a.rise-.016),('YMax',a.rise+.016),('Thickness',.005)]:gmsh.model.mesh.field.setNumber(axisfield,name,value)
m=gmsh.model.mesh.field.add('Min');gmsh.model.mesh.field.setNumbers(m,'FieldsList',[t,w,axisfield]);gmsh.model.mesh.field.setAsBackgroundMesh(m)
gmsh.option.setNumber('Mesh.Algorithm',6);gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0)
gmsh.model.mesh.generate(2)
gmsh.write(str(case/'meridian.msh'))
tags,xyz,_=gmsh.model.mesh.getNodes();rz={int(i):np.array(v[:2]) for i,v in zip(tags,np.array(xyz).reshape(-1,3))}
faces=[]
for kind,etags,nodes in zip(*gmsh.model.mesh.getElements(2)):
 size={2:3,3:4}.get(kind)
 if size is None:raise RuntimeError(f'Unsupported surface element {kind}')
 for vs in np.array(nodes).reshape(-1,size):
  vs=list(map(int,vs));points=np.array([rz[v] for v in vs]);signed=np.sum(points[:,0]*np.roll(points[:,1],-1)-points[:,1]*np.roll(points[:,0],-1))
  if signed<0:vs.reverse()
  faces.append(vs)
# Merge small convex corner-fan triangles in the meridian before revolution.
# Their union preserves all boundary edges and fluid volume.
def polygon_union(left,right):
 edges={}
 for vs in [left,right]:
  for u,v in zip(vs,vs[1:]+vs[:1]):
   key=tuple(sorted((u,v)))
   if key in edges:del edges[key]
   else:edges[key]=(u,v)
 nxt={u:v for u,v in edges.values()}
 if len(nxt)!=len(edges):return None
 start=next(iter(nxt));out=[start];node=nxt[start]
 while node!=start and len(out)<=len(edges):out.append(node);node=nxt.get(node,start)
 if len(out)!=len(edges):return None
 pp=np.array([rz[v] for v in out]);ee=np.roll(pp,-1,axis=0)-pp;cross=ee[:,0]*np.roll(ee[:,1],-1)-ee[:,1]*np.roll(ee[:,0],-1)
 return out if np.min(cross)>-1e-13 else None
def small_corner(vs):
 pp=np.array([rz[v] for v in vs]);c=pp.mean(axis=0)
 area=abs(np.sum(pp[:,0]*np.roll(pp[:,1],-1)-pp[:,1]*np.roll(pp[:,0],-1)))/2
 return abs(c[0]-(lip+.12)/2)<.008 and abs(c[1])<.008 and area<3e-7 and len(vs)<12
merged=0;eligible=[len(v)==3 for v in faces]
for attempt in range(64):
 adjacency={};pair=None
 for i,vs in enumerate(faces):
  if not eligible[i] or not small_corner(vs):continue
  for u,v in zip(vs,vs[1:]+vs[:1]):
   key=tuple(sorted((u,v)))
   if key in adjacency:
    j=adjacency[key];poly=polygon_union(faces[j],vs)
    if poly is not None:pair=(j,i,poly);break
   else:adjacency[key]=i
  if pair:break
 if pair is None:break
 j,i,poly=pair;faces[j]=poly;del faces[i];del eligible[i];merged+=1
print('Merged corner cells:',merged,flush=True)
edges={}
for patch,curves in [('dome',wall),('inlet',[inlet]),('outlet',[outlet]),('sides',[side])]:
 edges[patch]=[]
 for curve in curves:
  for kind,etags,nodes in zip(*gmsh.model.mesh.getElements(1,curve)):
   if kind!=1:raise RuntimeError('Only linear edges are supported')
   edges[patch].extend(np.array(nodes).reshape(-1,2).astype(int).tolist())
gmsh.finalize()
# Write native polyMesh: face deduplication avoids ad-hoc collapsed prism node orders.
points=[];lookup={}
def node(v,j):
 r,z=rz[v];j=0 if abs(r)<1e-10 else j%a.sectors;key=(v,j)
 if key not in lookup:
  theta=2*np.pi*j/a.sectors;lookup[key]=len(points);points.append(np.array([r*np.cos(theta),r*np.sin(theta),z]))
 return lookup[key]
allfaces=[];owner=[];neighbour=[];face_ids={};boundaries={name:set() for name in edges}
def clean(vs):return list(dict.fromkeys(vs))
def add_cell(fs):
 cell=len(centres);ids=set(v for f in fs for v in f);centroid=np.mean([points[v] for v in ids],axis=0);centres.append(centroid)
 for face in fs:
  face=clean(face)
  if len(face)<3:continue
  pp=np.array([points[v] for v in face]);normal=np.sum(np.cross(pp,np.roll(pp,-1,axis=0)),axis=0)
  if np.dot(normal,pp.mean(axis=0)-centroid)<0:face.reverse()
  key=tuple(sorted(face))
  if key in face_ids:
   i=face_ids[key]
   if neighbour[i]!=-1:raise RuntimeError('Non-manifold mesh')
   neighbour[i]=cell
  else:
   face_ids[key]=len(allfaces);allfaces.append(face);owner.append(cell);neighbour.append(-1)
centres=[]
for j in range(a.sectors):
 for index,vs in enumerate(faces):
  lo=[node(v,j) for v in vs];hi=[node(v,j+1) for v in vs]
  add_cell([lo,hi]+[[lo[k],lo[(k+1)%len(vs)],hi[(k+1)%len(vs)],hi[k]] for k in range(len(vs))])
for patch,es in edges.items():
 for j in range(a.sectors):
  for u,v in es:
   key=tuple(sorted(clean([node(u,j),node(v,j),node(v,j+1),node(u,j+1)])))
   if len(key)>=3:boundaries[patch].add(face_ids[key])
internal=sorted((i for i,n in enumerate(neighbour) if n>=0),key=lambda i:(owner[i],neighbour[i]));border=[i for i,n in enumerate(neighbour) if n<0]
if set(border)!=set.union(*boundaries.values()):raise RuntimeError('Unclassified boundary faces')
order=internal+[i for ids in boundaries.values() for i in sorted(ids)]
folder=case/'constant/polyMesh';folder.mkdir(parents=True,exist_ok=True)
def write(name,cls,body):
 (folder/name).write_text('FoamFile {version 2.0; format ascii; class '+cls+'; object '+name+';}\n'+body+'\n')
write('points','vectorField',str(len(points))+'\n(\n'+'\n'.join('('+ ' '.join(f'{v:.17g}' for v in xyz)+')' for xyz in points)+'\n)')
write('faces','faceList',str(len(order))+'\n(\n'+'\n'.join(str(len(allfaces[i]))+'('+ ' '.join(map(str,allfaces[i]))+')' for i in order)+'\n)')
for name,data,indices in [('owner',owner,order),('neighbour',neighbour,internal)]:write(name,'labelList',str(len(indices))+'\n(\n'+'\n'.join(str(data[i]) for i in indices)+'\n)')
offset=len(internal);body=[]
for name,ids in boundaries.items():
 body.append(f'{name} {{type {"wall" if name=="dome" else "patch"}; nFaces {len(ids)}; startFace {offset};}}');offset+=len(ids)
write('boundary','polyBoundaryMesh',str(len(body))+'\n(\n'+'\n'.join(body)+'\n)')
np.save(case/'mesh-centres.npy',np.array(centres))
(case/'mesh-metadata.json').write_text(json.dumps(dict(diameter_m=.24,rise_m=a.rise,shell_thickness_m=a.thickness,sphere_radius_m=R,mesh_method='Full 3D revolution of a meridional boundary-layer mesh',cells=len(centres),sectors=a.sectors,meridian_cells=len(faces),meridian_quads=sum(len(v)==4 for v in faces),surface_size_m=a.surface_size,first_layer_m=a.first_layer,boundary_layer_thickness_m=.003,layer_growth=1.25,domain_shape='cylinder',domain_radius_m=.96),indent=2)+'\n')
print('LAYERED MESH READY',len(centres),flush=True)
