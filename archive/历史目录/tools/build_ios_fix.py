from 制谱器 import *
import argparse

def invoke(value):
    m = mut(name='复制列表')
    ET.SubElement(m, 'arg', name='原值')
    return block('procedures_callreturn', {'PROCNAME':'复制列表'}, {'ARG0':value}, mutation=m)

def copier():
    m = mut()
    ET.SubElement(m,'arg',name='原值')
    lm = mut()
    ET.SubElement(lm,'localname',name='副本')
    body = block('controls_do_then_return', values={'VALUE':get('副本')}, statements={'STM':[遍历('元素',get('原值'),[添(get('副本'),invoke(get('元素')))])]})
    value = block('local_declaration_expression',{'VAR0':'副本'},{'DECL0':make_list(),'RETURN':body},mutation=lm)
    return block('procedures_defreturn',{'NAME':'复制列表','VAR0':'原值'},{'RETURN':选(列表(get('原值')),value,get('原值'))},mutation=m)

def music_names(path):
    extensions = {'.mp3','.m4a','.aac','.wav','.ogg'}
    if path.suffix.lower() == '.aia':
        with zipfile.ZipFile(path) as z:
            return sorted(n[7:] for n in z.namelist() if n.startswith('assets/') and Path(n).suffix.lower() in extensions)
    return sorted(p.name for p in path.iterdir() if p.is_file() and p.suffix.lower() in extensions)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input',type=Path,default=ROOT/'dist/Rail4K_Multi_v4_CodeOnly.aia')
    p.add_argument('--output',type=Path,default=ROOT/'dist/Rail4K_Multi_v5_CodeOnly.aia')
    p.add_argument('--catalog',type=Path,default=ROOT/'Phigros_Music_3.20.0')
    a = p.parse_args()
    assert a.input.resolve() != a.output.resolve()
    names = music_names(a.catalog)
    catalog = ('\n'.join(names)+'\n').encode('utf-8')
    (ROOT/'docs/music_list.txt').write_bytes(catalog)
    TYPES.update(音乐输入='ListPicker',曲目文件='File',EditorSettings='Form',提示='Notifier')
    with zipfile.ZipFile(a.input) as old, zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED) as new:
        for name in old.namelist():
            if name.startswith('assets/'): continue
            data = old.read(name)
            if name.endswith('.scm'):
                d = json.loads(data.decode().split('$JSON')[1].rsplit('|#',1)[0])
                def update(c):
                    if c['$Name'] == '音乐输入':
                        uuid = c['Uuid']
                        c.clear()
                        c.update(按钮('音乐输入','选择音乐（需上传同名素材）','ListPicker',ShowFilterBar='True',ElementsFromString='无音乐',Selection='无音乐'))
                        c['Uuid'] = uuid
                    for x in c.get('$Components',[]): update(x)
                update(d['Properties'])
                if name.endswith('/EditorSettings.scm'):
                    d['Properties']['$Components'].append(component('曲目文件','File',4))
                d['Properties'].update(VersionCode='9',VersionName='0.6.3')
                data = ('#|\n$JSON\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n|#\n').encode()
            elif name.endswith('.bky'):
                xml = ET.fromstring(data)
                for e in xml.iter(): e.tag = e.tag.split('}')[-1]
                count = 0
                def replace(parent):
                    nonlocal count
                    for child in list(parent):
                        if child.tag == 'block' and child.get('type') == 'lists_copy':
                            v = child.find("value[@name='LIST']/block")
                            replacement = invoke(copy.deepcopy(v))
                            parent.remove(child)
                            parent.append(replacement)
                            count += 1
                            replace(replacement)
                        else: replace(child)
                replace(xml)
                if count: xml.append(copier())
                if name.endswith('/EditorSettings.bky'):
                    for b in xml.iter('block'):
                        if b.get('type') == 'lexical_variable_set' and b.findtext("field[@name='VAR']") == 'global 音乐名':
                            v=b.find("value[@name='VALUE']")
                            v.clear(); v.set('name','VALUE')
                            v.append(选(等(取('音乐输入','Selection'),'无音乐'),'',取('音乐输入','Selection')))
                    TOP.clear()
                    事件('EditorSettings','Initialize',[method('曲目文件','ReadFrom','//music_list.txt')])
                    lines=block('text_split',{'OP':'SPLIT'},{'TEXT':get('内容'),'AT':'\n'})
                    事件('曲目文件','GotText',[local('曲目',make_list('无音乐'),[遍历('行',lines,[local('文件名',修剪(get('行')),[iff(全(非(等(get('文件名'),'')),非(包含(get('曲目'),get('文件名')))),[添(get('曲目'),get('文件名'))])])]),设('音乐输入',get('曲目'),'Elements')])],['内容'])
                    事件('音乐输入','AfterPicking',[设('音乐输入',取('音乐输入','Selection'))])
                    事件('EditorSettings','ErrorOccurred',[警告(join('音乐列表读取失败，请上传 music_list.txt。',get('消息')))],['组件','函数','编号','消息'])
                    xml.extend(TOP)
                stamp=xml.find('yacodeblocks')
                if stamp is not None:
                    xml.remove(stamp)
                    xml.append(stamp)
                for i,b in enumerate(xml.findall('block')):
                    b.set('x',str(40+(i//13)*470))
                    b.set('y',str(40+(i%13)*115))
                    if b.get('type')!='global_declaration': b.set('collapsed','true')
                for i,b in enumerate(xml.iter('block')): b.set('id',f'兼容_{i}')
                xml.set('xmlns','http://www.w3.org/1999/xhtml')
                ET.indent(xml,space='  ')
                data = ET.tostring(xml,encoding='utf-8')
                assert b'lists_copy' not in data and b'ListDirectory' not in data
            elif name.endswith('project.properties'):
                data=data.decode().replace('versioncode=8','versioncode=9').replace('versionname=0.6.2','versionname=0.6.3').encode()
            new.writestr(name,data)
            out=ROOT/'native/Rail4K_iOSFix'/name
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_bytes(data)
        new.writestr('assets/music_list.txt',catalog)
    print(json.dumps({'output':str(a.output),'catalog_tracks':len(names),'audio_files':0},ensure_ascii=False))

if __name__ == '__main__': main()
