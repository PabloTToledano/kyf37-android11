#!/usr/bin/env python3
from pathlib import Path
r=Path(__file__).resolve().parents[2];p=r/'templates/src/org/kyf37/walker/WalkerReader.java';s=p.read_text()
if 'void beginTools()' not in s:
 s=s.replace('private void send(int command,byte[] data)throws IOException {','private void send(int command,byte[] data)throws IOException {')
 s=s.replace('int length=payloadSize+8;long deadline=', 'return receiveTools(command,payloadSize,handshake,2,false);\n    }\n    Packet receiveTools(int command,int payloadSize,boolean handshake,int extra,boolean stream)throws IOException {\n        int length=payloadSize+8;long deadline=')
 s=s.replace('packet.extra==2','(extra<0||packet.extra==extra)').replace('if(pending.length!=0)throw','if(!stream && pending.length!=0)throw')
 at=s.index('    public static int le16')
 s=s[:at]+'''    // Explicit advanced operations use the same bounded framing and session checks.
    void beginTools()throws IOException {
        if(session!=null)throw new IOException("Use a fresh connection");
        operationDeadline=clock.milliseconds()+180000;
        advertise();send(0xfa,new byte[0]);session=receive(0xf8,0,true).session.clone();
    }
    Identity toolIdentity()throws IOException {send(0x20,new byte[0]);return new Identity(receive(0x22,104,false).payload);}
    byte[] toolRead(int address,int size)throws IOException {
        if(address<0||size<1||size>128||address+size>65536)throw new IOException("Invalid EEPROM range");
        send(0x0c,new byte[]{(byte)(address>>>8),(byte)address,(byte)size});return receive(0x0e,size,false).payload;
    }
    byte[] toolBackup(Progress progress)throws IOException {
        byte[] b=new byte[65536];for(int a=0;a<b.length;a+=128){System.arraycopy(toolRead(a,128),0,b,a,128);progress.bytesRead(a+128);}return b;
    }
    void toolCommand(int command,int extra,byte[] payload,int ack,boolean stream)throws IOException {
        check();link.send(new Packet(command,extra,session,payload).encode());receiveTools(ack,0,false,-1,stream);
    }
    void toolWrite(int address,byte[] data)throws IOException {
        if(address<0||address+data.length>65536)throw new IOException("Invalid write range");
        for(int at=0;at<data.length;){int n=Math.min(127,data.length-at);byte[] b=new byte[n+1];b[0]=(byte)address;
            System.arraycopy(data,at,b,1,n);toolCommand(0x0a,address>>>8,b,4,false);at+=n;address+=n;}
    }
    void toolExploit(byte[] payload,boolean stream)throws IOException {
        toolCommand(6,0xf9,payload,6,false);toolCommand(6,0xf7,WalkerCatalog.TRIGGER_EXPLOIT,6,stream);
    }
    void finishTools(){if(session!=null)try{link.send(new Packet(0xf4,1,session,new byte[0]).encode());}catch(IOException ignored){}}
''' +s[at:]
 p.write_text(s)

s=p.read_text().replace("/** Master-side normal read commands, documented by pwalkerHax. No write/exploit commands. */", "/** Bounded master-side framing. read() is read-only; WalkerTools invokes explicit advanced commands. */")
p.write_text(s)
