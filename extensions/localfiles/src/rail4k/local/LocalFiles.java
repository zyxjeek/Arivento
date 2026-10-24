package rail4k.local;

import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.view.MotionEvent;
import android.view.View;
import com.google.appinventor.components.runtime.*;
import java.io.*;

public final class LocalFiles extends AndroidNonvisibleComponent implements ActivityResultListener {
  private final Activity activity;
  private final int request;
  private volatile int mode;
  private String text = "";
  public LocalFiles(ComponentContainer container) {
    super(container.$form());
    activity = container.$context();
    request = form.registerForActivityResult(this);
  }
  public void 选择音乐() { open(1, "audio/*", ""); }
  public void 导入谱面() { open(2, "*/*", ""); }
  public void 启用多点(AndroidViewComponent 画布) {
    画布.getView().setOnTouchListener(new View.OnTouchListener() {
      public boolean onTouch(View view, MotionEvent event) {
        int action = event.getActionMasked();
        if ((action == MotionEvent.ACTION_DOWN || action == MotionEvent.ACTION_POINTER_DOWN) && view.getWidth() > 0) {
          int index = event.getActionIndex();
          int lane = Math.max(1, Math.min(4, (int) Math.floor(event.getX(index) * 4 / view.getWidth()) + 1));
          emit("轨道按下", lane, event.getPointerCount());
        }
        return true;
      }
    });
  }
  public void 保存谱面(String 名称, String 内容) {
    if (mode != 0) return;
    text = 内容;
    String name = 名称.replaceAll("[\\\\/:*?\"<>|\\p{Cntrl}]", "_").trim();
    if (name.length() == 0) name = "谱面";
    if (name.length() > 100) name = name.substring(0, 100);
    if (!name.toLowerCase(java.util.Locale.ROOT).endsWith(".txt")) name += ".txt";
    open(3, "text/plain", name);
  }
  private void open(int next, String mime, String name) {
    if (mode != 0) return;
    mode = next;
    try {
      Intent intent = new Intent(next == 3 ? Intent.ACTION_CREATE_DOCUMENT : Intent.ACTION_OPEN_DOCUMENT);
      intent.addCategory(Intent.CATEGORY_OPENABLE);
      intent.setType(mime);
      intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
      if (next == 3) {
        intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        intent.putExtra(Intent.EXTRA_TITLE, name);
      }
      activity.startActivityForResult(intent, request);
    } catch (Exception e) { fail(e); }
  }
  private String name(Uri uri) {
    try (Cursor cursor = activity.getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
      if (cursor != null && cursor.moveToFirst()) return cursor.getString(0);
    } catch (Exception ignored) {}
    return "文件";
  }
  private void emit(final String event, final Object... args) {
    activity.runOnUiThread(new Runnable() {
      public void run() { EventDispatcher.dispatchEvent(LocalFiles.this, event, args); }
    });
  }
  private void fail(Exception e) {
    mode = 0;
    text = "";
    emit("出错", e.getMessage() == null ? e.toString() : e.getMessage());
  }
  public void resultReturned(int code, int result, Intent data) {
    if (code != request || mode == 0) return;
    if (result != Activity.RESULT_OK || data == null || data.getData() == null) {
      mode = 0;
      text = "";
      emit("取消");
      return;
    }
    final Uri uri = data.getData();
    final int operation = mode;
    final String content = text;
    text = "";
    try {
      activity.getContentResolver().takePersistableUriPermission(uri, data.getFlags() &
        (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION));
    } catch (SecurityException ignored) {}
    new Thread(new Runnable() {
      public void run() {
        try {
          String filename = name(uri);
          if (operation == 1) {
            mode = 0;
            emit("音乐已选", uri.toString(), filename);
          } else if (operation == 2) {
            StringBuilder value = new StringBuilder();
            try (Reader input = new InputStreamReader(activity.getContentResolver().openInputStream(uri), "UTF-8")) {
              char[] buffer = new char[8192];
              int count;
              while ((count = input.read(buffer)) != -1) {
                if (value.length() + count > 16000000) throw new IOException("谱面文件过大");
                value.append(buffer, 0, count);
              }
            }
            if (value.length() > 0 && value.charAt(0) == '\uFEFF') value.deleteCharAt(0);
            mode = 0;
            emit("谱面已读", value.toString(), filename);
          } else {
            try (Writer output = new OutputStreamWriter(activity.getContentResolver().openOutputStream(uri, "wt"), "UTF-8")) {
              output.write(content);
            }
            mode = 0;
            emit("谱面已保存", filename);
          }
        } catch (Exception e) { fail(e); }
      }
    }).start();
  }
}
