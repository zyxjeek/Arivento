from pathlib import Path
import sys,copy,re

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/历史目录/tools'))
from 制谱器 import *
ROOT=Path(__file__).resolve().parents[1]
NAME='Rail4K_0925_1'
LANES=['轨道一','轨道二','轨道三','轨道四']

def load(data):
    return json.loads(data.decode().split('$JSON')[1].rsplit('|#',1)[0])

def scm(d):
    return ('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()

def xml(data):
    r=ET.fromstring(data)
    for e in r.iter():e.tag=e.tag.split('}')[-1]
    return r

def register(c):
    TYPES[c['$Name']]=c['$Type']
    for x in c.get('$Components',[]):register(x)

def save(r,screen):
    for i,b in enumerate(r.iter('block')):b.set('id',screen+'_'+str(i))
    r.set('xmlns','http://www.w3.org/1999/xhtml');ET.indent(r,space='  ')
    return ET.tostring(r,encoding='utf-8')

def main():
    with zipfile.ZipFile(ROOT/'dist/Rail4K_0924_2.aia') as z:files={n:z.read(n) for n in z.namelist()}
    home=next(n for n in files if n.endswith('/Screen1.scm'));folder=home.rsplit('/',1)[0]
    d=load(files[home]);p=d['Properties']
    p['$Components'][0]['$Components'].append(component('触摸检测','Button',7,Text='触摸检测',Width=-2,Height=44,BackgroundColor=背景,TextColor=白色,Uuid='900'))
    TOP.clear();TYPES.clear();PROCS.clear();register(p)
    事件('触摸检测','Click',[block('controls_openAnotherScreen',values={'SCREEN':'TouchCheck'})])
    r=xml(files[home[:-4]+'.bky']);stamp=r.find('yacodeblocks');r.remove(stamp);r.extend(TOP);r.append(stamp)
    files[home]=scm(d);files[home[:-4]+'.bky']=save(r,'Screen1')
    d=load(files[folder+'/Play.scm']);p=d['Properties'];p['$Name']='TouchCheck';p['Title']='触摸检测'
    game=p['$Components'][0];info,lanes,actions=game['$Components']
    info.update(FontSize='14',Height='-1012',Text='按住不同轨道，检查同时按住数')
    actions['$Components'][0].update(Text='清零',Width='-1050')
    p['$Components']=[game]
    TOP.clear();TYPES.clear();PROCS.clear();register(p)
    for n,v in [('按住轨道',make_list(0,0,0,0)),('按下次数',make_list(0,0,0,0)),('当前按住',0),('最高按住',0)]:
        top(block('global_declaration',{'NAME':n},{'VALUE':v}),'')
    PROCS.update({'显示检测':[],'重置检测':[]})
    过程('显示检测',[
        put('当前按住',add(*[item(g('按住轨道'),j) for j in range(1,5)])),
        iff(compare('GT',g('当前按住'),g('最高按住')),[put('最高按住',g('当前按住'))]),
        设('信息',join('当前按住 ',g('当前按住'),' / 4    最高 ',g('最高按住'),'\n按下次数：',item(g('按下次数'),1),' / ',item(g('按下次数'),2),' / ',item(g('按下次数'),3),' / ',item(g('按下次数'),4)))])
    过程('重置检测',[put('按住轨道',make_list(0,0,0,0)),put('按下次数',make_list(0,0,0,0)),put('最高按住',0),*[设(n,-16052192,'BackgroundColor') for n in LANES],call('显示检测')])
    事件('TouchCheck','Initialize',[call('重置检测')])
    事件('重开','Click',[call('重置检测')])
    事件('返回','Click',[block('controls_closeScreen')])
    for j,n in enumerate(LANES,1):
        事件(n,'TouchDown',[改(g('按住轨道'),j,1),改(g('按下次数'),j,add(item(g('按下次数'),j),1)),设(n,-11084049,'BackgroundColor'),call('显示检测')],['横坐标','纵坐标'])
        事件(n,'TouchUp',[改(g('按住轨道'),j,0),设(n,-16052192,'BackgroundColor'),call('显示检测')],['横坐标','纵坐标'])
    r=ET.Element('xml');r.extend(TOP)
    for i,b in enumerate(TOP):b.set('x',str(40+i//10*470));b.set('y',str(40+i%10*120))
    r.append(copy.deepcopy(stamp));files[folder+'/TouchCheck.bky']=save(r,'TouchCheck');files[folder+'/TouchCheck.scm']=scm(d)
    for n in list(files):
        if n.endswith('.scm'):
            d=load(files[n]);d['Properties'].update(VersionCode='22',VersionName='0925.1-test');files[n]=scm(d)
        if n.endswith('project.properties'):
            s=files[n].decode()
            for k,v in [('name',NAME),('versioncode','22'),('versionname','0925.1-test')]:s=re.sub(r'(?m)^'+k+r'=.*',k+'='+v,s)
            files[n]=s.encode()
    dest=ROOT/'archive/多押排查_0925'
    dest.mkdir(parents=True,exist_ok=True)
    out=dest/f'{NAME}.aia'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data);f=dest/'native'/NAME/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    print(out)

if __name__=='__main__':main()
