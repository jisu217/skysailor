from pathlib import Path
import re

def apply(path):
 p=Path(path);s=p.read_text()
 s=s.replace('const w=view.clientWidth;renderer.setSize(w,380);camera.aspect=w/380;', 'const w=view.clientWidth,h=Math.max(200,view.clientHeight);renderer.setSize(w,h);camera.aspect=w/h;')
 css='''<style>
html,body{width:100%;height:100%;margin:0;overflow:hidden}body{box-sizing:border-box;padding:12px}
body>div[id]{height:100%;display:flex;flex-direction:column;gap:8px;min-height:0}
body>div[id]>.gear-view{flex:1;min-height:0!important;height:auto!important;width:100%}
.viz-row,.viz-controls{margin:0;flex-shrink:0}.text-small,label{flex-shrink:0}canvas{display:block}
</style>'''
 s=s.replace('</html>',css+'</html>');p.write_text(s)
if __name__=='__main__':
 import sys
 for p in sys.argv[1:]:apply(p)
