from pathlib import Path
import subprocess,json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tests/local_extension_harness'
SOURCES={
'android/view/View.java':'''package android.view; public class View {public int width=400; public interface OnTouchListener {boolean onTouch(View v,MotionEvent e);} public OnTouchListener listener; public int getWidth(){return width;} public void setOnTouchListener(OnTouchListener l){listener=l;} public boolean touch(MotionEvent e){return listener.onTouch(this,e);}}''',
'android/view/MotionEvent.java':'''package android.view; public class MotionEvent {public static final int ACTION_DOWN=0,ACTION_POINTER_DOWN=5; private int action,index; private float[] xs; public MotionEvent(int a,int i,float...x){action=a;index=i;xs=x;} public int getActionMasked(){return action;}public int getActionIndex(){return index;}public float getX(int i){return xs[i];}public int getPointerCount(){return xs.length;}}''',
'com/google/appinventor/components/runtime/AndroidViewComponent.java':'''package com.google.appinventor.components.runtime; public class AndroidViewComponent {public android.view.View view=new android.view.View(); public android.view.View getView(){return view;}}''',
'android/net/Uri.java':'''package android.net; public class Uri { public final String value; private Uri(String s){value=s;} public static Uri parse(String s){return new Uri(s);} public String toString(){return value;} }''',
'android/database/Cursor.java':'''package android.database; public interface Cursor extends AutoCloseable {boolean moveToFirst(); String getString(int i); void close();}''',
'android/provider/OpenableColumns.java':'''package android.provider; public class OpenableColumns {public static final String DISPLAY_NAME="_display_name";}''',
'android/content/Intent.java':'''package android.content; import android.net.Uri; public class Intent {
public static final String ACTION_CREATE_DOCUMENT="CREATE",ACTION_OPEN_DOCUMENT="OPEN",CATEGORY_OPENABLE="OPENABLE",EXTRA_TITLE="TITLE";
public static final int FLAG_GRANT_READ_URI_PERMISSION=1,FLAG_GRANT_WRITE_URI_PERMISSION=2,FLAG_GRANT_PERSISTABLE_URI_PERMISSION=64;
public String action,mime,title,category; public int flags; public Uri uri;
public Intent(String s){action=s;} public Intent addCategory(String s){category=s;return this;} public Intent setType(String s){mime=s;return this;}
public Intent addFlags(int n){flags|=n;return this;} public Intent putExtra(String k,String v){title=v;return this;} public Uri getData(){return uri;} public int getFlags(){return flags;}
}''',
'android/content/ContentResolver.java':'''package android.content; import android.net.Uri; import android.database.Cursor; import java.io.*; import java.util.*;
public class ContentResolver {
public final Map<String,byte[]> files=new HashMap<String,byte[]>(); public boolean deny=false; public String writeMode=""; public int grants;
public Cursor query(Uri u,String[] a,String b,String[] c,String d){return new Cursor(){public boolean moveToFirst(){return true;}public String getString(int i){return "中文.txt";}public void close(){}};}
public void takePersistableUriPermission(Uri u,int flags){grants=flags;}
public InputStream openInputStream(Uri u)throws IOException {if(deny||!files.containsKey(u.value))throw new IOException("读取失败");return new ByteArrayInputStream(files.get(u.value));}
public OutputStream openOutputStream(final Uri u,String mode)throws IOException {writeMode=mode;if(deny)throw new IOException("空间不足");return new ByteArrayOutputStream(){public void close()throws IOException{super.close();files.put(u.value,toByteArray());}};}
}''',
'android/app/Activity.java':'''package android.app; import android.content.*; public class Activity {
public static final int RESULT_OK=-1; public Intent last; public boolean failStart; public ContentResolver resolver=new ContentResolver();
public void startActivityForResult(Intent i,int code){if(failStart)throw new IllegalStateException("无文件选择器");last=i;} public ContentResolver getContentResolver(){return resolver;}public void runOnUiThread(Runnable r){r.run();}
}''',
'com/google/appinventor/components/runtime/Component.java':'''package com.google.appinventor.components.runtime; public interface Component {}''',
'com/google/appinventor/components/runtime/Form.java':'''package com.google.appinventor.components.runtime; public class Form extends android.app.Activity {public int registerForActivityResult(ActivityResultListener listener){return 9;}}''',
'com/google/appinventor/components/runtime/ComponentContainer.java':'''package com.google.appinventor.components.runtime; public interface ComponentContainer {Form $form(); android.app.Activity $context();}''',
'com/google/appinventor/components/runtime/AndroidNonvisibleComponent.java':'''package com.google.appinventor.components.runtime; public class AndroidNonvisibleComponent implements Component {protected final Form form; public AndroidNonvisibleComponent(Form f){form=f;}}''',
'com/google/appinventor/components/runtime/ActivityResultListener.java':'''package com.google.appinventor.components.runtime; public interface ActivityResultListener {void resultReturned(int request,int result,android.content.Intent data);}''',
'com/google/appinventor/components/runtime/EventDispatcher.java':'''package com.google.appinventor.components.runtime; import java.util.concurrent.*; public class EventDispatcher {
public static final BlockingQueue<Object[]> events=new LinkedBlockingQueue<Object[]>(); public static boolean dispatchEvent(Component c,String event,Object...args){events.add(new Object[]{event,args});return true;}
}''',
'Harness.java':'''import rail4k.local.LocalFiles; import com.google.appinventor.components.runtime.*; import android.content.*; import android.net.Uri; import java.util.*; import java.util.concurrent.*;
public class Harness {
static int count; static final Form form=new Form(); static final LocalFiles file=new LocalFiles(new ComponentContainer(){public Form $form(){return form;}public android.app.Activity $context(){return form;}});
static void check(boolean b){if(!b)throw new AssertionError();count++;}
static Object[] event(String name)throws Exception{Object[] e=EventDispatcher.events.poll(5,TimeUnit.SECONDS);check(e!=null&&name.equals(e[0]));return (Object[])e[1];}
static void result(String path){Intent i=new Intent("RESULT");i.uri=Uri.parse(path);i.flags=3;file.resultReturned(9,-1,i);}
public static void main(String[]args)throws Exception{
file.选择音乐();check(form.last.mime.equals("audio/*"));check(form.last.action.equals("OPEN"));result("content://music/1");check(event("音乐已选")[0].equals("content://music/1"));check(form.resolver.grants==3);
String value="[\\\"中文谱\\\",0,1.2345]";file.保存谱面("谱:面/一",value);check(form.last.action.equals("CREATE"));check(form.last.title.equals("谱_面_一.txt"));check(EventDispatcher.events.isEmpty());result("content://chart/1");event("谱面已保存");check(new String(form.resolver.files.get("content://chart/1"),"UTF-8").equals(value));check(form.resolver.writeMode.equals("wt"));
form.resolver.files.put("content://chart/2",("\\uFEFF"+value).getBytes("UTF-8"));file.导入谱面();check(form.last.mime.equals("*/*"));result("content://chart/2");check(event("谱面已读")[0].equals(value));
file.保存谱面("取消","不写入");file.resultReturned(9,0,null);event("取消");check(form.resolver.files.size()==2);
form.resolver.deny=true;file.保存谱面("失败","不写入");result("content://chart/fail");event("出错");check(!form.resolver.files.containsKey("content://chart/fail"));check(EventDispatcher.events.isEmpty());
file.导入谱面();result("content://missing");event("出错");form.resolver.deny=false;
StringBuilder big=new StringBuilder();for(int i=0;i<50000;i++)big.append("[1,123.456],");file.保存谱面("大谱面",big.toString());result("content://large");event("谱面已保存");file.导入谱面();result("content://large");check(event("谱面已读")[0].equals(big.toString()));
form.failStart=true;file.选择音乐();event("出错");form.failStart=false;file.选择音乐();file.resultReturned(9,0,null);event("取消");
AndroidViewComponent canvas=new AndroidViewComponent();file.启用多点(canvas);
check(canvas.view.touch(new android.view.MotionEvent(0,0,250)));Object[] tap=event("轨道按下");check(tap[0].equals(3)&&tap[1].equals(1));
canvas.view.touch(new android.view.MotionEvent(5,1,250,50));tap=event("轨道按下");check(tap[0].equals(1)&&tap[1].equals(2));
canvas.view.touch(new android.view.MotionEvent(5,0,350,250,50));tap=event("轨道按下");check(tap[0].equals(4)&&tap[1].equals(3));
canvas.view.touch(new android.view.MotionEvent(5,3,350,250,50,150));tap=event("轨道按下");check(tap[0].equals(2)&&tap[1].equals(4));
for(int action:new int[]{1,2,3,6})canvas.view.touch(new android.view.MotionEvent(action,0,50));check(EventDispatcher.events.isEmpty());
canvas.view.width=0;canvas.view.touch(new android.view.MotionEvent(0,0,50));check(EventDispatcher.events.isEmpty());canvas.view.width=400;
file.启用多点(canvas);canvas.view.touch(new android.view.MotionEvent(0,0,50));event("轨道按下");check(EventDispatcher.events.isEmpty());
System.out.println("PASS "+count+" assertions; real extension source, mocked Android document provider");
}
}'''
}

def main():
    paths=[]
    for name,text in SOURCES.items():
        p=OUT/'src'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf8');paths.append(str(p))
    paths.append(str(ROOT/'extensions/localfiles/src/rail4k/local/LocalFiles.java'))
    subprocess.run(['javac','-encoding','UTF-8','-source','7','-target','7','-Xlint:-options','-d',str(OUT/'classes')]+paths,check=True)
    result=subprocess.run(['java','-cp',str(OUT/'classes'),'Harness'],check=True,capture_output=True,text=True)
    print(result.stdout)
    (ROOT/'docs/本地文件扩展测试.json').write_text(json.dumps({'result':result.stdout.strip(),'scope':'真实扩展源码，Android 文件提供器与事件分发使用替身；非手机实测'},ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__':main()
