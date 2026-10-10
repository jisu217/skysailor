from pathlib import Path
import trimesh,numpy as np,json,base64,gzip
out=Path(__file__).resolve().parent
gear=trimesh.load(out.parent/'gear-75pct/wheel-24t-75pct-2mm.stl')
def cyl(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation([0,0,z]);return m
upper=gear.copy();upper.apply_translation([0,0,6.5])
# Gear 0..2 / spool 2..6.5 / gear 6.5..8.5. Fixed tooth phase for concept only.
part=trimesh.boolean.union([gear,upper,cyl(1.9,8.5,4.25),cyl(7,.8,2.35),cyl(3,3.2,4.25),cyl(7,.8,6.15),cyl(1.5,3.2,-1.4),cyl(1.5,3.2,9.9)],engine='manifold')
assert part.is_watertight and part.is_winding_consistent and len(part.split())==1
printing=part.copy();printing.apply_translation([0,0,3]);printing.export(out/'double-gear-spool.stl')
# Packing keeps every triangle; no mesh decimation.
order=np.lexsort((np.arctan2(part.vertices[:,1],part.vertices[:,0]),np.round(part.vertices[:,2],6)));inv=np.empty_like(order);inv[order]=np.arange(len(order));v=part.vertices[order];f=inv[part.faces];f=np.take_along_axis(f,(np.arange(3)[None,:]+f.argmin(axis=1)[:,None])%3,axis=1);f=f[np.lexsort((f[:,2],f[:,1],f[:,0]))]
def pack(a,delta=False):
 raw=np.asarray(a,dtype='<i4' if delta else '<f4').ravel()
 if delta:raw=np.diff(raw,prepend=np.int32(0)).astype('<i4')
 return base64.b64encode(gzip.compress(raw.view('u1').reshape(-1,4).T.tobytes())).decode()
data={'part':{'v':pack(v),'f':pack(f,True)}}
fragment=(out/'viewer-template.html').read_text().replace('__DATA__',json.dumps(data))
# Standalone viewer retains complete geometry.
old=(out.parent/'hex-spools-r7-v1/assembly-preview.html').read_text();head=old[:old.index('<div id=')]
(out/'assembly-preview.html').write_text(head+fragment+'</html>')
(out/'dimensions.json').write_text(json.dumps(dict(gear_count=2,gear_teeth_each=24,gear_thickness_mm=2,spool_height_mm=4.5,spool_guide_radius_mm=7,spool_core_radius_mm=3,winding_width_mm=3,body_height_mm=8.5,shaft_diameter_mm=3,total_height_mm=14.5,stage='Concept assembly: existing tooth shape and equal phase. Worm, supports, print orientation and dual-mesh phasing not yet adapted.',triangles=len(part.faces)),indent=2))
print('Watertight:',part.is_watertight,'triangles:',len(part.faces),'bounds:',part.bounds.tolist())
