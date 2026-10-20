package org.kyf37.pokedex;

import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.graphics.Bitmap;
import org.json.*;
import org.tensorflow.lite.*;
import java.io.*;
import java.nio.*;
import java.nio.channels.FileChannel;
import java.security.MessageDigest;
import java.util.*;

/** Owned exclusively by IdentifyActivity's single inference worker. */
final class LiteClassifier implements AutoCloseable {
    static final class Match { final int id; final String name; final double score; Match(int i,String n,double s){id=i;name=n;score=s;} }
    static final class Result {
        final List<Match> matches; final boolean unknown, confident; final long milliseconds;
        Result(List<Match> m,boolean u,boolean c,long ms){matches=m;unknown=u;confident=c;milliseconds=ms;}
    }
    private Interpreter interpreter; private MappedByteBuffer weights;
    private final JSONArray labels; private final JSONObject metadata;
    private final ByteBuffer input, output; private final int size; private final int[] pixels;
    private final float inputScale, outputScale; private final int inputZero, outputZero;
    LiteClassifier(Context context) throws Exception {
        metadata=new JSONObject(read(context,"ml/model.json"));labels=new JSONArray(read(context,"ml/labels.json"));
        size=metadata.getInt("inputSize"); if(size<64||size>224||labels.length()!=650)throw new IOException("Unsupported model dimensions");
        try(AssetFileDescriptor fd=context.getAssets().openFd("ml/pokemon-int8.tflite");FileInputStream in=new FileInputStream(fd.getFileDescriptor())) {
            weights=in.getChannel().map(FileChannel.MapMode.READ_ONLY,fd.getStartOffset(),fd.getDeclaredLength());
        }
        MessageDigest digest=MessageDigest.getInstance("SHA-256");digest.update(weights.asReadOnlyBuffer());StringBuilder hex=new StringBuilder();for(byte b:digest.digest())hex.append(String.format(Locale.ROOT,"%02x",b&255));
        if(!hex.toString().equals(metadata.getString("modelSha256")))throw new IOException("Model integrity check failed");
        interpreter=new Interpreter(weights,new Interpreter.Options().setNumThreads(2).setUseNNAPI(false));
        Tensor it=interpreter.getInputTensor(0), ot=interpreter.getOutputTensor(0);
        if(it.dataType()!=DataType.UINT8 || ot.dataType()!=DataType.INT8 || !Arrays.equals(it.shape(),new int[]{1,size,size,3})|| !Arrays.equals(ot.shape(),new int[]{1,650})){close();throw new IOException("Unexpected model tensors");}
        inputScale=it.quantizationParams().getScale();inputZero=it.quantizationParams().getZeroPoint();outputScale=ot.quantizationParams().getScale();outputZero=ot.quantizationParams().getZeroPoint();
        input=ByteBuffer.allocateDirect(it.numBytes()).order(ByteOrder.nativeOrder());output=ByteBuffer.allocateDirect(ot.numBytes()).order(ByteOrder.nativeOrder());pixels=new int[size*size];
    }
    static String read(Context c,String path) throws IOException {
        try(InputStream in=c.getAssets().open(path);ByteArrayOutputStream out=new ByteArrayOutputStream()) {byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1)out.write(b,0,n);return out.toString("UTF-8");}
    }
    Result classify(Bitmap crop) throws Exception {
        long start=android.os.SystemClock.elapsedRealtime();
        if(crop.hasAlpha()){Bitmap flat=Bitmap.createBitmap(crop.getWidth(),crop.getHeight(),Bitmap.Config.ARGB_8888);
            android.graphics.Canvas cv=new android.graphics.Canvas(flat);cv.drawColor(0xffffffff);cv.drawBitmap(crop,0,0,null);crop=flat;}
        Bitmap image=Bitmap.createScaledBitmap(crop,size,size,true);
        image.getPixels(pixels,0,size,0,0,size,size);if(image!=crop)image.recycle();
        double sum=0,square=0;input.clear();
        for(int argb:pixels){int r=(argb>>16)&255,g=(argb>>8)&255,b=argb&255;int lum=(r*77+g*150+b*29)>>8;sum+=lum;square+=lum*lum;
            input.put(quantize(r));input.put(quantize(g));input.put(quantize(b));}
        double variance=square/pixels.length-Math.pow(sum/pixels.length,2);
        if(variance<12)return new Result(Collections.<Match>emptyList(),true,false,android.os.SystemClock.elapsedRealtime()-start);
        input.rewind();output.clear();interpreter.run(input,output);output.rewind();
        double[] scores=new double[650];double max=-Double.MAX_VALUE,temperature=metadata.getDouble("temperature");
        for(int i=0;i<650;i++){scores[i]=(output.get()-outputZero)*outputScale/temperature;max=Math.max(max,scores[i]);}
        double total=0;for(int i=0;i<650;i++){scores[i]=Math.exp(scores[i]-max);total+=scores[i];}for(int i=0;i<650;i++)scores[i]/=total;
        Integer[] order=new Integer[650];for(int i=0;i<650;i++)order[i]=i;Arrays.sort(order,(a,b)->Double.compare(scores[b],scores[a]));
        // Species are ranked on their own: the "unknown" class dominates on dark / busy camera backgrounds even when the
        // right species leads among species (host check: 16/16 sprites correct on white). Give up only when the best
        // species is weak.
        double rest=Math.max(1e-6,1-scores[649]);
        Integer[] species=new Integer[649];int k=0;for(Integer i:order)if(i!=649)species[k++]=i;
        double best=scores[species[0]]/rest, second=scores[species[1]]/rest;
        for(int i=0;i<649;i++)scores[i]/=rest;
        order=species;
        boolean unknown=best<metadata.optDouble("unknownBestThreshold",0.18);
        boolean confident=!unknown && best>=metadata.optDouble("confidentBestThreshold",0.6) && best-second>=metadata.optDouble("confidentMarginThreshold",0.15);
        List<Match> matches=new ArrayList<>();
        if(!unknown)for(int index:order){JSONObject item=labels.getJSONObject(index);int id=item.getInt("id");if(id>0&&id<=649){matches.add(new Match(id,item.getString("name"),scores[index]));if(matches.size()==3)break;}}
        return new Result(matches,unknown,confident,android.os.SystemClock.elapsedRealtime()-start);
    }
    private byte quantize(int value){return (byte)Math.max(0,Math.min(255,Math.round(value/inputScale)+inputZero));}
    @Override public void close(){if(interpreter!=null){interpreter.close();interpreter=null;}weights=null;}
}
