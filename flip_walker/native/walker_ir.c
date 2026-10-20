/* Offline-prepared KYF37 raw SIR helper. No arbitrary paths or shell commands.
 * Framing on stdin: op(1 TX / 2 RX / 3 CLOSE), big-endian u16 length/timeout.
 * stdout: big-endian u16 byte count, payload. Startup returns "PWIR1".
 * All error details go to stderr. UART is opened only after an ownership grant.
 */
#define _GNU_SOURCE
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <termios.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

static int uart=-1, power=-1, ue=-1, acquired=0, configured=0, exclusive=0, arbitration_unavailable=0;
static struct termios original;
static volatile sig_atomic_t stopping=0;
static void stop(int sig){(void)sig;stopping=1;}
static int exact(int fd,void *buf,size_t n,int writing){
    size_t off=0;
    while(off<n && !stopping){
        ssize_t got=writing?write(fd,(char*)buf+off,n-off):read(fd,(char*)buf+off,n-off);
        if(got<0 && errno==EINTR)continue;
        if(got<=0)return -1;
        off+=(size_t)got;
    }
    return off==n?0:-1;
}
static int arbitrate(unsigned char command){
    int fd=socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);if(fd<0)return -1;
    struct sockaddr_un addr;memset(&addr,0,sizeof(addr));addr.sun_family=AF_UNIX;
    strcpy(addr.sun_path,"/dev/socket/kflcd");
    struct timeval timeout={2,500000};
    setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
    setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
    unsigned char request[12]={0},response[12];request[0]=command;
    int result=-1;
    arbitration_unavailable=0;
    if(connect(fd,(struct sockaddr*)&addr,sizeof(addr))<0){
        arbitration_unavailable=errno==ECONNREFUSED || errno==ENOENT;
        fprintf(stderr,"UART arbitration connect error=%d\n",errno);
    }
    else if(exact(fd,request,12,1)<0)fprintf(stderr,"UART arbitration send error=%d\n",errno);
    else if(exact(fd,response,12,0)<0)fprintf(stderr,"UART arbitration receive error=%d\n",errno);
    else {
        result=(int)((uint32_t)response[4]|(uint32_t)response[5]<<8|(uint32_t)response[6]<<16|(uint32_t)response[7]<<24);
        fprintf(stderr,"UART reply=%02x%02x%02x%02x %02x%02x%02x%02x %02x%02x%02x%02x\n",
            response[0],response[1],response[2],response[3],response[4],response[5],response[6],response[7],response[8],response[9],response[10],response[11]);
    }
    fprintf(stderr,"UART arbitration command=%02x status=%d\n",command,result);
    close(fd);return result;
}
static int claim_atomic_uart(void){
    ue=open("/dev/felica_ue",O_RDWR|O_CLOEXEC|O_NOFOLLOW);if(ue<0)return -1;
    if(ioctl(ue,0x4bf0,0)==0){fprintf(stderr,"UART acquired through atomic kernel lease\n");return 0;}
    int unsupported=errno==ENOTTY;
    close(ue);ue=-1;return unsupported?1:-1;
}
static int claim_kernel_uart(void){
    // Same real kernel gate used by kflcd's GetFeliCaUseStatus/UartUseFinish.
    // Only a missing/non-listening daemon permits this path, never a busy reply.
    // This character device changes a RAM exclusion flag, not FeliCa/NV content.
    ue=open("/dev/felica_ue",O_RDWR|O_CLOEXEC|O_NOFOLLOW);if(ue<0)return -1;
    unsigned char busy=1,claim=1;
    if(flock(ue,LOCK_EX|LOCK_NB)<0 || read(ue,&busy,1)!=1 || busy!=0){close(ue);ue=-1;errno=EBUSY;return -1;}
    if(write(ue,&claim,1)!=1){close(ue);ue=-1;return -1;}
    // Confirm FeliCa did not start between the observation and claim.
    if(read(ue,&busy,1)!=1 || busy!=0){claim=0;write(ue,&claim,1);close(ue);ue=-1;errno=EBUSY;return -1;}
    fprintf(stderr,"UART acquired through the kernel exclusion gate (daemon not listening)\n");
    return 0;
}
static void cleanup(void){
    if(uart>=0){
        if(configured){ioctl(uart,0x5471,0);tcsetattr(uart,TCSANOW,&original);}
        if(exclusive)ioctl(uart,TIOCNXCL,0);
        close(uart);uart=-1;
    }
    if(power>=0){close(power);power=-1;}
    if(ue>=0){unsigned char clear=0;if(write(ue,&clear,1)!=1)fprintf(stderr,"Kernel UART release failed\n");close(ue);ue=-1;}
    if(acquired){stopping=0;int status=arbitrate(0x12);if(status<0)fprintf(stderr,"UART release failed; hardware check required\n");acquired=0;}
}
static int fail(const char *why){fprintf(stderr,"%s: %s\n",why,strerror(errno));return 1;}
static int frame(unsigned char *data,int count){
    unsigned char h[2]={(unsigned char)(count>>8),(unsigned char)count};
    return exact(1,h,2,1)||exact(1,data,(size_t)count,1);
}
static int receive(unsigned char *data,int wait){
    struct pollfd p={uart,POLLIN,0};int n=0,ready;
    do{ready=poll(&p,1,wait);}while(ready<0 && errno==EINTR && !stopping);
    if(ready<0)return -1;
    if(!ready)return 0;
    do{
        if(p.revents&(POLLERR|POLLHUP|POLLNVAL))return -1;
        ssize_t got=read(uart,data+n,(size_t)(527-n));
        if(got<=0)return -1;
        n+=(int)got;
        if(n>=527){errno=EMSGSIZE;return -1;}
        ready=poll(&p,1,4); /* interpacket silence, matching pico driver's ~3.7ms */
    }while(ready>0 && !stopping);
    return ready<0?-1:n;
}
static int broker(const char *program){
    if(geteuid()!=0){fprintf(stderr,"Broker requires root\n");return 1;}
    int server=socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);if(server<0)return fail("broker socket");
    struct sockaddr_un address;memset(&address,0,sizeof(address));address.sun_family=AF_UNIX;
    const char *name="kyf37.walker.ir";memcpy(address.sun_path+1,name,strlen(name));
    if(bind(server,(struct sockaddr*)&address,(socklen_t)(sizeof(address.sun_family)+1+strlen(name)))<0){close(server);return fail("broker bind");}
    if(listen(server,1)<0){close(server);return fail("broker listen");}
    signal(SIGTERM,stop);signal(SIGINT,stop);signal(SIGHUP,stop);signal(SIGPIPE,stop);
    fprintf(stderr,"Flip Walker IR broker ready; hardware unopened\n");
    while(!stopping){
        struct pollfd ready={server,POLLIN,0};int n=poll(&ready,1,1000);if(n<0 && errno==EINTR)continue;if(n<=0)continue;
        int client=accept4(server,NULL,NULL,SOCK_CLOEXEC);if(client<0)continue;
        struct ucred peer; socklen_t length=sizeof(peer);struct stat app;
        if(getsockopt(client,SOL_SOCKET,SO_PEERCRED,&peer,&length)<0 || stat("/data/user/0/org.kyf37.walker",&app)<0 ||
                !S_ISDIR(app.st_mode) || app.st_uid<10000 || peer.uid!=app.st_uid){
            fprintf(stderr,"Rejected unauthorized broker client\n");close(client);continue;
        }
        pid_t child=fork();
        if(child==0){
            close(server);
            if(dup2(client,0)<0 || dup2(client,1)<0)_exit(1);
            close(client);char *args[]={(char*)program,"--session",NULL};
            execv(program,args);_exit(1);
        }
        close(client);
        if(child>0){
            int status;
            while(waitpid(child,&status,0)<0 && errno==EINTR){if(stopping)kill(child,SIGTERM);}
        }
    }
    close(server);return 0;
}
int main(int argc,char **argv){
    if(argc==2 && strcmp(argv[1],"--self-test")==0){puts("PWIR1 raw SIR 115200 8N1; no hardware opened");return 0;}
    if(argc==2 && strcmp(argv[1],"--broker")==0)return broker(argv[0]);
    int probe=argc==2 && strcmp(argv[1],"--probe")==0;
    if(argc!=2 || (strcmp(argv[1],"--session")!=0 && !probe)){fprintf(stderr,"Use --session, --probe, --broker or --self-test\n");return 2;}
    if(geteuid()!=0){fprintf(stderr,"Root required for the shared KYF37 infrared UART\n");return 1;}
    signal(SIGTERM,stop);signal(SIGINT,stop);signal(SIGHUP,stop);signal(SIGPIPE,stop);
    atexit(cleanup);
    // Device name is established by the Kyocera UART driver; never scan devices.
    int atomic=claim_atomic_uart();
    if(atomic<0){fprintf(stderr,"Shared UART busy or kernel ownership unavailable\n");return 1;}
    if(atomic==1){
        if(arbitrate(0x11)==2)acquired=1;
        else if(!arbitration_unavailable || claim_kernel_uart()<0){fprintf(stderr,"Shared UART busy or arbitration unavailable\n");return 1;}
    }
    uart=open("/dev/ttyHSL3",O_RDWR|O_NOCTTY|O_CLOEXEC|O_NOFOLLOW);
    if(uart<0)return fail("open infrared UART");
    if(flock(uart,LOCK_EX|LOCK_NB)<0)return fail("exclusive helper lock");
    if(ioctl(uart,TIOCEXCL,0)<0)return fail("exclusive UART");
    exclusive=1;
    if(tcgetattr(uart,&original)<0)return fail("read UART settings");
    struct termios raw=original;cfmakeraw(&raw);raw.c_cflag&=~(CSTOPB|PARENB|CRTSCTS|CSIZE);raw.c_cflag|=CS8|CLOCAL|CREAD;
    raw.c_cc[VMIN]=1;raw.c_cc[VTIME]=0;cfsetispeed(&raw,B115200);cfsetospeed(&raw,B115200);
    if(tcsetattr(uart,TCSANOW,&raw)<0)return fail("configure SIR 115200");
    configured=1;
    if(ioctl(uart,0x5470,0)<0)return fail("enable SIR");
    // Opening irdasd lowers the shutdown GPIO; closing it powers IR down.
    // Evidence: Kyocera kernel drivers/irdasd/irda_sd.c, not a guessed GPIO.
    power=open("/dev/irdasd",O_RDWR|O_CLOEXEC|O_NOFOLLOW);
    if(power<0)return fail("power infrared transceiver");
    usleep(1000);
    tcflush(uart,TCIOFLUSH);
    if(probe){printf("PWIR_PROBE_OK UART=ttyHSL3 SIR=115200/8N1 POWER=irdasd ARBITRATION=%s; optical transfer untested\n",ue>=0?"kernel-ue":"kflcd");return 0;}
    if(exact(1,"PWIR1",5,1))return 1;
    unsigned char header[3],data[527],last_tx[263];int last_tx_size=0;
    while(!stopping){
        struct pollfd input={0,POLLIN,0};int ready=poll(&input,1,3000);
        if(ready<=0 || !(input.revents&POLLIN))break; // release if parent dies/stalls
        if(exact(0,header,3,0))break;
        int value=header[1]*256+header[2];
        if(header[0]==3)break;
        if(header[0]==1){
            if(value<1||value>263||exact(0,data,(size_t)value,0))return 1;
            if(exact(uart,data,(size_t)value,1)||tcdrain(uart)<0)return fail("transmit");
            memcpy(last_tx,data,(size_t)value);last_tx_size=value;
            if(frame(data,0))break;
        }else if(header[0]==2){
            if(value<1||value>1000)return 1;
            int n=receive(data,value);if(n<0)return fail("receive");
            if(last_tx_size>0 && n>=last_tx_size && memcmp(data,last_tx,(size_t)last_tx_size)==0){
                n-=last_tx_size;memmove(data,data+last_tx_size,(size_t)n);last_tx_size=0;
            }
            if(n>263){errno=EMSGSIZE;return fail("oversized received packet");}
            if(frame(data,n))break;
        }else return 1;
    }
    return 0;
}
