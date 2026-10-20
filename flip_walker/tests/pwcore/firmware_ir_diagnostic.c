#define PW_LIBRARY
#include "../../native/pwcore/main.c"
#undef printf
#undef puts
static void record(uint8_t *ee,int a,int n){int sum=1;for(int i=0;i<n;i++)sum+=ee[a+i];ee[a+n]=sum;memcpy(ee+a+256,ee+a,n+1);}
static void packet(uint8_t *b,int cmd,const uint8_t *session){memset(b,0,8);b[0]=cmd;b[1]=1;memcpy(b+4,session,4);unsigned sum=2;for(int i=0;i<8;i++)sum+=b[i]<<(i%2?0:8);while(sum>>16)sum=(sum&65535)+(sum>>16);b[2]=sum;b[3]=sum>>8;for(int i=0;i<8;i++)b[i]^=0xaa;}
int main(int argc,char**argv){
 uint8_t rom[0xc000],ee[65536]={0},out[263],b[8],session[4]={1,2,3,4};
 FILE*f=fopen(argv[1],"rb");if(!f)return 1;if(fread(rom,1,sizeof rom,f)!=sizeof rom)return 2;fclose(f);
 memcpy(ee,"nintendo",8);ee[0xed+0x5b]=1;ee[0xed+0x5c]=2;record(ee,0xed,104);record(ee,0x156,24);record(ee,0x16f,2);record(ee,0x83,40);
 pwcore_init(rom,sizeof rom,ee);for(int t=0;t<30000;t+=4)if(pwcore_run(4,0))return 3;
 printf("boot pc=%04x event=%04x scr=%02x\n",g_ctx.ip,read16(&g_ctx,0xf7e0),g_ctx.scr);
 pwcore_call(0x880,0);write16(&g_ctx,0xf7e0,0x08d6);while(pwcore_ir_pop(out,263)>0){}
 packet(b,0xfa,session);pwcore_ir_push(b,8);int phase=0,at=0;
 for(int t=0;t<2000;t++){if(pwcore_run(1,0))return 4;int n;while((n=pwcore_ir_pop(out,263))>0){printf("t=%d TX n=%d cmd=%02x\n",t,n,out[0]^0xaa);if(n==8&&(out[0]^0xaa)==0xf8){for(int i=0;i<4;i++)session[i]^=out[i+4]^0xaa;packet(b,0x20,session);pwcore_ir_push(b,8);phase=1;at=t;}else if(n==112){printf("IDENTITY_REPLY_EMULATED_MS=%d first=%02x\n",t-at,out[8]^0xaa);return 0;}}}
 printf("NO_REPLY phase=%d pc=%04x\n",phase,g_ctx.ip);return 5;
}
