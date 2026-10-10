import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import TwoSlopeNorm

def render_fields(case, metadata, result):
    plt.style.use("dark_background")
    def mask_shell(triang,x,z):
     # Reject any interpolated triangle edge crossing the shell mid-surface.
     mask=np.zeros(len(triang.triangles),dtype=bool)
     for j in range(3):
      ia=triang.triangles[:,j];ib=triang.triangles[:,(j+1)%3]
      ax=x[ia];az=z[ia]+.16;dx=x[ib]-ax;dz=z[ib]-z[ia]
      aa=dx*dx+dz*dz;bb=2*(ax*dx+az*dz);cc=ax*ax+az*az-.1995**2
      discriminant=bb*bb-4*aa*cc
      for sign in [-1,1]:
       t=(-bb+sign*np.sqrt(np.maximum(0,discriminant)))/(2*aa)
       mask|=(discriminant>=0)&(t>1e-6)&(t<1-1e-6)&(az+t*dz>.16)
     triang.set_mask(mask)
    
    # Plane samples are physical pressure and velocity fields, not force-arrow illustrations.
    raw=list(case.glob('postProcessing/planes/**/*.raw'))
    pressure=[p for p in raw if p.name.startswith('p_') or p.name.endswith('_p.raw')]
    velocity=[p for p in raw if p.name.startswith('U_') or p.name.endswith('_U.raw')]
    if pressure:
     sample=max(pressure,key=lambda p:p.stat().st_mtime);data=np.loadtxt(sample,comments='#',ndmin=2)
     coords=data[:,:3];press=data[:,3]*metadata['air_density']
     select=(abs(coords[:,0])<.45)&(coords[:,2]>-.30)&(coords[:,2]<.7)
     x,z=coords[select,0],coords[select,2];press=press[select]
     unique,index=np.unique(np.c_[x,z],axis=0,return_index=True);x,z=unique.T;press=press[index]
     triang=mtri.Triangulation(x,z)
     cx=x[triang.triangles].mean(axis=1);cz=z[triang.triangles].mean(axis=1)
     # Exclude triangles whose centres lie in the solid cap shell.
     mask_shell(triang,x,z)
     fig,ax=plt.subplots(figsize=(7,8),layout='constrained');plot=ax.tricontourf(triang,press,levels=np.linspace(-5,2,50),norm=TwoSlopeNorm(vmin=-5,vcenter=0,vmax=2),cmap='coolwarm',extend='both');fig.colorbar(plot,ax=ax,label='Gauge pressure (Pa)')
     xx=np.linspace(-.12,.12,300);zz=np.sqrt(.2**2-xx**2)-.16;ax.plot(xx,zz,color='white',lw=2)
     ax.set(xlabel='x (m)',ylabel='z (m)',title=f'CFD pressure / body plane / tilt {metadata.get("tilt_deg",0):g} deg\n'+result['status'],aspect='equal');fig.savefig(case/'pressure.png',dpi=150);plt.close(fig)
    if velocity:
     sample=max(velocity,key=lambda p:p.stat().st_mtime);data=np.loadtxt(sample,comments='#',ndmin=2)
     coords=data[:,:3];select=(abs(coords[:,0])<.45)&(coords[:,2]>-.30)&(coords[:,2]<.7)
     xyz=coords[select];vel=data[select,3:6];unique,index=np.unique(xyz[:,[0,2]],axis=0,return_index=True);x,z=unique.T;vel=vel[index]
     triang=mtri.Triangulation(x,z);cx=x[triang.triangles].mean(axis=1);cz=z[triang.triangles].mean(axis=1);mask_shell(triang,x,z)
     fig,ax=plt.subplots(figsize=(7,8),layout='constrained');plot=ax.tricontourf(triang,np.linalg.norm(vel,axis=1),levels=np.linspace(0,3,50),cmap='viridis',extend='max');fig.colorbar(plot,ax=ax,label='Velocity magnitude (m/s)')
     gridx=np.linspace(-.4,.4,160);gridz=np.linspace(-.25,.65,180);X,Z=np.meshgrid(gridx,gridz)
     ux=mtri.LinearTriInterpolator(triang,vel[:,0])(X,Z);uz=mtri.LinearTriInterpolator(triang,vel[:,2])(X,Z)
     # The streamline plotting grid is coarser than the 1 mm wall: stop
     # integration in a half-grid-diagonal band instead of crossing the shell.
     band=.5*np.hypot(gridx[1]-gridx[0],gridz[1]-gridz[0])
     wall=(abs(np.sqrt(X*X+(Z+.16)**2)-.1995)<band)&(Z>=-band)
     ux=np.ma.masked_where(wall,ux);uz=np.ma.masked_where(wall,uz)
     ax.streamplot(gridx,gridz,ux,uz,density=1.1,color='white',linewidth=.5,arrowsize=.65)
     xx=np.linspace(-.12,.12,300);zz=np.sqrt(.2**2-xx**2)-.16;ax.plot(xx,zz,color='#ffbf75',lw=2)
     ax.set(xlabel='x (m)',ylabel='z (m)',title=f'CFD velocity / body plane / tilt {metadata.get("tilt_deg",0):g} deg\n'+result['status'],aspect='equal');fig.savefig(case/'velocity.png',dpi=150);plt.close(fig)
