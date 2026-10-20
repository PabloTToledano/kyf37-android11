package org.kyf37.pokedex;

import android.app.Activity;
import android.content.*;
import android.graphics.*;
import android.graphics.drawable.*;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.*;
import android.provider.MediaStore;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.util.concurrent.*;

/** Keypad camera/import, bounded image decode, crop, and one offline inference at a time. */
public final class IdentifyActivity extends Activity {
    private static final int PHOTO=61, PICK=62, SOURCE=0, CROP=1, BUSY=2, RESULTS=3;
    private final Handler ui=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private volatile int generation;private boolean destroyed,active;private int state=SOURCE;
    private LinearLayout body,root;private TextView footer;private Bitmap preview;private CropView crop;
    private LiteClassifier classifier; // Read, invoke and close only on worker.
    private float centerX=.5f,centerY=.5f,cropSize=1;
    private final boolean es=DexLogic.spanish(java.util.Locale.getDefault().getLanguage());
    private String tr(String en,String spanish){return es?spanish:en;}
    private final int accent=0xffb94050,ink=0xff263f43,paper=0xffe8eee4;
    private final Runnable scan=new Runnable(){public void run(){if(active&&state==BUSY&&crop!=null){crop.invalidate();ui.postDelayed(this,80);}}};
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN|View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        showSource();
        if(saved!=null&&saved.getBoolean("image")&&new File(getCacheDir(),"identify-input.image").exists())load(Uri.fromFile(new File(getCacheDir(),"identify-input.image")));
    }
    @Override public void onSaveInstanceState(Bundle out){super.onSaveInstanceState(out);out.putBoolean("image",preview!=null);}
    @Override protected void onResume(){super.onResume();active=true;if(state==SOURCE&&viewfinder!=null&&viewfinder.getHolder().getSurface().isValid())openCamera(viewfinder.getHolder());}
    @Override protected void onPause(){
        closeCamera();
        active=false;generation++;ui.removeCallbacks(scan);
        if(state==BUSY&&preview!=null)showCrop(tr("Scan cancelled. Press OK to try again.","Análisis cancelado. Pulsa OK para intentarlo de nuevo."));
        worker.execute(this::closeModel);super.onPause();
    }
    @Override protected void onDestroy(){destroyed=true;generation++;ui.removeCallbacksAndMessages(null);worker.execute(this::closeModel);worker.shutdown();preview=null;super.onDestroy();}
    private void closeModel(){if(classifier!=null){classifier.close();classifier=null;}}
    private int dp(float n){return Math.round(n*getResources().getDisplayMetrics().density);}
    // kyf37-dex-identify: same chrome as the main Pokédex screen (red lid with lens, paper, panels, corner key bar)
    private int themeAccent(){int t=getSharedPreferences("field-journal",MODE_PRIVATE).getInt("theme",0);return t==1?0xff766487:t==2?0xff39464f:0xffbd3f50;}
    private int themePaper(){int t=getSharedPreferences("field-journal",MODE_PRIVATE).getInt("theme",0);return t==1?0xffe9e9ee:t==2?0xffe8eff3:0xffe8eee4;}
    private String[] keys={"","",""};
    private void layout(String title,String unused){
        root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(themePaper());
        root.addView(new DexHeader(title),new LinearLayout.LayoutParams(-1,dp(56)));
        body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);body.setPadding(dp(12),dp(10),dp(12),dp(6));
        if(state==SOURCE||state==RESULTS){ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.addView(body,new ScrollView.LayoutParams(-1,-2));root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));}
        else root.addView(body,new LinearLayout.LayoutParams(-1,0,1));
        footer=label("",16,0xffffffff);footer.setVisibility(View.GONE);
        root.addView(new KeyBar(),new LinearLayout.LayoutParams(-1,dp(50)));
        setContentView(root);
    }
    private void keys(String left,String center,String right){keys=new String[]{left,center,right};if(root!=null)root.invalidate();for(int i=0;root!=null&&i<root.getChildCount();i++)root.getChildAt(i).invalidate();}
    /** Lid of the Pokédex: lens, three lights, POKÉDEX and the section name - identical to the main screen. */
    private final class DexHeader extends View {
        private final String title;private final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
        DexHeader(String t){super(IdentifyActivity.this);title=t;}
        @Override protected void onDraw(Canvas c){
            float s=getWidth()/480f,h=getHeight();int accent=themeAccent();
            p.setColor(accent);c.drawRect(0,0,getWidth(),h,p);p.setColor(0x33000000);c.drawRect(0,h-4*s,getWidth(),h,p);
            float cy=h/2-2*s;p.setColor(0xffe4f6fc);c.drawCircle(37*s,cy,19*s,p);p.setColor(0xff61c9e0);c.drawCircle(37*s,cy,14*s,p);p.setColor(0xffffffff);c.drawCircle(33*s,cy-4*s,3.5f*s,p);
            for(int i=0;i<3;i++){p.setColor(i==0?0xfff2b7a3:0xffdc8590);c.drawCircle((74+i*14)*s,cy-12*s,4*s,p);}
            p.setColor(0xffffffff);p.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));p.setTextSize(22*s);c.drawText("POKÉDEX",70*s,cy+14*s,p);
            p.setTextSize(13*s);p.setColor(0xfff5dce0);p.setTextAlign(Paint.Align.RIGHT);c.drawText(title,getWidth()-16*s,cy+13*s,p);p.setTextAlign(Paint.Align.LEFT);
        }
    }
    /** Corner key bar like the main screen: left key, OK pill, right key. */
    private final class KeyBar extends View {
        private final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
        KeyBar(){super(IdentifyActivity.this);}
        @Override protected void onDraw(Canvas c){
            float s=getWidth()/480f,h=getHeight();int accent=themeAccent();
            p.setColor(accent);c.drawRect(0,0,getWidth(),h,p);p.setTextAlign(Paint.Align.CENTER);p.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));
            for(int i=0;i<2;i++){float l=i==0?12*s:310*s,r=i==0?170*s:468*s;p.setColor(0x33301522);c.drawRoundRect(new RectF(l,8*s,r,h-8*s),4*s,4*s,p);
                p.setColor(0xffffffff);p.setTextSize(15*s);c.drawText(keys[i==0?0:2],(l+r)/2,h/2+5*s,p);}
            if(!keys[1].isEmpty()){p.setColor(0xfff8f1e8);c.drawRoundRect(new RectF(185*s,4*s,295*s,h-4*s),(h-8*s)/2,(h-8*s)/2,p);p.setColor(accent);p.setTextSize(16*s);c.drawText(keys[1],240*s,h/2+6*s,p);}
            p.setTextAlign(Paint.Align.LEFT);
        }
    }
    private TextView label(String text,int size,int color){TextView t=new TextView(this);t.setText(text);t.setTextSize(size);t.setTextColor(color);t.setTypeface(Typeface.create("sans-serif-medium",0));return t;}
    private void note(String value){if(value==null||value.isEmpty())return;TextView t=label(value,16,ink);t.setPadding(dp(4),dp(4),dp(4),dp(10));body.addView(t);}
    private Button button(String title,Runnable action){
        Button b=new Button(this);b.setAllCaps(false);b.setText(title);b.setTextSize(18);b.setTextColor(ink);b.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));
        b.setGravity(Gravity.CENTER_VERTICAL);b.setPadding(dp(16),0,dp(12),0);b.setCompoundDrawablePadding(dp(10));
        GradientDrawable normal=new GradientDrawable();normal.setColor(0xfff9fbf2);normal.setCornerRadius(dp(4));
        GradientDrawable focus=new GradientDrawable();focus.setColor(0xfff9fbf2);focus.setCornerRadius(dp(4));focus.setStroke(dp(3),themeAccent());
        StateListDrawable states=new StateListDrawable();states.addState(new int[]{android.R.attr.state_focused},focus);states.addState(new int[]{android.R.attr.state_pressed},focus);states.addState(new int[]{},normal);b.setBackground(states);
        LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,dp(60));params.bottomMargin=dp(8);body.addView(b,params);b.setOnClickListener(v->action.run());return b;
    }
    private android.graphics.drawable.Drawable sprite(int id){
        try(java.io.InputStream in=getAssets().open("sprites/"+id+".png")){Bitmap bm=android.graphics.BitmapFactory.decodeStream(in);if(bm==null)return null;
            android.graphics.drawable.BitmapDrawable d=new android.graphics.drawable.BitmapDrawable(getResources(),Bitmap.createScaledBitmap(bm,dp(48),dp(48),false));return d;}catch(Exception e){return null;}
    }
    // ---- live viewfinder (kyf37-live-camera)
    private android.hardware.Camera cam;private SurfaceView viewfinder;private boolean autoAnalyze, capturing;
    private void showSource(){
        state=SOURCE;layout(tr("IDENTIFY","IDENTIFICAR"),"");keys(tr("Back","Atrás"),tr("SCAN","ESCANEAR"),tr("Gallery","Galería"));
        if(checkSelfPermission(android.Manifest.permission.CAMERA)!=android.content.pm.PackageManager.PERMISSION_GRANTED){
            note(tr("Camera access is needed to scan.","Se necesita acceso a la cámara para escanear."));
            Button b=button(tr("Allow camera","Permitir cámara"),()->requestPermissions(new String[]{android.Manifest.permission.CAMERA},11));
            button(tr("Choose image","Elegir imagen"),this::choose);b.requestFocus();return;
        }
        FrameLayout box=new FrameLayout(this);viewfinder=new SurfaceView(this);box.addView(viewfinder,new FrameLayout.LayoutParams(-1,-1));box.addView(new Reticle(),new FrameLayout.LayoutParams(-1,-1));
        int w=getResources().getDisplayMetrics().widthPixels-dp(36);body.addView(upper(box),new LinearLayout.LayoutParams(-1,w));
        note(tr("Frame one Pokémon inside the corners.","Encuadra un Pokémon dentro de las esquinas."));
        viewfinder.getHolder().addCallback(new SurfaceHolder.Callback(){
            public void surfaceCreated(SurfaceHolder h){openCamera(h);}
            public void surfaceChanged(SurfaceHolder h,int f,int ww,int hh){}
            public void surfaceDestroyed(SurfaceHolder h){closeCamera();}
        });
        root.setContentDescription(tr("Identify. Camera viewfinder. OK scans.","Identificar. Visor de cámara. OK escanea."));
    }
    @Override public void onRequestPermissionsResult(int code,String[] perms,int[] res){super.onRequestPermissionsResult(code,perms,res);if(state==SOURCE)showSource();}
    private int cameraRotation(){android.hardware.Camera.CameraInfo info=new android.hardware.Camera.CameraInfo();android.hardware.Camera.getCameraInfo(0,info);return info.orientation;}
    private void openCamera(SurfaceHolder h){
        try{closeCamera();cam=android.hardware.Camera.open(0);android.hardware.Camera.Parameters p=cam.getParameters();
            android.hardware.Camera.Size best=null;for(android.hardware.Camera.Size z:p.getSupportedPreviewSizes())if(z.width*3==z.height*4&&z.width<=960&&(best==null||z.width>best.width))best=z;if(best!=null)p.setPreviewSize(best.width,best.height);
            android.hardware.Camera.Size pic=null;for(android.hardware.Camera.Size z:p.getSupportedPictureSizes())if(z.width*3==z.height*4&&z.width<=1600&&(pic==null||z.width>pic.width))pic=z;if(pic!=null)p.setPictureSize(pic.width,pic.height);
            java.util.List<String> fm=p.getSupportedFocusModes();if(fm!=null&&fm.contains(android.hardware.Camera.Parameters.FOCUS_MODE_CONTINUOUS_PICTURE))p.setFocusMode(android.hardware.Camera.Parameters.FOCUS_MODE_CONTINUOUS_PICTURE);
            p.setJpegQuality(90);cam.setParameters(p);cam.setDisplayOrientation(cameraRotation());cam.setPreviewDisplay(h);cam.startPreview();
        }catch(Exception e){closeCamera();message(tr("Camera unavailable","Cámara no disponible"),tr("Close the Camera app and try again, or choose an image.","Cierra la app de Cámara y vuelve a intentarlo, o elige una imagen."));}
    }
    private void closeCamera(){if(cam!=null){try{cam.stopPreview();}catch(Exception ignored){}cam.release();cam=null;}}
    /** OK: take the photo, keep the framed square, then analyse straight away. */
    private void capture(){
        if(cam==null||capturing)return;capturing=true;
        try{cam.takePicture(null,null,(data,c)->{capturing=false;final byte[] jpeg=data;closeCamera();
            final int request=++generation;state=BUSY;layout(tr("SCANNING","ESCANEANDO"),"");keys("",tr("WAIT","ESPERA"),"");note(tr("Preparing photo…","Preparando foto…"));
            worker.execute(()->{File out=new File(getCacheDir(),"identify-input.image");String err=null;
                try{BitmapFactory.Options o=new BitmapFactory.Options();o.inSampleSize=2;Bitmap b=BitmapFactory.decodeByteArray(jpeg,0,jpeg.length,o);
                    Matrix m=new Matrix();m.setRotate(cameraRotation());Bitmap up=Bitmap.createBitmap(b,0,0,b.getWidth(),b.getHeight(),m,true);if(up!=b)b.recycle();
                    int side=Math.round(Math.min(up.getWidth(),up.getHeight())*0.82f);Bitmap sq=Bitmap.createBitmap(up,(up.getWidth()-side)/2,(up.getHeight()-side)/2,side,side);if(sq!=up)up.recycle();
                    try(FileOutputStream f=new FileOutputStream(out)){sq.compress(Bitmap.CompressFormat.JPEG,92,f);}sq.recycle();
                }catch(Exception|OutOfMemoryError e){err=String.valueOf(e.getMessage());}
                final String error=err;ui.post(()->{if(destroyed||request!=generation)return;if(error!=null){message(tr("Photo unavailable","Foto no disponible"),error);return;}autoAnalyze=true;load(Uri.fromFile(out));});
            });});
        }catch(RuntimeException e){capturing=false;message(tr("Camera unavailable","Cámara no disponible"),tr("Try again or choose an image.","Vuelve a intentarlo o elige una imagen."));}
    }
    /** Corner brackets marking the square that is analysed (82 % of the short side, centred). */
    private final class Reticle extends View {
        private final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
        Reticle(){super(IdentifyActivity.this);setWillNotDraw(false);}
        @Override protected void onDraw(Canvas c){
            float w=getWidth(),h=getHeight(),side=Math.min(w,h)*0.82f,l=(w-side)/2,t=(h-side)/2,len=side*0.16f,d=getResources().getDisplayMetrics().density;
            p.setColor(0xffffffff);p.setStrokeWidth(4*d);p.setStrokeCap(Paint.Cap.ROUND);
            c.drawLine(l,t,l+len,t,p);c.drawLine(l,t,l,t+len,p);c.drawLine(l+side,t,l+side-len,t,p);c.drawLine(l+side,t,l+side,t+len,p);
            c.drawLine(l,t+side,l+len,t+side,p);c.drawLine(l,t+side,l,t+side-len,p);c.drawLine(l+side,t+side,l+side-len,t+side,p);c.drawLine(l+side,t+side,l+side,t+side-len,p);
        }
    }
    private void camera(){
        try {
            CaptureProvider.file(this).delete();
            Intent i=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);i.putExtra(MediaStore.EXTRA_OUTPUT,CaptureProvider.URI);i.setClipData(ClipData.newRawUri("capture",CaptureProvider.URI));i.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivityForResult(i,PHOTO);
        }catch(ActivityNotFoundException|SecurityException e){message(tr("Camera unavailable","Cámara no disponible"),tr("Choose an existing image instead.","Elige una imagen existente en su lugar."));}
    }
    private void choose(){
        try{Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.setType("image/*");i.addCategory(Intent.CATEGORY_OPENABLE);startActivityForResult(i,PICK);}
        catch(ActivityNotFoundException e){message(tr("Image picker unavailable","Selector de imágenes no disponible"),tr("No document picker is installed on this device.","No hay ningún selector de documentos instalado en este dispositivo."));}
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request==PHOTO){revokeUriPermission(CaptureProvider.URI,Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION);if(result==RESULT_OK)load(Uri.fromFile(CaptureProvider.file(this)));else showSource();}
        else if(request==PICK&&result==RESULT_OK&&data!=null&&data.getData()!=null)load(data.getData());
    }
    private void message(String title,String text){state=RESULTS;layout(title,tr("F1 / Clear  Back       OK  Retry","F1 / Clear  Atrás       OK  Reintentar"));note(text);Button b=button(tr("Try another image","Probar otra imagen"),this::showSource);root.setContentDescription(tr("Identify. ERROR. ","Identificar. ERROR. ")+text);b.requestFocus();}
    private void load(Uri uri){
        final int request=++generation;state=BUSY;layout(tr("LOADING IMAGE","CARGANDO IMAGEN"),tr("Clear  Cancel","Clear  Cancelar"));keys(tr("Cancel","Cancelar"),"","");note(tr("Preparing image…","Preparando imagen…"));root.setContentDescription(tr("Identify. LOADING.","Identificar. CARGANDO."));
        worker.execute(()->{
            Bitmap image=null;String failure=null;
            try{
                if(request!=generation)return;
                File saved=new File(getCacheDir(),"identify-input.image");boolean same="file".equals(uri.getScheme())&&saved.getAbsolutePath().equals(uri.getPath());
                if(!same){File temp=new File(getCacheDir(),"identify-input.part");try(InputStream in=getContentResolver().openInputStream(uri);FileOutputStream out=new FileOutputStream(temp)){if(in==null)throw new IOException(tr("Image cannot be read","No se puede leer la imagen"));byte[] b=new byte[8192];int n;long count=0;while((n=in.read(b))!=-1){if(request!=generation)throw new IOException(tr("Cancelled","Cancelado"));count+=n;if(count>32*1024*1024)throw new IOException(tr("Image file exceeds 32 MB","El archivo de imagen supera los 32 MB"));out.write(b,0,n);}}if(!temp.renameTo(saved))throw new IOException(tr("Cannot prepare private image copy","No se puede preparar la copia privada de la imagen"));}
                if(request!=generation)return;
                BitmapFactory.Options options=new BitmapFactory.Options();options.inJustDecodeBounds=true;BitmapFactory.decodeFile(saved.getPath(),options);
                if(options.outWidth<=0||options.outHeight<=0||options.outWidth>25000||options.outHeight>25000)throw new IOException(tr("Unsupported image dimensions","Dimensiones de imagen no compatibles"));
                options.inSampleSize=1;while(Math.max(options.outWidth,options.outHeight)/options.inSampleSize>1024)options.inSampleSize*=2;
                options.inJustDecodeBounds=false;options.inPreferredConfig=Bitmap.Config.ARGB_8888;Bitmap decoded=BitmapFactory.decodeFile(saved.getPath(),options);if(decoded==null)throw new IOException(tr("Image decoder could not read this file","El decodificador no pudo leer este archivo"));
                int orientation=ExifInterface.ORIENTATION_NORMAL;try{orientation=new ExifInterface(saved.getPath()).getAttributeInt(ExifInterface.TAG_ORIENTATION,ExifInterface.ORIENTATION_NORMAL);}catch(IOException ignored){}
                Matrix transform=new Matrix();
                switch(orientation){case 2:transform.setScale(-1,1);break;case 3:transform.setRotate(180);break;case 4:transform.setScale(1,-1);break;case 5:transform.setRotate(90);transform.postScale(-1,1);break;case 6:transform.setRotate(90);break;case 7:transform.setRotate(270);transform.postScale(-1,1);break;case 8:transform.setRotate(270);break;}
                Bitmap upright=Bitmap.createBitmap(decoded,0,0,decoded.getWidth(),decoded.getHeight(),transform,true);if(upright!=decoded)decoded.recycle();
                image=Bitmap.createBitmap(512,512,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(image);c.drawColor(Color.WHITE);float ratio=512f/Math.max(upright.getWidth(),upright.getHeight());float w=upright.getWidth()*ratio,h=upright.getHeight()*ratio;
                c.drawBitmap(upright,null,new RectF((512-w)/2,(512-h)/2,(512+w)/2,(512+h)/2),new Paint(Paint.FILTER_BITMAP_FLAG));upright.recycle();
            }catch(Exception|OutOfMemoryError e){failure=e instanceof OutOfMemoryError?tr("Not enough memory for this image.","No hay memoria suficiente para esta imagen."):e.getMessage();}
            final Bitmap ready=image;final String error=failure;
            ui.post(()->{if(destroyed||request!=generation){if(ready!=null)ready.recycle();return;}if(ready==null){message(tr("Image unavailable","Imagen no disponible"),error==null?tr("Try a smaller JPEG or PNG.","Prueba con un JPEG o PNG más pequeño."):error);return;}preview=ready;centerX=.5f;centerY=.5f;cropSize=1;showCrop(tr("Frame one Pokémon, then press OK.","Encuadra un Pokémon y pulsa OK."));if(autoAnalyze){autoAnalyze=false;analyze();}});
        });
    }
    /** Image panel framed like the Pokédex sprite box. */
    private View upper(View v){FrameLayout f=new FrameLayout(this);GradientDrawable g=new GradientDrawable();g.setColor(0xfff9fbf2);g.setCornerRadius(dp(4));g.setStroke(dp(2),0x22000000);f.setBackground(g);f.setPadding(dp(6),dp(6),dp(6),dp(6));
        f.addView(v,new FrameLayout.LayoutParams(-1,-1));LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,0,1);lp.bottomMargin=dp(10);f.setLayoutParams(lp);return f;}
    private void showCrop(String instruction){
        state=CROP;layout(tr("FRAME POKÉMON","ENCUADRAR POKÉMON"),tr("D-pad  Move crop       2 / 8  Zoom\n5  Reset       OK  Analyze       Clear  Back","D-pad  Mover recorte       2 / 8  Zoom\n5  Reiniciar       OK  Analizar       Clear  Atrás"));keys(tr("Back","Atrás"),tr("ANALYZE","ANALIZAR"),"");
        note(instruction);crop=new CropView();body.addView(upper(crop),new LinearLayout.LayoutParams(-1,0,1));button(tr("Analyze","Analizar"),this::analyze);crop.requestFocus();updateCropDescription();
    }
    private void updateCropDescription(){if(crop!=null)crop.setContentDescription(String.format(java.util.Locale.ROOT,tr("Identify. CROP. Center %.2f %.2f. Size %.2f.","Identificar. RECORTE. Centro %.2f %.2f. Tamaño %.2f."),centerX,centerY,cropSize));}
    private void analyze(){
        if(preview==null||state!=CROP)return;final int request=++generation;final Bitmap image=preview;final float x=centerX,y=centerY,size=cropSize;
        state=BUSY;layout(tr("IDENTIFYING","IDENTIFICANDO"),tr("Clear  Cancel       Photos stay on device","Clear  Cancelar       Las fotos se quedan en el dispositivo"));keys(tr("Cancel","Cancelar"),"","");note(tr("Looking for possible matches…","Buscando posibles coincidencias…"));crop=new CropView();body.addView(upper(crop),new LinearLayout.LayoutParams(-1,0,1));note(tr("Experimental recognition. No result is selected automatically.","Reconocimiento experimental. Ningún resultado se elige automáticamente."));root.setContentDescription(tr("Identify. CHECKING.","Identificar. COMPROBANDO."));ui.post(scan);
        worker.execute(()->{
            LiteClassifier.Result result=null;String failure=null;Bitmap cropped=null;
            try{if(request!=generation)return;int side=Math.max(1,Math.round(size*512)),left=Math.max(0,Math.min(512-side,Math.round(x*512-side/2f))),top=Math.max(0,Math.min(512-side,Math.round(y*512-side/2f)));
                cropped=Bitmap.createBitmap(image,left,top,side,side);if(classifier==null)classifier=new LiteClassifier(getApplicationContext());if(request!=generation)return;result=classifier.classify(cropped);
            }catch(Exception|LinkageError|OutOfMemoryError e){android.util.Log.e("FlipIdentify","Offline inference failed",e);failure=e instanceof OutOfMemoryError?tr("Not enough memory. Try again after closing other apps.","No hay memoria suficiente. Vuelve a intentarlo tras cerrar otras apps."):tr("The offline model could not run on this device.","El modelo sin conexión no puede ejecutarse en este dispositivo.");closeModel();}
            finally{if(cropped!=null&&cropped!=image)cropped.recycle();}
            final LiteClassifier.Result completed=result;final String error=failure;
            ui.post(()->{if(destroyed||request!=generation)return;ui.removeCallbacks(scan);if(completed==null)message("Identification unavailable",error);else showResults(completed);});
        });
    }
    private void showResults(LiteClassifier.Result result){
        state=RESULTS;layout(tr("POSSIBLE MATCHES","POSIBLES COINCIDENCIAS"),tr("D-pad  Choose       OK  Open entry\nF1 / Clear  Crop       1  New image","D-pad  Elegir       OK  Abrir ficha\nF1 / Clear  Recortar       1  Nueva imagen"));keys(tr("Crop","Recortar"),tr("OPEN","ABRIR"),tr("New photo","Nueva foto"));
        note(result.unknown?tr("Cannot identify this image. Try a clearer crop or another photo.","No se puede identificar esta imagen. Prueba con un recorte más claro u otra foto."):result.confident?tr("Likely matches — please confirm.","Coincidencias probables: confírmalo tú."):tr("Uncertain — compare these suggestions.","Incierto: compara estas sugerencias."));
        Button first=null;
        for(LiteClassifier.Match match:result.matches){Button b=button(String.format(java.util.Locale.ROOT,tr("No. %03d  %s   %d%%","Nº %03d  %s   %d%%"),match.id,match.name,(int)Math.round(match.score*100)),()->{setResult(RESULT_OK,new Intent().putExtra("national",match.id));finish();});b.setMinHeight(dp(64));b.setCompoundDrawablesWithIntrinsicBounds(sprite(match.id),null,null,null);if(first==null)first=b;}
        Button retry=button(tr("Adjust crop and retry","Ajustar recorte y reintentar"),()->showCrop(tr("Frame one Pokémon, then press OK.","Encuadra un Pokémon y pulsa OK.")));button(tr("Choose another image","Elegir otra imagen"),this::showSource);
        
        root.setContentDescription(tr("Identify. RESULTS. ","Identificar. RESULTADOS. ")+(result.unknown?tr("Cannot identify.","No se puede identificar."):result.confident?tr("Likely matches.","Coincidencias probables."):tr("Uncertain suggestions.","Sugerencias inciertas."))+tr(" Inference "," Inferencia ")+result.milliseconds+" ms.");(first==null?retry:first).requestFocus();
    }
    private void back(){generation++;ui.removeCallbacks(scan);worker.execute(this::closeModel);if(state==SOURCE){finish();return;}if(preview!=null&&(state==BUSY||state==RESULTS)){showCrop(tr("Adjust the crop or press Clear for a new image.","Ajusta el recorte o pulsa Clear para una imagen nueva."));return;}showSource();}
    @Override public void onBackPressed(){back();}
    @Override public boolean dispatchKeyEvent(KeyEvent e){
        int k=e.getKeyCode();boolean back=k==KeyEvent.KEYCODE_BACK||k==KeyEvent.KEYCODE_ESCAPE||k==KeyEvent.KEYCODE_DEL||k==KeyEvent.KEYCODE_F1;
        boolean corner=k>=KeyEvent.KEYCODE_F1&&k<=KeyEvent.KEYCODE_F4;boolean digit=k>=KeyEvent.KEYCODE_0&&k<=KeyEvent.KEYCODE_9;
        boolean dir=k>=KeyEvent.KEYCODE_DPAD_UP&&k<=KeyEvent.KEYCODE_DPAD_RIGHT;boolean ok=k==KeyEvent.KEYCODE_DPAD_CENTER||k==KeyEvent.KEYCODE_ENTER||k==KeyEvent.KEYCODE_NUMPAD_ENTER;
        if(!(back||corner||digit||dir||ok))return super.dispatchKeyEvent(e);
        if(e.getAction()==KeyEvent.ACTION_UP){if(dir||ok)return state==SOURCE||state==RESULTS?super.dispatchKeyEvent(e):true;return true;}
        if(e.getAction()!=KeyEvent.ACTION_DOWN)return true;if(e.getRepeatCount()>0&&!dir)return true;
        if(back){back();return true;}
        if(state==SOURCE){if(cam!=null&&(ok||k==KeyEvent.KEYCODE_F2||k==KeyEvent.KEYCODE_1)){capture();return true;}if(k==KeyEvent.KEYCODE_2||k==KeyEvent.KEYCODE_F3){choose();return true;}return (dir||ok)?super.dispatchKeyEvent(e):true;}
        if(state==CROP){float step=cropSize*.05f;
            if(k==KeyEvent.KEYCODE_DPAD_LEFT)centerX-=step;else if(k==KeyEvent.KEYCODE_DPAD_RIGHT)centerX+=step;else if(k==KeyEvent.KEYCODE_DPAD_UP)centerY-=step;else if(k==KeyEvent.KEYCODE_DPAD_DOWN)centerY+=step;
            else if(k==KeyEvent.KEYCODE_2)cropSize=Math.max(.15f,cropSize*.8f);else if(k==KeyEvent.KEYCODE_8)cropSize=Math.min(1,cropSize/ .8f);else if(k==KeyEvent.KEYCODE_5){cropSize=1;centerX=.5f;centerY=.5f;}else if(ok||k==KeyEvent.KEYCODE_F4){analyze();return true;}
            centerX=Math.max(cropSize/2,Math.min(1-cropSize/2,centerX));centerY=Math.max(cropSize/2,Math.min(1-cropSize/2,centerY));updateCropDescription();crop.invalidate();return true;
        }
        if(state==BUSY)return true;
        if(state==RESULTS){if(k==KeyEvent.KEYCODE_1||k==KeyEvent.KEYCODE_F3){generation++;worker.execute(this::closeModel);showSource();return true;}return (dir||ok)?super.dispatchKeyEvent(e):true;}
        return true;
    }
    private final class CropView extends View {
        private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);private final RectF area=new RectF();
        CropView(){super(IdentifyActivity.this);setFocusable(true);setFocusableInTouchMode(true);}
        @Override protected void onDraw(Canvas c){
            c.drawColor(0xfffafcf6);if(preview==null)return;float size=Math.min(getWidth(),getHeight())-dp(8),l=(getWidth()-size)/2,t=(getHeight()-size)/2;area.set(l,t,l+size,t+size);c.drawBitmap(preview,null,area,paint);
            float side=cropSize*size,cx=l+centerX*size,cy=t+centerY*size;paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(dp(3));paint.setColor(accent);c.drawRect(cx-side/2,cy-side/2,cx+side/2,cy+side/2,paint);paint.setStyle(Paint.Style.FILL);
            if(state==BUSY){paint.setColor(0xff38aeb5);float y=t+(android.os.SystemClock.uptimeMillis()%1200)/1200f*size;c.drawRect(l,y,l+size,y+dp(2),paint);}
        }
        @Override public boolean onTouchEvent(MotionEvent e){if(state==CROP&&e.getAction()==MotionEvent.ACTION_UP&&area.contains(e.getX(),e.getY())){centerX=(e.getX()-area.left)/area.width();centerY=(e.getY()-area.top)/area.height();centerX=Math.max(cropSize/2,Math.min(1-cropSize/2,centerX));centerY=Math.max(cropSize/2,Math.min(1-cropSize/2,centerY));updateCropDescription();invalidate();performClick();}return true;}
        @Override public boolean performClick(){super.performClick();return true;}
    }
}
