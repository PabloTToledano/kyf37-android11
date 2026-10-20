package org.kyf37.pokedex;

import android.content.*;
import android.database.*;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.*;

/** One private capture file, available only to the chosen camera through a URI grant. */
public final class CaptureProvider extends ContentProvider {
    static final Uri URI=Uri.parse("content://org.kyf37.pokedex.capture/capture");
    static File file(Context c){return new File(c.getCacheDir(),"identify-capture.jpg");}
    @Override public boolean onCreate(){return true;}
    private void check(Uri uri)throws FileNotFoundException{if(!URI.equals(uri))throw new FileNotFoundException("Unknown capture URI");}
    @Override public ParcelFileDescriptor openFile(Uri uri,String mode)throws FileNotFoundException{
        check(uri);int flags;
        if("r".equals(mode))flags=ParcelFileDescriptor.MODE_READ_ONLY;
        else if("w".equals(mode)||"wt".equals(mode))flags=ParcelFileDescriptor.MODE_WRITE_ONLY|ParcelFileDescriptor.MODE_CREATE|ParcelFileDescriptor.MODE_TRUNCATE;
        else if("rw".equals(mode))flags=ParcelFileDescriptor.MODE_READ_WRITE|ParcelFileDescriptor.MODE_CREATE;
        else throw new FileNotFoundException("Unsupported mode");
        return ParcelFileDescriptor.open(file(getContext()),flags);
    }
    @Override public String getType(Uri uri){return URI.equals(uri)?"image/jpeg":null;}
    @Override public Cursor query(Uri uri,String[] projection,String selection,String[] args,String sort){
        if(!URI.equals(uri))return null;String[] columns=projection==null?new String[]{OpenableColumns.DISPLAY_NAME,OpenableColumns.SIZE}:projection;MatrixCursor c=new MatrixCursor(columns);Object[] row=new Object[columns.length];
        for(int i=0;i<columns.length;i++)row[i]=OpenableColumns.DISPLAY_NAME.equals(columns[i])?"capture.jpg":OpenableColumns.SIZE.equals(columns[i])?file(getContext()).length():null;c.addRow(row);return c;
    }
    @Override public Uri insert(Uri u,ContentValues v){throw new UnsupportedOperationException();}
    @Override public int update(Uri u,ContentValues v,String s,String[] a){throw new UnsupportedOperationException();}
    @Override public int delete(Uri u,String s,String[] a){throw new UnsupportedOperationException();}
}
